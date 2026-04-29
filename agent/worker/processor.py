"""Background worker — processes pending requests via Chrome extension.

Thin dispatcher: picks up PENDING requests, delegates to OperationService
for actual API work, handles status transitions + retry + scene updates.
"""
import asyncio
import base64
import json
import logging
import time
import re
from datetime import datetime, timedelta, timezone

import aiohttp

from agent.db import crud
from agent.services.flow_client import get_flow_client
from agent.services.event_bus import event_bus
from agent.config import (
    POLL_INTERVAL,
    MAX_RETRIES,
    API_COOLDOWN,
    IMAGE_API_COOLDOWN,
    CHARACTER_IMAGE_API_COOLDOWN,
    MAX_CONCURRENT_REQUESTS,
    MAX_CONCURRENT_CAPTCHA_REQUESTS,
    CAPTCHA_API_COOLDOWN,
    VIDEO_API_COOLDOWN,
    MAX_CONCURRENT_IMAGE_REQUESTS,
    MAX_CONCURRENT_VIDEO_REQUESTS,
    MAX_CONCURRENT_CHARACTER_REF_REQUESTS,
    CAPTCHA_RETRY_LIMIT,
    CAPTCHA_RETRY_BACKOFF_BASE,
    CAPTCHA_RETRY_BACKOFF_MAX,
    CAPTCHA_GROUP_PAUSE_SEC,
    CAPTCHA_TRAFFIC_PAUSE_SEC,
    CAPTCHA_SAFE_MODE_SEC,
    CAPTCHA_SAFE_MODE_IMAGE_CONCURRENCY,
    CAPTCHA_SAFE_MODE_IMAGE_COOLDOWN,
    CAPTCHA_CONTENT_TIMEOUT_PAUSE_SEC,
    OPERATION_FAILED_RETRY_BASE_SEC,
    REQUEST_DISPATCH_TIMEOUT,
    VIDEO_POLL_TIMEOUT,
)
from agent.worker._parsing import _is_error
from agent.sdk.services.result_handler import parse_result, apply_scene_result, apply_character_result
from agent.utils.orientation import normalize_orientation

logger = logging.getLogger(__name__)

_API_CALL_TYPES = {"GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE",
                   "GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL",
                   "GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE",
                   "EDIT_CHARACTER_IMAGE"}
_IMAGE_CALL_TYPES = {"GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE",
                     "GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"}
_CHARACTER_IMAGE_CALL_TYPES = {"GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"}
_VIDEO_CALL_TYPES = {
    "GENERATE_VIDEO",
    "REGENERATE_VIDEO",
    "GENERATE_VIDEO_REFS",
    "UPSCALE_VIDEO",
    "UPSCALE_VIDEO_LOCAL",
}
_CAPTCHA_CALL_TYPES = {
    "GENERATE_IMAGE",
    "REGENERATE_IMAGE",
    "EDIT_IMAGE",
    "GENERATE_VIDEO",
    "REGENERATE_VIDEO",
    "GENERATE_VIDEO_REFS",
    "GENERATE_CHARACTER_IMAGE",
    "REGENERATE_CHARACTER_IMAGE",
    "EDIT_CHARACTER_IMAGE",
}

_TYPE_PRIORITY = {
    "GENERATE_CHARACTER_IMAGE": 0, "REGENERATE_CHARACTER_IMAGE": 0, "EDIT_CHARACTER_IMAGE": 0,
    "GENERATE_IMAGE": 1, "REGENERATE_IMAGE": 1, "EDIT_IMAGE": 1,
    "GENERATE_VIDEO": 2, "REGENERATE_VIDEO": 2, "GENERATE_VIDEO_REFS": 2,
    "UPSCALE_VIDEO": 3, "UPSCALE_VIDEO_LOCAL": 3,
}

_OP_NAME_RE = re.compile(r"Operation failed:\s*([A-Za-z0-9_-]+)")
_LOCAL_UPSCALE_SETUP_MARKER = "local_upscale_setup_required"

# Backward-compatible module-level retry map used by unit tests and as
# fallback state when _handle_failure is called without explicit retry dict.
_retry_state: dict[str, float] = {}


def _iso_after(seconds: float) -> str:
    ts = datetime.now(timezone.utc) + timedelta(seconds=max(0.0, float(seconds)))
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_flow_tab_unavailable_error(error_lower: str) -> bool:
    if not error_lower:
        return False
    markers = (
        "no_flow_tab",
        "no flow tab",
        "flow_tab_not_ready",
        "flow tab not ready",
        "flow tab unavailable",
        "cannot access contents of the page",
        "must request permission to access the respective host",
        "grecaptcha not available",
        "context invalidated",
        "token expired",
        "state off",
        "no active flow tab",
        "could not establish connection",
    )
    return any(marker in error_lower for marker in markers)


def _is_unsafe_generation_error(error_lower: str) -> bool:
    markers = (
        "public_error_unsafe_generation",
        "unsafe_generation",
        "unsafe generation",
    )
    return any(marker in error_lower for marker in markers)


def _is_unusual_traffic_error(error_lower: str) -> bool:
    markers = (
        "public_error_unusual_activity_too_much_traffic",
        "too_much_traffic",
        "too much traffic",
        "unusual activity",
    )
    return any(marker in error_lower for marker in markers)


def _is_captcha_timeout_error(error_lower: str) -> bool:
    markers = (
        "content_timeout",
        "captcha_timeout",
        "timed out",
    )
    return any(marker in error_lower for marker in markers)


class APIRateLimiter:
    """Enforces max concurrent requests AND minimum gap between API calls."""
    def __init__(self, max_concurrent: int, cooldown_seconds: float,
                 image_cooldown_seconds: float, character_image_cooldown_seconds: float):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cooldown = cooldown_seconds
        self._image_cooldown = image_cooldown_seconds
        self._character_image_cooldown = character_image_cooldown_seconds
        self._last_call = 0.0
        self._last_image_call = 0.0
        self._last_character_image_call = 0.0
        self._gate = asyncio.Lock()
        self._image_gate = asyncio.Lock()
        self._character_image_gate = asyncio.Lock()

    async def acquire(self, req_type: str):
        await self._semaphore.acquire()
        global_cooldown = self._cooldown
        if req_type in _CHARACTER_IMAGE_CALL_TYPES:
            global_cooldown = min(self._cooldown, self._character_image_cooldown)
        async with self._gate:
            elapsed = time.monotonic() - self._last_call
            if elapsed < global_cooldown:
                await asyncio.sleep(global_cooldown - elapsed)
            self._last_call = time.monotonic()
        if req_type in _CHARACTER_IMAGE_CALL_TYPES:
            async with self._character_image_gate:
                elapsed = time.monotonic() - self._last_character_image_call
                if elapsed < self._character_image_cooldown:
                    await asyncio.sleep(self._character_image_cooldown - elapsed)
                self._last_character_image_call = time.monotonic()
        elif req_type in _IMAGE_CALL_TYPES:
            async with self._image_gate:
                elapsed = time.monotonic() - self._last_image_call
                if elapsed < self._image_cooldown:
                    await asyncio.sleep(self._image_cooldown - elapsed)
                self._last_image_call = time.monotonic()

    def release(self):
        self._semaphore.release()


class WorkerController:
    """Controls the background worker loop with rate limiting and graceful shutdown."""

    def __init__(self):
        self._shutdown = asyncio.Event()
        self._active_ids: set[str] = set()
        self._active_types: dict[str, str] = {}
        self._rate_limiter = APIRateLimiter(
            MAX_CONCURRENT_REQUESTS,
            API_COOLDOWN,
            IMAGE_API_COOLDOWN,
            CHARACTER_IMAGE_API_COOLDOWN,
        )
        self._deferred: dict[str, float] = {}  # rid -> defer_until timestamp
        self._retry_after: dict[str, float] = {}  # rid -> retry_after timestamp
        self._group_retry_after: dict[str, float] = {}  # group key -> retry_after timestamp

    def _image_safe_mode_active(self, now: float) -> bool:
        return self._group_retry_after.get("image_safe_mode_until", 0.0) > now

    def _can_schedule(self, req: dict, now: float) -> bool:
        req_type = req.get("type", "")
        safe_mode = self._image_safe_mode_active(now)

        captcha_pause_until = self._group_retry_after.get("captcha", 0.0)
        captcha_cooldown_until = self._group_retry_after.get("captcha_cooldown_until", 0.0)
        video_cooldown_until = self._group_retry_after.get("video_cooldown_until", 0.0)
        image_pause_until = self._group_retry_after.get("image", 0.0)
        image_cooldown_until = self._group_retry_after.get("image_cooldown_until", 0.0)
        character_image_cooldown_until = self._group_retry_after.get("character_image_cooldown_until", 0.0)
        if req_type in _CAPTCHA_CALL_TYPES:
            if req_type in _VIDEO_CALL_TYPES:
                if captcha_pause_until > now or video_cooldown_until > now:
                    return False
            elif captcha_pause_until > now or captcha_cooldown_until > now:
                return False
            captcha_active = sum(1 for t in self._active_types.values() if t in _CAPTCHA_CALL_TYPES)
            captcha_non_char_active = sum(
                1 for t in self._active_types.values()
                if t in _CAPTCHA_CALL_TYPES and t not in _CHARACTER_IMAGE_CALL_TYPES
            )
            max_captcha_concurrency = MAX_CONCURRENT_CAPTCHA_REQUESTS
            if req_type in _VIDEO_CALL_TYPES:
                max_captcha_concurrency = max(
                    max_captcha_concurrency,
                    min(MAX_CONCURRENT_VIDEO_REQUESTS, MAX_CONCURRENT_REQUESTS),
                )
            if req_type in _CHARACTER_IMAGE_CALL_TYPES and captcha_non_char_active == 0:
                # Ref stage (character/location) can burst slightly faster when no scene jobs are active.
                max_captcha_concurrency = max(
                    max_captcha_concurrency,
                    min(MAX_CONCURRENT_CHARACTER_REF_REQUESTS, 2),
                )
            if safe_mode and req_type in _IMAGE_CALL_TYPES:
                max_captcha_concurrency = min(max_captcha_concurrency, 1)
            if captcha_active >= max_captcha_concurrency:
                return False

        if req_type in _VIDEO_CALL_TYPES:
            video_active = sum(1 for t in self._active_types.values() if t in _VIDEO_CALL_TYPES)
            if video_active >= max(1, MAX_CONCURRENT_VIDEO_REQUESTS):
                return False

        if req_type in _CHARACTER_IMAGE_CALL_TYPES:
            if image_pause_until > now or character_image_cooldown_until > now:
                return False
            char_active = sum(1 for t in self._active_types.values() if t in _CHARACTER_IMAGE_CALL_TYPES)
            max_char_concurrency = MAX_CONCURRENT_CHARACTER_REF_REQUESTS
            if safe_mode:
                max_char_concurrency = min(max_char_concurrency, CAPTCHA_SAFE_MODE_IMAGE_CONCURRENCY)
            return char_active < max_char_concurrency
        if req_type in _IMAGE_CALL_TYPES:
            if image_pause_until > now or image_cooldown_until > now:
                return False
            image_active = sum(
                1 for t in self._active_types.values()
                if t in _IMAGE_CALL_TYPES and t not in _CHARACTER_IMAGE_CALL_TYPES
            )
            max_image_concurrency = MAX_CONCURRENT_IMAGE_REQUESTS
            if safe_mode:
                max_image_concurrency = min(max_image_concurrency, CAPTCHA_SAFE_MODE_IMAGE_CONCURRENCY)
            return image_active < max_image_concurrency
        return True

    @property
    def active_count(self) -> int:
        """Number of currently active requests."""
        return len(self._active_ids)

    async def start(self):
        """Start the worker loop."""
        await self._cleanup_stale_processing()
        await self._run_loop()

    def request_shutdown(self):
        """Signal the worker to stop after current tasks drain."""
        self._shutdown.set()

    async def drain(self, timeout: float = 30.0):
        """Wait until all active tasks complete, with timeout."""
        deadline = time.monotonic() + timeout
        while self._active_ids and time.monotonic() < deadline:
            await asyncio.sleep(0.5)
        if self._active_ids:
            logger.warning("Drain timeout: %d tasks still active after %.0fs", len(self._active_ids), timeout)

    async def _cleanup_stale_processing(self):
        """Reset any requests stuck in PROCESSING state from a previous run."""
        try:
            migrated = await crud.migrate_upscale_requests_to_local()
            if migrated:
                logger.info("Migrated %d legacy UPSCALE_VIDEO request(s) to UPSCALE_VIDEO_LOCAL", migrated)
            stale = await crud.list_requests(status="PROCESSING")
            for req in stale:
                await crud.update_request(req["id"], status="PENDING",
                                          error_message="reset: stale PROCESSING on startup")
                logger.warning("Stale request reset: %s type=%s", req["id"][:8], req.get("type"))
            if stale:
                logger.info("Cleaned up %d stale PROCESSING requests", len(stale))
        except Exception as e:
            logger.warning("Could not clean up stale requests: %s", e)

    async def _run_loop(self):
        client = get_flow_client()

        while not self._shutdown.is_set():
            try:
                if not client.connected:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                now = time.time()
                slots_available = MAX_CONCURRENT_REQUESTS - len(self._active_ids)
                if slots_available <= 0:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                pending = await crud.list_actionable_requests(
                    exclude_ids=self._active_ids,
                    limit=max(25, slots_available * 8),
                )

                pending_count = len(pending)
                await event_bus.emit("worker_tick", {
                    "active": len(self._active_ids),
                    "slots": slots_available,
                    "pending": pending_count,
                })

                if pending:
                    logger.info("Worker: %d actionable, %d active, %d slots",
                                len(pending), len(self._active_ids), slots_available)

                for req in pending:
                    if slots_available <= 0:
                        break
                    rid = req["id"]

                    # Skip in-flight
                    if rid in self._active_ids:
                        continue

                    # Respect stricter image throttle + temporary captcha pause window
                    if not self._can_schedule(req, now):
                        continue

                    # Skip recently deferred (prereq or retry cooldown)
                    if rid in self._deferred and self._deferred[rid] > now:
                        continue
                    self._deferred.pop(rid, None)

                    # DB `next_retry_at` is the source of truth for retry scheduling.
                    # If row is actionable now, clear stale in-memory backoff gate.
                    if rid in self._retry_after and self._retry_after[rid] > now:
                        self._retry_after.pop(rid, None)

                    self._active_ids.add(rid)
                    self._active_types[rid] = req.get("type", "")
                    if req.get("type", "") in _IMAGE_CALL_TYPES:
                        cooldown_key = "image_cooldown_until"
                        cooldown_sec = IMAGE_API_COOLDOWN
                        if req.get("type", "") in _CHARACTER_IMAGE_CALL_TYPES:
                            cooldown_key = "character_image_cooldown_until"
                            cooldown_sec = CHARACTER_IMAGE_API_COOLDOWN
                        elif self._image_safe_mode_active(now):
                            cooldown_sec = max(cooldown_sec, CAPTCHA_SAFE_MODE_IMAGE_COOLDOWN)
                        if cooldown_sec > 0:
                            self._group_retry_after[cooldown_key] = max(
                                self._group_retry_after.get(cooldown_key, 0.0),
                                now + cooldown_sec,
                            )
                    if req.get("type", "") in _CAPTCHA_CALL_TYPES:
                        if req.get("type", "") in _VIDEO_CALL_TYPES:
                            cooldown_key = "video_cooldown_until"
                            cooldown_sec = VIDEO_API_COOLDOWN
                        else:
                            cooldown_key = "captcha_cooldown_until"
                            cooldown_sec = CAPTCHA_API_COOLDOWN
                        if req.get("type", "") in _CHARACTER_IMAGE_CALL_TYPES:
                            cooldown_sec = min(cooldown_sec, CHARACTER_IMAGE_API_COOLDOWN)
                        if self._image_safe_mode_active(now) and req.get("type", "") in _IMAGE_CALL_TYPES:
                            cooldown_sec = max(cooldown_sec, CAPTCHA_SAFE_MODE_IMAGE_COOLDOWN)
                        if cooldown_sec > 0:
                            self._group_retry_after[cooldown_key] = max(
                                self._group_retry_after.get(cooldown_key, 0.0),
                                now + cooldown_sec,
                            )
                    slots_available -= 1
                    asyncio.create_task(self._run_one(req))

                # Prune stale deferred/retry entries for requests no longer pending
                pending_ids = {r["id"] for r in pending}
                self._deferred = {k: v for k, v in self._deferred.items() if k in pending_ids}
                self._retry_after = {k: v for k, v in self._retry_after.items() if k in pending_ids}
                if self._group_retry_after.get("image", 0.0) <= now:
                    self._group_retry_after.pop("image", None)
                if self._group_retry_after.get("captcha", 0.0) <= now:
                    self._group_retry_after.pop("captcha", None)
                if self._group_retry_after.get("captcha_cooldown_until", 0.0) <= now:
                    self._group_retry_after.pop("captcha_cooldown_until", None)
                if self._group_retry_after.get("video_cooldown_until", 0.0) <= now:
                    self._group_retry_after.pop("video_cooldown_until", None)
                if self._group_retry_after.get("image_cooldown_until", 0.0) <= now:
                    self._group_retry_after.pop("image_cooldown_until", None)
                if self._group_retry_after.get("character_image_cooldown_until", 0.0) <= now:
                    self._group_retry_after.pop("character_image_cooldown_until", None)
                if self._group_retry_after.get("image_safe_mode_until", 0.0) <= now:
                    self._group_retry_after.pop("image_safe_mode_until", None)

            except Exception as e:
                logger.exception("Worker loop error: %s", e)

            await asyncio.sleep(POLL_INTERVAL)

    async def _run_one(self, req: dict):
        rid = req["id"]
        req_type = req.get("type", "")
        try:
            await self._rate_limiter.acquire(req_type)
            try:
                await _process_one(req, self._deferred, self._retry_after, self._group_retry_after)
            finally:
                self._rate_limiter.release()
        finally:
            self._active_ids.discard(rid)
            self._active_types.pop(rid, None)


async def _prerequisites_met(req: dict, orientation: str) -> bool:
    """Check if prerequisites are ready. Returns False to defer (stay PENDING)."""
    req_type = req.get("type", "")
    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"

    # Video gen needs scene image to be ready; upscale needs video to be ready
    if req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
        scene = await crud.get_scene(req.get("scene_id"))
        if not scene:
            return True  # let _dispatch handle "scene not found"
        if req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
            if not scene.get(f"{prefix}_image_media_id"):
                logger.info("VIDEO prereq deferred: scene=%s no %s_image_media_id", req.get("scene_id","")[:12], prefix)
                return False
        elif req_type in ("UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
            if not scene.get(f"{prefix}_video_media_id"):
                logger.info("UPSCALE prereq deferred: scene=%s no %s_video_media_id", req.get("scene_id","")[:12], prefix)
                return False

    # Edit requests need source media (own image or parent's for INSERT scenes)
    if req_type in ("EDIT_IMAGE", "EDIT_CHARACTER_IMAGE"):
        if not req.get("source_media_id"):
            if req_type == "EDIT_CHARACTER_IMAGE":
                char = await crud.get_character(req.get("character_id"))
                if not char or not char.get("media_id"):
                    return False
            elif req_type == "EDIT_IMAGE":
                scene = await crud.get_scene(req.get("scene_id"))
                if not scene:
                    return True  # let _dispatch handle
                # CONTINUATION scenes always use parent's image as source
                src = None
                if scene.get("parent_scene_id"):
                    parent = await crud.get_scene(scene["parent_scene_id"])
                    src = parent.get(f"{prefix}_image_media_id") if parent else None
                if not src:
                    src = scene.get(f"{prefix}_image_media_id")
                logger.info("EDIT_IMAGE prereq: scene=%s src=%s parent=%s", req.get("scene_id","")[:12], src, scene.get("parent_scene_id","")[:12] if scene.get("parent_scene_id") else "none")
                if not src:
                    return False

    return True


async def _resolve_orientation(req: dict) -> str:
    """Resolve orientation from request, falling back to video table, then VERTICAL."""
    orient = req.get("orientation")
    if orient:
        return normalize_orientation(orient)
    vid = req.get("video_id")
    if vid:
        video = await crud.get_video(vid)
        if video and video.get("orientation"):
            return normalize_orientation(video["orientation"])
    pid = req.get("project_id")
    if pid:
        project = await crud.get_project(pid)
        if project and project.get("orientation"):
            return normalize_orientation(project["orientation"])
    return "VERTICAL"


async def _process_one(
    req: dict,
    deferred: dict = None,
    retry_after: dict = None,
    group_retry_after: dict = None,
):
    rid, req_type = req["id"], req["type"]
    orientation = await _resolve_orientation(req)

    if await _is_already_completed(req, orientation):
        logger.info("Request %s skipped — already COMPLETED", rid[:8])
        # Copy existing result data from scene/character onto the request record
        skip_kwargs = {"status": "COMPLETED", "error_message": "skipped: already completed"}
        prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
        if req_type in ("GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"):
            char = await crud.get_character(req.get("character_id"))
            if char:
                skip_kwargs["media_id"] = char.get("media_id")
                skip_kwargs["output_url"] = char.get("image_url")
        else:
            scene = await crud.get_scene(req.get("scene_id"))
            if scene:
                if req_type == "GENERATE_IMAGE":
                    skip_kwargs["media_id"] = scene.get(f"{prefix}_image_media_id")
                    skip_kwargs["output_url"] = scene.get(f"{prefix}_image_url")
                elif req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
                    skip_kwargs["media_id"] = scene.get(f"{prefix}_video_media_id")
                    skip_kwargs["output_url"] = scene.get(f"{prefix}_video_url")
                elif req_type in ("UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
                    skip_kwargs["media_id"] = scene.get(f"{prefix}_upscale_media_id")
                    skip_kwargs["output_url"] = scene.get(f"{prefix}_upscale_url")
        skip_kwargs["next_retry_at"] = None
        await crud.update_request(rid, **skip_kwargs)
        return

    # Check prerequisites before dispatching — don't burn retries on missing deps
    if not await _prerequisites_met(req, orientation):
        if deferred is not None:
            deferred[rid] = time.time() + 30  # defer 30s before rechecking
        return

    logger.info("Processing request %s type=%s", rid[:8], req_type)
    await crud.update_request(rid, status="PROCESSING", next_retry_at=None)
    processing_payload = {
        "id": rid,
        "status": "PROCESSING",
        "type": req_type,
        "project_id": req.get("project_id"),
        "video_id": req.get("video_id"),
        "scene_id": req.get("scene_id"),
        "character_id": req.get("character_id"),
    }
    await event_bus.emit("request_update", processing_payload)

    try:
        dispatch_timeout = REQUEST_DISPATCH_TIMEOUT
        if req_type in _VIDEO_CALL_TYPES:
            dispatch_timeout = max(REQUEST_DISPATCH_TIMEOUT, VIDEO_POLL_TIMEOUT + 60)

        result = await asyncio.wait_for(_dispatch(req, orientation), timeout=dispatch_timeout)
        if isinstance(result, dict) and result.get("pending") is True:
            retry_after_sec_raw = result.get("retry_after_sec", 8)
            try:
                retry_after_sec = max(3, int(float(retry_after_sec_raw)))
            except Exception:
                retry_after_sec = 8
            pending_message = str(result.get("message") or "Video operation pending")
            await crud.update_request(
                rid,
                status="PENDING",
                error_message=pending_message,
                next_retry_at=_iso_after(retry_after_sec),
            )
            pending_payload = {
                "id": rid,
                "status": "PENDING",
                "type": req_type,
                "project_id": req.get("project_id"),
                "video_id": req.get("video_id"),
                "scene_id": req.get("scene_id"),
                "character_id": req.get("character_id"),
                "message": pending_message,
                "pending": True,
                "next_retry_in_sec": retry_after_sec,
            }
            await event_bus.emit("request_update", pending_payload)
            return
        if _is_error(result):
            failed_payload = {
                "id": rid,
                "status": "FAILED",
                "type": req_type,
                "project_id": req.get("project_id"),
                "video_id": req.get("video_id"),
                "scene_id": req.get("scene_id"),
                "character_id": req.get("character_id"),
                "error": result.get("error") or result.get("data"),
            }
            await event_bus.emit("request_update", failed_payload)
            await event_bus.emit("request_failed", failed_payload)
            await _handle_failure(rid, req, result, retry_after, group_retry_after)
        else:
            gen_result = parse_result(result, req_type)
            await crud.update_request(
                rid,
                status="COMPLETED",
                media_id=gen_result.media_id,
                output_url=gen_result.url,
                next_retry_at=None,
            )
            if req_type in ("GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"):
                char_id = req.get("character_id")
                if char_id:
                    await apply_character_result(char_id, gen_result)
            else:
                await apply_scene_result(req.get("scene_id"), req_type, orientation, gen_result)
            completed_payload = {
                "id": rid,
                "status": "COMPLETED",
                "type": req_type,
                "project_id": req.get("project_id"),
                "video_id": req.get("video_id"),
                "scene_id": req.get("scene_id"),
                "character_id": req.get("character_id"),
                "media_id": gen_result.media_id,
                "output_url": gen_result.url,
            }
            await event_bus.emit("request_update", completed_payload)
            # Backward-compatible aliases for older UI listeners.
            await event_bus.emit("request_completed", completed_payload)
            logger.info("Request %s COMPLETED: media=%s", rid[:8], gen_result.media_id[:20] if gen_result.media_id else "?")
    except Exception as e:
        logger.exception("Request %s exception: %s", rid[:8], e)
        failed_payload = {
            "id": rid,
            "status": "FAILED",
            "type": req_type,
            "project_id": req.get("project_id"),
            "video_id": req.get("video_id"),
            "scene_id": req.get("scene_id"),
            "character_id": req.get("character_id"),
            "error": str(e),
        }
        await event_bus.emit("request_update", failed_payload)
        # Backward-compatible aliases for older UI listeners.
        await event_bus.emit("request_failed", failed_payload)
        await _handle_failure(rid, req, {"error": str(e)}, retry_after, group_retry_after)


async def _dispatch(req: dict, orientation: str) -> dict:
    """Route request to the appropriate OperationService method."""
    from agent.sdk.services.operations import get_operations
    ops = get_operations()
    req_type, rid = req["type"], req["id"]
    pid = req.get("project_id", "0")

    # Scene-based operations
    if req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE",
                    "GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
        scene = await crud.get_scene(req.get("scene_id"))
        if not scene:
            return {"error": "Scene not found"}
        scene["_project_id"] = pid

        if req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE"):
            return await ops.generate_scene_image(scene, orientation)
        if req_type == "EDIT_IMAGE":
            return await ops.edit_scene_image(scene, orientation, source_media_id=req.get("source_media_id"))
        if req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO"):
            return await ops.generate_scene_video(scene, orientation, request_id=rid)
        if req_type == "GENERATE_VIDEO_REFS":
            return await ops.generate_scene_video_refs(scene, orientation, request_id=rid)
        if req_type in ("UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
            from agent.services.local_upscaler import upscale_scene_video_local

            return await upscale_scene_video_local(
                scene,
                orientation,
                project_id=pid,
            )

    # Character operations
    if req_type in ("GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"):
        char = await crud.get_character(req.get("character_id"))
        if not char:
            return {"error": "Character not found"}
        if req_type == "REGENERATE_CHARACTER_IMAGE":
            # Clear existing media so generate_reference_image takes the normal (not fast) path
            await crud.update_character(char["id"], media_id=None, reference_image_url=None)
            char["media_id"] = None
            char["reference_image_url"] = None
            return await ops.generate_reference_image(char, pid)
        if req_type == "EDIT_CHARACTER_IMAGE":
            src = req.get("source_media_id") or char.get("media_id")
            if not src:
                return {"error": "No source image to edit — generate a reference image first"}
            edit_prompt = char.get("image_prompt") or char.get("description", "")
            project = await crud.get_project(pid) if pid != "0" else None
            tier = project.get("user_paygate_tier", "PAYGATE_TIER_ONE") if project else "PAYGATE_TIER_ONE"
            aspect = "IMAGE_ASPECT_RATIO_LANDSCAPE" if char.get("entity_type") in ("location",) else "IMAGE_ASPECT_RATIO_PORTRAIT"
            return await ops._client.edit_image(
                prompt=edit_prompt, source_media_id=src,
                project_id=pid, aspect_ratio=aspect,
                user_paygate_tier=tier,
            )
        return await ops.generate_reference_image(char, pid)

    return {"error": f"Unknown request type: {req_type}"}


async def _reupload_media(url: str, project_id: str) -> str | None:
    """Download image from URL and re-upload to get a fresh media_id."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.warning("Re-upload: failed to download %s (status %d)", url[:60], resp.status)
                    return None
                image_bytes = await resp.read()
                content_type = resp.headers.get("Content-Type", "image/jpeg")

        if not content_type.startswith("image/"):
            logger.warning("Re-upload: unexpected content-type %s from %s", content_type, url[:60])
            return None
        image_b64 = base64.b64encode(image_bytes).decode()
        mime = content_type.split(";")[0].strip()

        client = get_flow_client()
        result = await client.upload_image(image_b64, mime_type=mime, project_id=project_id)
        new_mid = result.get("_mediaId")
        if new_mid:
            logger.info("Re-upload OK: fresh media_id=%s", new_mid[:20])
            return new_mid
        logger.warning("Re-upload: no media_id in response: %s", str(result)[:200])
    except Exception as e:
        logger.warning("Re-upload failed: %s", e)
    return None


async def _recover_entity_not_found(req: dict) -> bool:
    """When Google returns 'entity not found', re-upload the image to get a fresh media_id."""
    req_type = req.get("type", "")
    pid = req.get("project_id", "")
    orientation = await _resolve_orientation(req)
    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"

    # Scene-based requests: re-upload scene image
    if req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
        scene = await crud.get_scene(req.get("scene_id"))
        if not scene:
            return False
        url = scene.get(f"{prefix}_image_url")
        if not url:
            return False
        new_mid = await _reupload_media(url, pid)
        if new_mid:
            await crud.update_scene(scene["id"], **{f"{prefix}_image_media_id": new_mid})
            logger.info("Recovered scene %s: new %s_image_media_id=%s", scene["id"][:12], prefix, new_mid[:12])
            return True

    # Character-based requests: re-upload ref image
    if req_type in ("EDIT_CHARACTER_IMAGE",):
        char = await crud.get_character(req.get("character_id"))
        if not char:
            return False
        url = char.get("reference_image_url")
        if not url:
            return False
        new_mid = await _reupload_media(url, pid)
        if new_mid:
            await crud.update_character(char["id"], media_id=new_mid)
            logger.info("Recovered character %s: new media_id=%s", char["id"][:12], new_mid[:12])
            return True

    return False


async def _handle_failure(
    rid: str,
    req: dict,
    result: dict,
    retry_after: dict = None,
    group_retry_after: dict = None,
):
    if retry_after is None:
        retry_after = _retry_state

    error_msg = result.get("error")
    if not error_msg:
        data = result.get("data", {})
        if isinstance(data, dict):
            ef = data.get("error", "Unknown error")
            if isinstance(ef, dict):
                error_msg = ef.get("message", json.dumps(ef)[:200])
                # Extract detailed reason from error details (e.g. PUBLIC_ERROR_UNSAFE_GENERATION)
                details = ef.get("details", [])
                if details and isinstance(details, list):
                    for d in details:
                        reason = d.get("reason") if isinstance(d, dict) else None
                        if reason:
                            error_msg = f"{error_msg} [{reason}]"
                            break
            else:
                error_msg = str(ef)
        else:
            error_msg = "Unknown error"
    if isinstance(error_msg, dict):
        error_msg = json.dumps(error_msg)[:200]

    # Reconcile stale state: operation may have completed but app request got a transient
    # poll/read mismatch. If we can confirm SUCCESS from check-status, mark COMPLETED.
    if await _try_reconcile_operation_success(rid, req, error_msg):
        return

    # Auto-recover expired media by re-uploading
    if "not found" in str(error_msg).lower():
        recovered = await _recover_entity_not_found(req)
        if recovered:
            logger.info("Request %s: recovered expired media, retrying", rid[:8])
            await crud.update_request(rid, status="PENDING", error_message=f"recovered: {error_msg}", next_retry_at=None)
            return

    error_lower = str(error_msg).lower()

    # WS transient errors (extension disconnect/reconnect): retry without incrementing count
    if "extension reconnected" in error_lower or "extension disconnected" in error_lower or "extension not connected" in error_lower:
        await crud.update_request(rid, status="PENDING", error_message=str(error_msg), next_retry_at=None)
        logger.info("Request %s transient WS error, will retry (no retry increment): %s", rid[:8], error_msg)
        return

    # Flow tab/runtime unavailable: don't burn captcha retry budget.
    if _is_flow_tab_unavailable_error(error_lower):
        delay = max(15, CAPTCHA_CONTENT_TIMEOUT_PAUSE_SEC // 2)
        if retry_after is not None:
            retry_after[rid] = time.time() + delay
        if group_retry_after is not None and req.get("type", "") in _CAPTCHA_CALL_TYPES:
            pause_until = time.time() + max(delay, CAPTCHA_GROUP_PAUSE_SEC)
            group_retry_after["captcha"] = max(group_retry_after.get("captcha", 0.0), pause_until)
            if req.get("type", "") in _IMAGE_CALL_TYPES:
                group_retry_after["image"] = max(group_retry_after.get("image", 0.0), pause_until)
        await crud.update_request(
            rid,
            status="PENDING",
            error_message=str(error_msg),
            next_retry_at=_iso_after(delay),
        )
        try:
            # Trigger extension warm-up (open/refresh Flow tab + token) opportunistically.
            await get_flow_client().refresh_token()
        except Exception:
            pass
        logger.warning(
            "Request %s Flow tab unavailable, deferred %ss without increasing retry_count: %s",
            rid[:8], delay, error_msg
        )
        return

    # reCAPTCHA errors: exponential backoff + temporary pause for all captcha-consuming requests
    if "captcha" in error_lower or "recaptcha" in error_lower:
        retry = req.get("retry_count", 0) + 1
        if retry < CAPTCHA_RETRY_LIMIT:
            delay = int(min(CAPTCHA_RETRY_BACKOFF_BASE * (1.6 ** (retry - 1)), CAPTCHA_RETRY_BACKOFF_MAX))
            is_traffic = _is_unusual_traffic_error(error_lower)
            is_timeout = _is_captcha_timeout_error(error_lower)
            if is_timeout:
                delay = max(delay, CAPTCHA_CONTENT_TIMEOUT_PAUSE_SEC)
            if is_traffic:
                delay = max(delay, CAPTCHA_TRAFFIC_PAUSE_SEC)
            until = time.time() + delay
            if retry_after is not None:
                retry_after[rid] = until
            if group_retry_after is not None and req.get("type", "") in _CAPTCHA_CALL_TYPES:
                group_pause_until = time.time() + max(delay, CAPTCHA_GROUP_PAUSE_SEC)
                group_retry_after["captcha"] = max(group_retry_after.get("captcha", 0.0), group_pause_until)
                if req.get("type", "") in _IMAGE_CALL_TYPES:
                    group_retry_after["image"] = max(group_retry_after.get("image", 0.0), group_pause_until)
                if is_traffic:
                    safe_until = time.time() + max(delay, CAPTCHA_SAFE_MODE_SEC)
                    group_retry_after["captcha"] = max(group_retry_after.get("captcha", 0.0), safe_until)
                    group_retry_after["captcha_cooldown_until"] = max(
                        group_retry_after.get("captcha_cooldown_until", 0.0),
                        safe_until,
                    )
                    if req.get("type", "") in _IMAGE_CALL_TYPES:
                        group_retry_after["image_safe_mode_until"] = max(
                            group_retry_after.get("image_safe_mode_until", 0.0),
                            safe_until,
                        )
            await crud.update_request(
                rid,
                status="PENDING",
                retry_count=retry,
                error_message=str(error_msg),
                next_retry_at=_iso_after(delay),
            )
            if retry <= 2:
                try:
                    await get_flow_client().refresh_token()
                except Exception:
                    pass
            logger.warning(
                "Request %s reCAPTCHA failed (retry %d/%d), backoff=%ds, traffic=%s timeout=%s",
                rid[:8], retry, CAPTCHA_RETRY_LIMIT - 1, delay, is_traffic, is_timeout
            )
            return
        else:
            await crud.update_request(rid, status="FAILED", error_message=str(error_msg), next_retry_at=None)
            await _mark_scene_failed(req)
            logger.error(
                "Request %s FAILED after %d reCAPTCHA retries: %s",
                rid[:8], CAPTCHA_RETRY_LIMIT - 1, error_msg
            )
            return

    # Safety-filter blocks are usually deterministic for the same prompt.
    # We already do one auto-safe prompt retry in OperationService; if it still fails,
    # fail fast with a clear hint instead of burning the generic retry budget.
    if _is_unsafe_generation_error(error_lower):
        msg = (
            "Google Flow chan boi bo loc an toan (PUBLIC_ERROR_UNSAFE_GENERATION). "
            "He thong da thu auto-safe prompt nhung van bi chan. "
            "Hay giam noi dung nhay cam/bao luc/18+/thu ghet va tao lai."
        )
        await crud.update_request(rid, status="FAILED", error_message=msg, next_retry_at=None)
        await _mark_scene_failed(req)
        logger.warning("Request %s FAILED by safety filter: %s", rid[:8], error_msg)
        return

    if _LOCAL_UPSCALE_SETUP_MARKER in error_lower:
        await crud.update_request(rid, status="FAILED", error_message=str(error_msg), next_retry_at=None)
        await _mark_scene_failed(req)
        logger.error("Request %s local upscale setup missing: %s", rid[:8], error_msg)
        return

    # Operation failed with operation-id is often a transient bridge/poll mismatch.
    # Retry with a calmer backoff before marking FAILED.
    if _extract_operation_name_from_error(error_msg):
        retry = req.get("retry_count", 0) + 1
        if retry < max(MAX_RETRIES, 8):
            delay = min(OPERATION_FAILED_RETRY_BASE_SEC * retry, 600)
            if retry_after is not None:
                retry_after[rid] = time.time() + delay
            await crud.update_request(
                rid,
                status="PENDING",
                retry_count=retry,
                error_message=str(error_msg),
                next_retry_at=_iso_after(delay),
            )
            logger.warning(
                "Request %s operation-failed transient (retry %d), defer=%ss: %s",
                rid[:8], retry, delay, error_msg
            )
            return

    retry = req.get("retry_count", 0) + 1
    if retry < MAX_RETRIES:
        now = time.time()
        delay = min(2 ** retry * 10, 300)
        if retry_after is not None:
            ra = retry_after.get(rid, 0.0)
            if ra > now:
                # Still in backoff — reset to PENDING so it's not stuck in PROCESSING
                await crud.update_request(rid, status="PENDING", error_message=str(error_msg), next_retry_at=_iso_after(ra - now))
                return
            retry_after[rid] = now + delay
        await crud.update_request(
            rid,
            status="PENDING",
            retry_count=retry,
            error_message=str(error_msg),
            next_retry_at=_iso_after(delay),
        )
        logger.warning("Request %s failed (retry %d/%d): %s", rid[:8], retry, MAX_RETRIES, error_msg)
    else:
        await crud.update_request(rid, status="FAILED", error_message=str(error_msg), next_retry_at=None)
        await _mark_scene_failed(req)
        logger.error("Request %s FAILED permanently: %s", rid[:8], error_msg)


async def _mark_scene_failed(req: dict):
    scene_id = req.get("scene_id")
    if not scene_id:
        return
    orientation = await _resolve_orientation(req)
    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    req_type = req["type"]

    scene = None
    try:
        maybe_scene = crud.get_scene(scene_id)
        if asyncio.iscoroutine(maybe_scene):
            scene = await maybe_scene
        else:
            scene = maybe_scene
    except TypeError:
        # Tests may patch crud as non-async MagicMock without get_scene awaitable.
        scene = None

    if scene:
        # Do not downgrade a stage that already has a completed media result.
        if req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE"):
            if scene.get(f"{prefix}_image_status") == "COMPLETED" and scene.get(f"{prefix}_image_media_id"):
                logger.info("Skip marking image FAILED for scene %s: already COMPLETED with media", scene_id[:12])
                return
        elif req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
            if scene.get(f"{prefix}_video_status") == "COMPLETED" and scene.get(f"{prefix}_video_media_id"):
                logger.info("Skip marking video FAILED for scene %s: already COMPLETED with media", scene_id[:12])
                return
        elif req_type in ("UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
            if scene.get(f"{prefix}_upscale_status") == "COMPLETED" and (
                scene.get(f"{prefix}_upscale_media_id") or scene.get(f"{prefix}_upscale_url")
            ):
                logger.info("Skip marking upscale FAILED for scene %s: already COMPLETED with media", scene_id[:12])
                return

    updates = {}
    if req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE"):
        updates[f"{prefix}_image_status"] = "FAILED"
    elif req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
        updates[f"{prefix}_video_status"] = "FAILED"
    elif req_type in ("UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
        updates[f"{prefix}_upscale_status"] = "FAILED"
    if updates:
        await crud.update_scene(scene_id, **updates)


def _extract_operation_name_from_error(error_msg: str | None) -> str | None:
    if not error_msg:
        return None
    m = _OP_NAME_RE.search(str(error_msg))
    if not m:
        return None
    return m.group(1)


async def _try_reconcile_operation_success(rid: str, req: dict, error_msg: str | None) -> bool:
    """If request has an operation id, re-check it once and recover COMPLETED state."""
    req_type = req.get("type", "")
    if req_type not in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO"):
        return False

    req_row = await crud.get_request(rid)
    op_name = (req_row or {}).get("request_id") or req.get("request_id") or _extract_operation_name_from_error(error_msg)
    if not op_name:
        return False

    client = get_flow_client()
    if not client.connected:
        return False

    status_result = await client.check_video_status([{"operation": {"name": op_name}}])
    if _is_error(status_result):
        return False

    data = status_result.get("data", status_result)
    ops = data.get("operations", []) if isinstance(data, dict) else []
    if not ops:
        return False

    if ops[0].get("status") != "MEDIA_GENERATION_STATUS_SUCCESSFUL":
        return False

    gen_result = parse_result(status_result, req_type)
    if not gen_result.success:
        return False

    await crud.update_request(
        rid,
        status="COMPLETED",
        request_id=op_name,
        media_id=gen_result.media_id,
        output_url=gen_result.url,
        error_message=f"reconciled after transient failure: {error_msg or 'unknown'}",
        next_retry_at=None,
    )

    if req.get("scene_id"):
        orientation = await _resolve_orientation(req)
        await apply_scene_result(req.get("scene_id"), req_type, orientation, gen_result)

    payload = {
        "id": rid,
        "status": "COMPLETED",
        "type": req_type,
        "project_id": req.get("project_id"),
        "video_id": req.get("video_id"),
        "scene_id": req.get("scene_id"),
        "character_id": req.get("character_id"),
        "media_id": gen_result.media_id,
        "output_url": gen_result.url,
    }
    await event_bus.emit("request_update", payload)
    await event_bus.emit("request_completed", payload)
    logger.info("Reconciled request %s to COMPLETED via operation status: %s", rid[:8], op_name)
    return True


async def _is_already_completed(req: dict, orientation: str) -> bool:
    scene_id = req.get("scene_id")
    req_type = req.get("type", "")
    if req_type == "GENERATE_CHARACTER_IMAGE":
        char_id = req.get("character_id")
        if not char_id:
            return False
        char = await crud.get_character(char_id)
        return bool(char and char.get("media_id"))
    if not scene_id:
        return False
    scene = await crud.get_scene(scene_id)
    if not scene:
        return False
    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    if req_type in ("EDIT_IMAGE", "REGENERATE_IMAGE", "REGENERATE_VIDEO", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"):
        return False  # Always run — explicitly requesting new generation
    if req_type == "GENERATE_IMAGE":
        return scene.get(f"{prefix}_image_status") == "COMPLETED"
    if req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
        return scene.get(f"{prefix}_video_status") == "COMPLETED"
    if req_type in ("UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
        return scene.get(f"{prefix}_upscale_status") == "COMPLETED"
    return False


# ─── Module-level controller ──────────────────────────────────

_controller: WorkerController | None = None


def get_worker_controller() -> WorkerController:
    global _controller
    if _controller is None:
        _controller = WorkerController()
    return _controller
