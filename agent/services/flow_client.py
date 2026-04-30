"""
Flow Client — communicates with Google Flow API via Chrome extension WebSocket bridge.

Agent runs a WS server. Extension connects as client. Agent sends API requests,
extension executes them in browser context (residential IP, cookies, reCAPTCHA).
"""
import asyncio
import json
import logging
import re
import shutil
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from urllib.parse import parse_qs, unquote, urlparse

import aiohttp

from agent.config import (
    GOOGLE_FLOW_API, GOOGLE_API_KEY, ENDPOINTS,
    VIDEO_MODELS, UPSCALE_MODELS, IMAGE_MODELS, VIDEO_POLL_TIMEOUT,
    API_HOST, API_PORT, OUTPUT_DIR,
    FLOW_CREDITS_CACHE_TTL_SEC, FLOW_CREDITS_ERROR_TTL_SEC,
    TIER_SYNC_MIN_INTERVAL_SEC,
)
from agent.utils.paths import scene_filename
from agent.utils.slugify import slugify
from agent.services.headers import random_headers, read_headers

logger = logging.getLogger(__name__)
_UNICODE_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _decode_escaped_text(raw: str) -> str:
    """Decode common JSON-escaped URL text emitted by Flow payloads."""
    if not isinstance(raw, str):
        return ""
    text = raw.replace("\\/", "/")
    return _UNICODE_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


def _declared_aspect_in_model_key(model_key: str) -> str | None:
    """Infer declared aspect from model key naming (portrait/landscape)."""
    low = (model_key or "").lower()
    has_portrait = "portrait" in low
    has_landscape = "landscape" in low
    if has_portrait and not has_landscape:
        return "portrait"
    if has_landscape and not has_portrait:
        return "landscape"
    return None


def _wanted_aspect_name(aspect_ratio: str) -> str:
    return "portrait" if str(aspect_ratio or "").upper().endswith("PORTRAIT") else "landscape"


def _model_matches_aspect(model_key: str, aspect_ratio: str) -> bool:
    declared = _declared_aspect_in_model_key(model_key)
    if not declared:
        return True
    return declared == _wanted_aspect_name(aspect_ratio)


def _tier_for_model_key(model_key: str, default_tier: str) -> str:
    """Infer required paygate tier from model key naming."""
    low = (model_key or "").lower()
    # Ultra-relaxed models are PAYGATE_TIER_TWO in current Flow naming.
    if "ultra_relaxed" in low:
        return "PAYGATE_TIER_TWO"
    # Fast portrait/landscape variants map to tier one configs.
    if "fast" in low:
        return "PAYGATE_TIER_ONE"
    return default_tier


def _extract_error_text(result: dict) -> str:
    """Extract normalized error text from extension/API response."""
    if not isinstance(result, dict):
        return str(result)
    error = result.get("error")
    if error:
        return str(error)
    data = result.get("data", {})
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            msg = str(err.get("message") or json.dumps(err)[:240])
            details = err.get("details")
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict) and detail.get("reason"):
                        msg = f"{msg} [{detail['reason']}]"
                        break
            return msg
        if err:
            return str(err)
    return ""


def _is_internal_error_text(text: str | None) -> bool:
    low = (text or "").lower()
    return "internal error encountered" in low or "internal error" in low


def _is_signed_url_expired(url: str | None) -> bool:
    if not isinstance(url, str) or not url.startswith("http"):
        return False
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        raw = (qs.get("Expires") or qs.get("expires") or [None])[0]
        if raw is None:
            return False
        expires_ts = int(raw)
        return expires_ts <= int(time.time())
    except Exception:
        return False


def _is_direct_media_url(url: str | None) -> bool:
    """Return True for renderer-safe media URLs we can persist to DB.

    Rejects trpc redirect URLs (media.getMediaUrlRedirect) which often become
    unusable across sessions.
    """
    if not isinstance(url, str):
        return False
    text = url.strip()
    if not text.startswith("http"):
        return False
    low = text.lower()
    if "media.getmediaurlredirect" in low:
        return False
    if low.startswith("https://flow-content.google/"):
        return True
    if low.startswith("https://storage.googleapis.com/"):
        return True
    if "googleusercontent.com/" in low:
        return True
    return False


def _extract_local_media_path(url: str | None) -> Path | None:
    """Extract local media file path from absolute path / file:// / local-media proxy URL."""
    if not isinstance(url, str):
        return None
    text = url.strip()
    if not text:
        return None

    if text.startswith("http://") or text.startswith("https://"):
        try:
            parsed = urlparse(text)
            host = (parsed.hostname or "").lower()
            if host not in ("127.0.0.1", "localhost"):
                return None
            if parsed.path.rstrip("/") != "/api/flow/local-media":
                return None
            raw_path = (parse_qs(parsed.query).get("path") or [None])[0]
            if not isinstance(raw_path, str) or not raw_path.strip():
                return None
            candidate = Path(unquote(raw_path)).expanduser()
            return candidate if candidate.is_absolute() else None
        except Exception:
            return None

    if text.startswith("file://"):
        try:
            parsed = urlparse(text)
            candidate = Path(unquote(parsed.path)).expanduser()
            return candidate if candidate.is_absolute() else None
        except Exception:
            return None

    candidate = Path(text).expanduser()
    return candidate if candidate.is_absolute() else None


def _has_local_media_file(url: str | None) -> bool:
    path = _extract_local_media_path(url)
    if not path:
        return False
    try:
        return path.exists() and path.is_file()
    except Exception:
        return False


def _scene_slot_meta(url_field: str) -> tuple[str, str, str] | None:
    if url_field.startswith("vertical_"):
        axis = "vertical"
    elif url_field.startswith("horizontal_"):
        axis = "horizontal"
    else:
        return None
    if "_image_" in url_field:
        return "image", axis, "png"
    if "_upscale_" in url_field:
        return "upscale", axis, "mp4"
    if "_video_" in url_field:
        return "video", axis, "mp4"
    return None


def _canonical_scene_media_base_path(
    *,
    project_slug: str,
    scene_id: str,
    display_order: int,
    kind: str,
    axis: str,
) -> Path:
    ext = "png" if kind == "image" else "mp4"
    subdir = "images" if kind == "image" else ("upscale" if kind == "upscale" else "videos")
    filename = scene_filename(display_order + 1, scene_id, ext=ext)
    return OUTPUT_DIR / project_slug / subdir / axis / filename


def _find_scene_canonical_file(
    *,
    project_slug: str,
    scene_id: str,
    display_order: int,
    kind: str,
    axis: str,
) -> Path | None:
    base = _canonical_scene_media_base_path(
        project_slug=project_slug,
        scene_id=scene_id,
        display_order=display_order,
        kind=kind,
        axis=axis,
    )
    if base.exists() and base.is_file():
        return base
    for candidate in sorted(base.parent.glob(f"{base.stem}.*")):
        if candidate.is_file():
            return candidate
    return None


def _find_scene_media_file_any_project(
    *,
    scene_id: str,
    kind: str,
    axis: str,
) -> Path | None:
    """Fallback local lookup when project slug changed after media was downloaded."""
    subdir = "images" if kind == "image" else ("upscale" if kind == "upscale" else "videos")
    pattern = f"scene_*_{scene_id}.*"
    try:
        for project_dir in sorted(OUTPUT_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            media_dir = project_dir / subdir / axis
            if not media_dir.exists() or not media_dir.is_dir():
                continue
            matches = [p for p in sorted(media_dir.glob(pattern)) if p.is_file()]
            if matches:
                return matches[0]
    except Exception:
        return None
    return None


def _find_character_ref_any_slug(character_id: str) -> Path | None:
    refs_dir = OUTPUT_DIR / "_shared" / "refs"
    if not refs_dir.exists() or not refs_dir.is_dir():
        return None
    try:
        matches = [p for p in sorted(refs_dir.glob(f"*_{character_id}.*")) if p.is_file()]
        if matches:
            return matches[0]
    except Exception:
        return None
    return None


_API_PUBLIC_HOST = "127.0.0.1" if API_HOST in {"0.0.0.0", "::"} else API_HOST
_LOCAL_MEDIA_PROXY_BASE = f"http://{_API_PUBLIC_HOST}:{API_PORT}/api/flow/local-media"
_IMAGE_EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/avif": "avif",
}
_VIDEO_EXT_BY_MIME = {
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/webm": "webm",
    "video/x-matroska": "mkv",
}


def _build_local_media_proxy_url(path: Path) -> str:
    return f"{_LOCAL_MEDIA_PROXY_BASE}?path={quote(str(path), safe='')}"


def _guess_media_ext(url: str, content_type: str | None, kind: str) -> str:
    if content_type:
        mime = content_type.split(";", 1)[0].strip().lower()
        if kind == "video" and mime in _VIDEO_EXT_BY_MIME:
            return _VIDEO_EXT_BY_MIME[mime]
        if kind == "image" and mime in _IMAGE_EXT_BY_MIME:
            return _IMAGE_EXT_BY_MIME[mime]
    try:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix.lower().lstrip(".")
        if kind == "video" and suffix in {"mp4", "mov", "webm", "mkv"}:
            return suffix
        if kind == "image" and suffix in {"jpg", "jpeg", "png", "webp", "gif", "bmp", "avif"}:
            return "jpg" if suffix == "jpeg" else suffix
    except Exception:
        pass
    return "mp4" if kind == "video" else "png"


async def _download_remote_media(url: str, target_base_path: Path, kind: str) -> Path | None:
    if not _is_direct_media_url(url):
        return None
    target_base_path.parent.mkdir(parents=True, exist_ok=True)
    timeout_sec = 420 if kind == "video" else 180
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                ext = _guess_media_ext(url, resp.headers.get("content-type"), kind)
                target_path = target_base_path.with_suffix(f".{ext}")
                tmp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
                tmp_path.write_bytes(await resp.read())
                tmp_path.replace(target_path)
                return target_path
    except Exception as exc:
        logger.debug("Failed downloading local media copy from %s: %s", url, exc)
        return None


def _is_model_access_denied(result: dict) -> bool:
    text = _extract_error_text(result).lower()
    return (
        "public_error_model_access_denied" in text
        or "model_access_denied" in text
        or "does not have permission" in text
    )


def _model_key_variants(model_key: str) -> list[str]:
    """Generate safe fallback variants for known Flow naming patterns."""
    low = (model_key or "").lower()
    variants: list[str] = []
    if not low:
        return variants
    # Some accounts only allow *_ultra_relaxed variants for portrait/landscape.
    if "ultra_relaxed" not in low and ("_portrait" in low or "_landscape" in low):
        variants.append(f"{model_key}_ultra_relaxed")
    return variants


def _resolve_video_model_candidates(
    *,
    user_paygate_tier: str,
    gen_type: str,
    aspect_ratio: str,
    requested_model_key: str | None = None,
) -> list[tuple[str, str, str]]:
    """Return ordered, deduplicated candidates: (source, model_key, context_tier)."""
    candidates: list[tuple[str, str, str]] = []
    if requested_model_key:
        candidates.append(
            ("requested", requested_model_key, _tier_for_model_key(requested_model_key, user_paygate_tier))
        )

    tier_order = [user_paygate_tier]
    for tier in ("PAYGATE_TIER_TWO", "PAYGATE_TIER_ONE"):
        if tier not in tier_order:
            tier_order.append(tier)

    for tier in tier_order:
        key = VIDEO_MODELS.get(tier, {}).get(gen_type, {}).get(aspect_ratio)
        if key:
            candidates.append((f"{tier}:{gen_type}:{aspect_ratio}", key, _tier_for_model_key(key, tier)))

    # Heuristic variants (append at the end, keep priority for explicit config).
    base_candidates = list(candidates)
    for source, key, tier in base_candidates:
        for variant in _model_key_variants(key):
            candidates.append((f"{source}:variant", variant, _tier_for_model_key(variant, tier)))

    seen: set[str] = set()
    deduped: list[tuple[str, str, str]] = []
    for source, key, tier in candidates:
        if key and key not in seen:
            seen.add(key)
            deduped.append((source, key, tier))

    matched = [c for c in deduped if _model_matches_aspect(c[1], aspect_ratio)]
    return matched if matched else deduped


def _resolve_video_model_key(
    *,
    user_paygate_tier: str,
    gen_type: str,
    aspect_ratio: str,
    requested_model_key: str | None = None,
) -> tuple[str | None, str]:
    """Pick an aspect-compatible video model key.

    Priority:
    1) explicitly requested key (if aspect-compatible),
    2) configured key for current tier + requested ratio,
    3) compatible fallback from known tiers for same gen_type + ratio.
    """
    candidates = _resolve_video_model_candidates(
        user_paygate_tier=user_paygate_tier,
        gen_type=gen_type,
        aspect_ratio=aspect_ratio,
        requested_model_key=requested_model_key,
    )

    if candidates:
        source, key, resolved_tier = candidates[0]
        if requested_model_key and source != "requested":
            logger.warning(
                "Requested model '%s' mismatches %s. Falling back to '%s' from %s",
                requested_model_key,
                aspect_ratio,
                key,
                source,
            )
        if not _model_matches_aspect(key, aspect_ratio):
            logger.warning(
                "No aspect-compatible model found for %s %s %s; using '%s' from %s",
                user_paygate_tier,
                gen_type,
                aspect_ratio,
                key,
                source,
            )
        return key, resolved_tier
    return None, user_paygate_tier


class FlowClient:
    """Sends commands to Chrome extension via WebSocket."""

    def __init__(self):
        self._extension_ws = None  # Set by WS server when extension connects
        self._extension_ws_pool: set = set()
        self._extension_ws_order: dict[object, int] = {}
        self._extension_ws_seq = 0
        self._pending: dict[str, asyncio.Future] = {}
        self._flow_key: Optional[str] = None
        self._sync_in_progress = False
        self._sync_task: asyncio.Task | None = None
        self._last_tier_sync_at: float = 0.0
        self._last_tier_sync_flow_key: str = ""
        self._tier_sync_min_interval_sec = float(TIER_SYNC_MIN_INTERVAL_SEC)
        self._credits_cache: dict | None = None
        self._credits_cached_at: float = 0.0
        self._credits_cache_flow_key: str = ""
        self._credits_inflight: asyncio.Task | None = None
        # WS stats
        self._ws_connect_count = 0
        self._ws_disconnect_count = 0
        self._ws_connected_at: Optional[float] = None
        self._ws_last_disconnect_at: Optional[float] = None
        # Guard against pull_project_urls spam when UI retries many broken media at once.
        self._project_pull_cooldown_until: dict[str, float] = {}

    def set_extension(self, ws):
        """Called when extension connects via WS."""
        # Keep a pool because MV3 service workers can reconnect frequently.
        # Forcing close on older sockets can create reconnect storms.
        self._extension_ws_pool.add(ws)
        self._extension_ws_seq += 1
        self._extension_ws_order[ws] = self._extension_ws_seq
        self._extension_ws = ws
        self._ws_connect_count += 1
        self._ws_connected_at = time.time()
        logger.info("Extension connected #%d (waiting for extension_ready/token_captured to sync)", self._ws_connect_count)

    def _choose_live_ws(self):
        """Pick any live WS from pool (latest available)."""
        ordered = sorted(
            list(self._extension_ws_pool),
            key=lambda item: self._extension_ws_order.get(item, 0),
            reverse=True,
        )
        for ws in ordered:
            if getattr(ws, "closed", False):
                self._extension_ws_pool.discard(ws)
                self._extension_ws_order.pop(ws, None)
                continue
            return ws
        return None

    def _live_ws_candidates(self) -> list[object]:
        ordered = sorted(
            list(self._extension_ws_pool),
            key=lambda item: self._extension_ws_order.get(item, 0),
            reverse=True,
        )
        live: list[object] = []
        for ws in ordered:
            if getattr(ws, "closed", False):
                self._extension_ws_pool.discard(ws)
                self._extension_ws_order.pop(ws, None)
                continue
            live.append(ws)
        if self._extension_ws in live:
            live.remove(self._extension_ws)
            live.insert(0, self._extension_ws)
        return live

    def clear_extension(self, ws=None):
        """Called when an extension WS disconnects.

        We can have transient duplicate WS connections (service worker reload/reconnect).
        Only drop global connectivity when no live WS remains.
        """
        if ws is not None:
            self._extension_ws_pool.discard(ws)
            self._extension_ws_order.pop(ws, None)
            if self._extension_ws is ws:
                self._extension_ws = self._choose_live_ws()
            elif self._extension_ws is None:
                self._extension_ws = self._choose_live_ws()
        else:
            self._extension_ws_pool.clear()
            self._extension_ws_order.clear()
            self._extension_ws = None

        self._ws_disconnect_count += 1
        self._ws_last_disconnect_at = time.time()

        if self._extension_ws is not None:
            logger.info(
                "Extension WS disconnected, but another WS is still active (connects=%d disconnects=%d)",
                self._ws_connect_count,
                self._ws_disconnect_count,
            )
            return

        # No live WS left: fail pending requests.
        pending_copy = list(self._pending.items())
        count = len(pending_copy)
        for _req_id, future in pending_copy:
            if not future.done():
                future.set_exception(ConnectionError("Extension disconnected"))
        self._pending.clear()
        logger.warning("All extension WS disconnected, cleared %d pending requests", count)

    def set_flow_key(self, key: str):
        if key and key != self._flow_key:
            self._credits_cache = None
            self._credits_cached_at = 0.0
            self._credits_cache_flow_key = ""
        self._flow_key = key

    @property
    def connected(self) -> bool:
        return self._extension_ws is not None

    @property
    def ws_stats(self) -> dict:
        uptime = None
        if self._ws_connected_at and self.connected:
            uptime = int(time.time() - self._ws_connected_at)
        return {
            "connected": self.connected,
            "connects": self._ws_connect_count,
            "disconnects": self._ws_disconnect_count,
            "uptime_s": uptime,
        }

    async def handle_message(self, data: dict):
        """Handle incoming message from extension."""
        if data.get("type") == "token_captured":
            new_key = str(data.get("flowKey") or "").strip()
            key_changed = bool(new_key) and new_key != (self._flow_key or "")
            if new_key:
                if key_changed:
                    self._credits_cache = None
                    self._credits_cached_at = 0.0
                    self._credits_cache_flow_key = ""
                self._flow_key = new_key
            logger.info("Flow key captured from extension%s", " (updated)" if key_changed else "")
            self._queue_tier_sync(reason="token_captured", force=key_changed)
            return

        if data.get("type") == "extension_ready":
            logger.info("Extension ready, flowKey=%s", "yes" if data.get("flowKeyPresent") else "no")
            # Avoid redundant credits checks on each worker reconnect.
            self._queue_tier_sync(reason="extension_ready")
            return

        if data.get("type") == "media_urls_refresh":
            asyncio.create_task(self._refresh_media_urls(data.get("urls", [])))
            return

        if data.get("type") == "pong":
            return

        if data.get("type") == "ping":
            # Respond to keepalive
            if self._extension_ws:
                await self._extension_ws.send(json.dumps({"type": "pong"}))
            return

        # Response to a pending request
        req_id = data.get("id")
        if req_id and req_id in self._pending:
            if not self._pending[req_id].done():
                self._pending[req_id].set_result(data)
            return

    def _queue_tier_sync(self, *, reason: str, force: bool = False):
        """Schedule a debounced tier sync to avoid spamming /v1/credits."""
        if not self.connected:
            return
        if not self._flow_key:
            # Without a captured token, credits call is likely to fail/noise.
            return

        now = time.time()
        key_changed = self._flow_key != self._last_tier_sync_flow_key
        should_run = force or key_changed or (now - self._last_tier_sync_at) >= self._tier_sync_min_interval_sec
        if not should_run:
            return

        if self._sync_task and not self._sync_task.done():
            return

        self._sync_task = asyncio.create_task(self._sync_tier(reason=reason))

    async def _sync_tier(self, *, reason: str = "unknown"):
        """Detect current tier from credits API and update all active projects."""
        if self._sync_in_progress:
            return
        self._sync_in_progress = True
        try:
            result = await self.get_credits(max_age_sec=self._tier_sync_min_interval_sec)
            status = result.get("status")
            if _is_ws_error(result) or (isinstance(status, int) and status >= 400):
                self._last_tier_sync_at = time.time()
                logger.warning(
                    "Tier sync skipped (%s): credits failed status=%s error=%s",
                    reason,
                    status,
                    _extract_error_text(result) or "unknown",
                )
                return

            data = result.get("data", result)
            tier = data.get("userPaygateTier")
            if not tier:
                self._last_tier_sync_at = time.time()
                logger.warning("Tier sync skipped (%s): userPaygateTier missing in credits payload", reason)
                return
            logger.info("Syncing tier: %s (reason=%s)", tier, reason)

            from agent.db import crud
            projects = await crud.list_projects(status="ACTIVE")
            for p in projects:
                if p.get("user_paygate_tier") != tier:
                    await crud.update_project(p["id"], user_paygate_tier=tier)
                    logger.info("Updated project %s tier: %s -> %s",
                                p["id"][:12], p.get("user_paygate_tier"), tier)
            self._last_tier_sync_at = time.time()
            self._last_tier_sync_flow_key = self._flow_key or ""
        except Exception as e:
            self._last_tier_sync_at = time.time()
            logger.warning("Failed to sync tier: %s", e)
        finally:
            self._sync_in_progress = False

    _UUID_RE = __import__("re").compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    _SAFE_URL_RE = __import__("re").compile(r'^https://(storage\.googleapis\.com|lh3\.googleusercontent\.com|flow-content\.google)/')

    @staticmethod
    def _extract_media_url_from_result(result: dict, media_id: str | None = None) -> str | None:
        """Extract URL from get_media response (supports nested payloads).

        Google can return URL in multiple fields or nested structures. We look for common keys first,
        then recursively scan for HTTP URLs that likely point to this media.
        """
        if not isinstance(result, dict):
            return None
        payload = result.get("data", result)

        def _prefer(url: str) -> bool:
            if not _is_direct_media_url(url):
                return False
            low = str(url).lower()
            if media_id and str(media_id).lower() in low:
                return True
            return True

        if isinstance(payload, dict):
            for key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri"):
                value = payload.get(key)
                if _prefer(value):
                    return value

        seen_ids: set[int] = set()
        queue: deque = deque([payload])
        while queue:
            node = queue.popleft()
            node_id = id(node)
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)

            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri") and _prefer(value):
                        return value
                    if isinstance(value, (dict, list, tuple)):
                        queue.append(value)
                    elif _prefer(value):
                        return value
            elif isinstance(node, (list, tuple)):
                for value in node:
                    if isinstance(value, (dict, list, tuple)):
                        queue.append(value)
                    elif _prefer(value):
                        return value
        return None

    async def _refresh_media_urls(self, urls: list[dict]) -> int:
        """Update scene/character URLs in DB from fresh TRPC-captured signed URLs.

        Each entry: {mediaId: str, mediaType: 'image'|'video', url: str}
        """
        from agent.db import crud
        from agent.services.event_bus import event_bus

        updated = 0
        for entry in urls:
            media_id = entry.get("mediaId", "")
            media_type = entry.get("mediaType", "")
            url = entry.get("url", "")
            project_id = str(entry.get("projectId") or "").strip().lower()
            if not media_id or not url:
                continue
            # Validate media_id is UUID and url is from trusted domains
            if not self._UUID_RE.match(media_id):
                logger.warning("Rejected invalid media_id: %s", media_id[:20])
                continue
            if not self._SAFE_URL_RE.match(url):
                logger.warning("Rejected untrusted URL domain for media %s", media_id[:12])
                continue
            if media_type not in ("image", "video"):
                continue
            cached_local_url = await self.cache_media_locally(
                media_id,
                url,
                project_id=project_id or None,
            )
            effective_url = cached_local_url or url

            # Try matching against scenes (check both orientations)
            scenes = await crud.list_scenes_by_media_id(media_id)
            for scene in scenes:
                updates = {}
                if media_type == "image":
                    # Update whichever orientation matches
                    if scene.get("vertical_image_media_id") == media_id:
                        if not _has_local_media_file(scene.get("vertical_image_url")):
                            updates["vertical_image_url"] = effective_url
                    if scene.get("horizontal_image_media_id") == media_id:
                        if not _has_local_media_file(scene.get("horizontal_image_url")):
                            updates["horizontal_image_url"] = effective_url
                elif media_type == "video":
                    if scene.get("vertical_video_media_id") == media_id:
                        if not _has_local_media_file(scene.get("vertical_video_url")):
                            updates["vertical_video_url"] = effective_url
                    if scene.get("horizontal_video_media_id") == media_id:
                        if not _has_local_media_file(scene.get("horizontal_video_url")):
                            updates["horizontal_video_url"] = effective_url
                    if scene.get("vertical_upscale_media_id") == media_id:
                        if not _has_local_media_file(scene.get("vertical_upscale_url")):
                            updates["vertical_upscale_url"] = effective_url
                    if scene.get("horizontal_upscale_media_id") == media_id:
                        if not _has_local_media_file(scene.get("horizontal_upscale_url")):
                            updates["horizontal_upscale_url"] = effective_url
                if updates:
                    await crud.update_scene(scene["id"], **updates)
                    updated += 1

            # Try matching against characters
            chars = await crud.list_characters_by_media_id(media_id)
            for char in chars:
                if media_type == "image" and char.get("media_id") == media_id:
                    if not _has_local_media_file(char.get("reference_image_url")):
                        await crud.update_character(char["id"], reference_image_url=effective_url)
                        updated += 1

        if updated:
            logger.info("Refreshed %d media URLs from TRPC intercept", updated)
            await event_bus.emit("urls_refreshed", {"count": updated})
        return updated

    async def cache_media_locally(
        self,
        media_id: str,
        remote_url: str | None,
        *,
        project_id: str | None = None,
    ) -> str | None:
        """Persist a stable local copy for a scene/character media and return proxy URL."""
        from agent.db import crud

        if not isinstance(media_id, str) or not self._UUID_RE.match(media_id):
            return None
        if not _is_direct_media_url(remote_url):
            return None

        requested_project_id = str(project_id or "").strip().lower()
        first_local_url: str | None = None

        scenes = await crud.list_scenes_by_media_id(media_id)
        video_cache: dict[str, dict | None] = {}
        project_cache: dict[str, dict | None] = {}

        async def _scene_project(scene: dict) -> tuple[dict | None, dict | None]:
            video_id = scene.get("video_id")
            if not isinstance(video_id, str) or not video_id:
                return None, None
            if video_id not in video_cache:
                video_cache[video_id] = await crud.get_video(video_id)
            video = video_cache.get(video_id)
            pid = (video or {}).get("project_id")
            if not isinstance(pid, str) or not pid:
                return video, None
            if pid not in project_cache:
                project_cache[pid] = await crud.get_project(pid)
            return video, project_cache.get(pid)

        scene_slots = (
            ("vertical_image_media_id", "vertical_image_url", "image", "vertical"),
            ("horizontal_image_media_id", "horizontal_image_url", "image", "horizontal"),
            ("vertical_video_media_id", "vertical_video_url", "video", "vertical"),
            ("horizontal_video_media_id", "horizontal_video_url", "video", "horizontal"),
            ("vertical_upscale_media_id", "vertical_upscale_url", "upscale", "vertical"),
            ("horizontal_upscale_media_id", "horizontal_upscale_url", "upscale", "horizontal"),
        )

        for scene in scenes:
            video, project = await _scene_project(scene)
            scene_project_id = str((video or {}).get("project_id") or "").strip().lower()
            if requested_project_id and scene_project_id and scene_project_id != requested_project_id:
                continue

            for media_field, url_field, kind, axis in scene_slots:
                if scene.get(media_field) != media_id:
                    continue

                current_url = scene.get(url_field)
                if _has_local_media_file(current_url):
                    if isinstance(current_url, str):
                        return current_url
                    continue

                project_seed = (
                    (project or {}).get("name")
                    or (video or {}).get("project_id")
                    or scene.get("video_id")
                    or "project"
                )
                project_slug = slugify(str(project_seed)) or "project"
                display_order = int(scene.get("display_order") or 0) + 1
                nominal_ext = "png" if kind == "image" else "mp4"
                canonical_name = scene_filename(display_order, scene["id"], ext=nominal_ext)
                subdir = "images" if kind == "image" else ("upscale" if kind == "upscale" else "videos")
                target_base_path = OUTPUT_DIR / project_slug / subdir / axis / canonical_name
                downloaded = await _download_remote_media(
                    remote_url,
                    target_base_path,
                    "image" if kind == "image" else "video",
                )
                if not downloaded:
                    continue

                proxy_url = _build_local_media_proxy_url(downloaded)
                if scene.get(url_field) != proxy_url:
                    await crud.update_scene(scene["id"], **{url_field: proxy_url})
                if first_local_url is None:
                    first_local_url = proxy_url

        chars = await crud.list_characters_by_media_id(media_id)
        for char in chars:
            char_project_id = str(char.get("project_id") or "").strip().lower()
            if requested_project_id and char_project_id and char_project_id != requested_project_id:
                continue

            current_url = char.get("reference_image_url")
            if _has_local_media_file(current_url):
                if isinstance(current_url, str):
                    return current_url
                continue

            slug = slugify(str(char.get("name") or "character")) or "character"
            target_base_path = OUTPUT_DIR / "_shared" / "refs" / f"{slug}_{char['id']}.png"
            downloaded = await _download_remote_media(remote_url, target_base_path, "image")
            if not downloaded:
                continue

            proxy_url = _build_local_media_proxy_url(downloaded)
            if char.get("reference_image_url") != proxy_url:
                await crud.update_character(char["id"], reference_image_url=proxy_url)
            if first_local_url is None:
                first_local_url = proxy_url

        return first_local_url

    async def find_local_media_url(
        self,
        media_id: str,
        *,
        project_id: str | None = None,
    ) -> str | None:
        from agent.db import crud

        if not isinstance(media_id, str) or not self._UUID_RE.match(media_id):
            return None

        requested_project_id = str(project_id or "").strip().lower()
        scenes = await crud.list_scenes_by_media_id(media_id)
        video_cache: dict[str, dict | None] = {}
        project_cache: dict[str, dict | None] = {}
        for scene in scenes:
            video_id = scene.get("video_id")
            video = None
            project = None
            scene_project_id = ""
            if isinstance(video_id, str) and video_id:
                if video_id not in video_cache:
                    video_cache[video_id] = await crud.get_video(video_id)
                video = video_cache.get(video_id)
                scene_project_id = str((video or {}).get("project_id") or "").strip().lower()
                if requested_project_id and scene_project_id and scene_project_id != requested_project_id:
                    continue
                if scene_project_id:
                    if scene_project_id not in project_cache:
                        project_cache[scene_project_id] = await crud.get_project(scene_project_id)
                    project = project_cache.get(scene_project_id)

            project_seed = (
                (project or {}).get("name")
                or (video or {}).get("project_id")
                or scene.get("video_id")
                or "project"
            )
            project_slug = slugify(str(project_seed)) or "project"
            scene_display_order = int(scene.get("display_order") or 0)
            scene_id = str(scene.get("id") or "")
            if not scene_id:
                continue

            for url_field in (
                "vertical_image_url",
                "horizontal_image_url",
                "vertical_video_url",
                "horizontal_video_url",
                "vertical_upscale_url",
                "horizontal_upscale_url",
            ):
                meta = _scene_slot_meta(url_field)
                if not meta:
                    continue
                kind, axis, nominal_ext = meta
                url = scene.get(url_field)
                local_path = _extract_local_media_path(url)
                if local_path and local_path.exists() and local_path.is_file():
                    canonical_base = _canonical_scene_media_base_path(
                        project_slug=project_slug,
                        scene_id=scene_id,
                        display_order=scene_display_order,
                        kind=kind,
                        axis=axis,
                    )
                    canonical_target = canonical_base.with_suffix(local_path.suffix or f".{nominal_ext}")
                    chosen_path = local_path
                    if canonical_target != local_path:
                        try:
                            canonical_target.parent.mkdir(parents=True, exist_ok=True)
                            if not canonical_target.exists():
                                shutil.copy2(local_path, canonical_target)
                            chosen_path = canonical_target
                        except Exception:
                            chosen_path = local_path
                    normalized_url = _build_local_media_proxy_url(chosen_path)
                    if url != normalized_url:
                        await crud.update_scene(scene_id, **{url_field: normalized_url})
                    return normalized_url

                canonical_existing = _find_scene_canonical_file(
                    project_slug=project_slug,
                    scene_id=scene_id,
                    display_order=scene_display_order,
                    kind=kind,
                    axis=axis,
                )
                if not canonical_existing:
                    canonical_existing = _find_scene_media_file_any_project(
                        scene_id=scene_id,
                        kind=kind,
                        axis=axis,
                    )
                if canonical_existing:
                    normalized_url = _build_local_media_proxy_url(canonical_existing)
                    if url != normalized_url:
                        await crud.update_scene(scene_id, **{url_field: normalized_url})
                    return normalized_url

        chars = await crud.list_characters_by_media_id(media_id)
        for char in chars:
            char_project_id = str(char.get("project_id") or "").strip().lower()
            if requested_project_id and char_project_id and char_project_id != requested_project_id:
                continue
            url = char.get("reference_image_url")
            local_path = _extract_local_media_path(url)
            if local_path and local_path.exists() and local_path.is_file():
                normalized_url = _build_local_media_proxy_url(local_path)
                if url != normalized_url:
                    await crud.update_character(char["id"], reference_image_url=normalized_url)
                return normalized_url

            slug = slugify(str(char.get("name") or "character")) or "character"
            canonical_base = OUTPUT_DIR / "_shared" / "refs" / f"{slug}_{char['id']}.png"
            canonical_existing = canonical_base if canonical_base.exists() else None
            if not canonical_existing:
                for candidate in sorted(canonical_base.parent.glob(f"{canonical_base.stem}.*")):
                    if candidate.is_file():
                        canonical_existing = candidate
                        break
            if canonical_existing and canonical_existing.exists():
                normalized_url = _build_local_media_proxy_url(canonical_existing)
                if url != normalized_url:
                    await crud.update_character(char["id"], reference_image_url=normalized_url)
                return normalized_url
            fallback_ref = _find_character_ref_any_slug(char["id"])
            if fallback_ref and fallback_ref.exists():
                normalized_url = _build_local_media_proxy_url(fallback_ref)
                if url != normalized_url:
                    await crud.update_character(char["id"], reference_image_url=normalized_url)
                return normalized_url
        return None

    _SIGNED_URL_RE = re.compile(
        r"https://(?:storage\.googleapis\.com/ai-sandbox-videofx/(?:image|video)/[0-9a-f-]{36}"
        r"|flow-content\.google/(?:image|video)/[0-9a-f-]{36})[^\s\"']*",
        re.IGNORECASE,
    )
    _MEDIA_PATH_RE = re.compile(r"/(image|video)/([0-9a-f-]{36})(?:\?|$)", re.IGNORECASE)

    def _extract_signed_media_entries(self, payload: object) -> list[dict]:
        """Extract signed media URLs from TRPC payloads.

        Returns a deduplicated list with shape:
          { "mediaId": "<uuid>", "mediaType": "image|video", "url": "<signed-url>" }
        """
        candidates: list[str] = []
        structured_candidates: list[dict] = []
        queue: deque = deque([payload])
        seen_nodes: set[int] = set()

        def _normalized(s: str) -> str:
            return _decode_escaped_text(s)

        def _extract_id_and_type(value: str) -> tuple[str | None, str | None]:
            if not isinstance(value, str):
                return None, None
            raw = value.strip()
            if not raw:
                return None, None
            low = raw.lower()
            if self._UUID_RE.match(low):
                return low, None
            m = self._MEDIA_PATH_RE.search(low)
            if m:
                return m.group(2), m.group(1)
            m2 = re.search(r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b", low)
            if m2:
                return m2.group(1), None
            return None, None

        while queue:
            node = queue.popleft()
            nid = id(node)
            if nid in seen_nodes:
                continue
            seen_nodes.add(nid)

            if isinstance(node, str):
                text = _normalized(node)
                candidates.extend(self._SIGNED_URL_RE.findall(text))
                continue
            if isinstance(node, dict):
                node_media_id: str | None = None
                node_media_type: str | None = None
                node_url: str | None = None

                for key in ("mediaId", "media_id", "id", "name"):
                    value = node.get(key)
                    if not isinstance(value, str):
                        continue
                    extracted_id, extracted_type = _extract_id_and_type(value)
                    if extracted_id:
                        node_media_id = extracted_id
                        if extracted_type:
                            node_media_type = extracted_type
                        break

                for key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri"):
                    value = node.get(key)
                    if not isinstance(value, str):
                        continue
                    normalized_value = _normalized(value)
                    if normalized_value.startswith("http"):
                        node_url = normalized_value
                        break

                if node_media_id and node_url:
                    inferred_type = node_media_type
                    if not inferred_type:
                        path_match = self._MEDIA_PATH_RE.search(node_url.lower())
                        if path_match:
                            inferred_type = path_match.group(1).lower()
                    if inferred_type in ("image", "video"):
                        structured_candidates.append(
                            {
                                "mediaId": node_media_id,
                                "mediaType": inferred_type,
                                "url": node_url,
                            }
                        )

                for value in node.values():
                    if isinstance(value, (dict, list, tuple)):
                        queue.append(value)
                    elif isinstance(value, str):
                        text = _normalized(value)
                        candidates.extend(self._SIGNED_URL_RE.findall(text))
                continue
            if isinstance(node, (list, tuple)):
                for value in node:
                    if isinstance(value, (dict, list, tuple)):
                        queue.append(value)
                    elif isinstance(value, str):
                        text = _normalized(value)
                        candidates.extend(self._SIGNED_URL_RE.findall(text))

        dedup: dict[str, dict] = {}
        for item in structured_candidates:
            media_id = item.get("mediaId")
            media_type = item.get("mediaType")
            url = item.get("url")
            if not isinstance(media_id, str) or not isinstance(media_type, str) or not isinstance(url, str):
                continue
            if not self._UUID_RE.match(media_id):
                continue
            if media_type not in ("image", "video"):
                continue
            dedup[media_id] = {"mediaId": media_id, "mediaType": media_type, "url": url}

        for raw in candidates:
            url = _normalized(raw)
            m = self._MEDIA_PATH_RE.search(url)
            if not m:
                continue
            media_type, media_id = m.group(1).lower(), m.group(2).lower()
            if not self._UUID_RE.match(media_id):
                continue
            dedup[media_id] = {"mediaId": media_id, "mediaType": media_type, "url": url}
        return list(dedup.values())

    async def _refresh_project_urls_via_trpc(self, project_id: str) -> tuple[int, str | None]:
        """Try to refresh project URLs via TRPC flow/project endpoints.

        Returns: (updated_count, source_endpoint_or_none)
        """
        def _input_param(payload: dict) -> str:
            return quote(json.dumps(payload, separators=(",", ":")))

        base_paths = [
            "https://labs.google/fx/api/trpc",
            "https://flow.google.com/api/trpc",
            "https://flow.google.com/fx/api/trpc",
        ]
        endpoints: list[tuple[str, dict]] = [
            ("flow.getFlow", {"json": {"projectId": project_id}}),
            ("flow.getFlow", {"projectId": project_id}),
            ("project.getProject", {"json": {"projectId": project_id}}),
        ]
        endpoint_candidates: list[tuple[str, str, dict | None]] = []
        for base in base_paths:
            for procedure, payload in endpoints:
                endpoint_candidates.append(
                    (
                        f"{base}/{procedure}?input={_input_param(payload)}",
                        "GET",
                        None,
                    )
                )
                endpoint_candidates.append(
                    (
                        f"{base}/{procedure}?batch=1&input={_input_param({'0': payload})}",
                        "GET",
                        None,
                    )
                )
                if len(endpoint_candidates) >= 8:
                    break
            if len(endpoint_candidates) >= 8:
                break
        headers = {
            "content-type": "application/json",
            "accept": "*/*",
        }

        for url, method, body in endpoint_candidates:
            result = await self._send("trpc_request", {
                "url": url,
                "method": method,
                "headers": headers,
                "body": body,
            }, timeout=7)

            status = result.get("status")
            if _is_ws_error(result) or (isinstance(status, int) and status >= 400):
                logger.info(
                    "TRPC URL refresh candidate failed: %s (%s)",
                    url,
                    _extract_error_text(result) or f"HTTP_{status}",
                )
                continue

            payload = result.get("data", result)
            entries = self._extract_signed_media_entries(payload)
            if not entries:
                logger.info("TRPC URL refresh candidate returned no signed URLs: %s", url)
                continue

            updated = await self._refresh_media_urls(entries)
            logger.info("TRPC URL refresh succeeded via %s (entries=%d, updated=%d)", url, len(entries), updated)
            return updated, url

        return 0, None

    async def _refresh_project_urls_via_flow_tab(
        self,
        project_id: str,
        media_hints: list[dict] | None = None,
    ) -> tuple[int, str | None, list[dict], str | None]:
        """Ask extension to scrape signed URLs directly from the active Flow tab."""
        payload: dict = {"projectId": project_id}
        payload["forceFresh"] = True
        if media_hints:
            payload["mediaHints"] = media_hints[:240]
        result = await self._send(
            "pull_project_urls",
            payload,
            timeout=8,
        )
        status = result.get("status")
        if _is_ws_error(result) or (isinstance(status, int) and status >= 400):
            err_text = _extract_error_text(result) or f"HTTP_{status}"
            logger.info(
                "Flow-tab URL pull failed: %s",
                err_text,
            )
            return 0, None, [], err_text

        raw_data = result.get("data")
        if not isinstance(raw_data, dict):
            raw_data = result.get("result")
        data = raw_data if isinstance(raw_data, dict) else result
        entries_raw = data.get("entries") if isinstance(data, dict) else None
        attempts = data.get("attempts") if isinstance(data, dict) else []
        attempts = attempts if isinstance(attempts, list) else []
        if not isinstance(entries_raw, list) or not entries_raw:
            logger.info("Flow-tab URL pull returned no entries for project %s", project_id)
            return 0, None, attempts, None

        entries: list[dict] = []
        for row in entries_raw:
            if not isinstance(row, dict):
                continue
            media_id = str(row.get("mediaId") or "").lower().strip()
            media_type = str(row.get("mediaType") or "").lower().strip()
            url = str(row.get("url") or "").strip()
            if not media_id or not media_type or not url:
                continue
            if not self._UUID_RE.match(media_id):
                continue
            if media_type not in ("image", "video"):
                continue
            entries.append({"mediaId": media_id, "mediaType": media_type, "url": url})

        if not entries:
            return 0, None, attempts, None

        updated = await self._refresh_media_urls(entries)
        logger.info(
            "Flow-tab URL pull refreshed %d rows (entries=%d)",
            updated,
            len(entries),
        )
        return updated, "flow_tab", attempts, None

    async def _get_media_with_retry(
        self,
        media_id: str,
        project_id: str | None,
        *,
        timeout_sec: float = 10.0,
    ) -> tuple[dict, str]:
        """Fetch get_media quickly with a project→global fallback.

        For refresh flows we prefer fast failover instead of long sequential retries:
        - try project-scoped once
        - try global once
        """
        attempts: list[tuple[str, str | None]] = []
        if project_id:
            attempts.append(("project", project_id))
        attempts.append(("global", None))

        last_result: dict = {"error": "Unknown error"}
        last_mode = "global"
        for mode, pid in attempts:
            last_mode = mode
            result = await self.get_media(media_id, project_id=pid, timeout_sec=timeout_sec)
            last_result = result
            status = result.get("status", 0)
            if not _is_ws_error(result) and (not isinstance(status, int) or status < 400):
                # Some project-scoped responses can be HTTP 200 but omit usable URL.
                # In that case continue to the next mode (global) before declaring success.
                direct_url = self._extract_media_url_from_result(result, media_id)
                if direct_url:
                    return result, mode
                if mode == "project":
                    logger.info(
                        "get_media(%s) project mode returned 200 but no direct URL; fallback to global",
                        media_id[:12],
                    )
                    continue
                return result, mode

            # 401 means auth/token issue — no point trying further modes.
            if isinstance(status, int) and status == 401:
                break

            # Internal errors for images are often deterministic; move on quickly.
            if mode == "project":
                continue
            break

        return last_result, last_mode

    async def refresh_project_urls(self, project_id: str) -> dict:
        """Refresh scene/character URLs for a project via get_media(media_id)."""
        from agent.db import crud
        from agent.services.event_bus import event_bus

        videos = await crud.list_videos(project_id)
        scenes: list[dict] = []
        for video in videos:
            scenes.extend(await crud.list_scenes(video["id"]))
        characters = await crud.get_project_characters(project_id)

        slot_pairs = [
            ("vertical_image_media_id", "vertical_image_url"),
            ("horizontal_image_media_id", "horizontal_image_url"),
            ("vertical_video_media_id", "vertical_video_url"),
            ("horizontal_video_media_id", "horizontal_video_url"),
            ("vertical_upscale_media_id", "vertical_upscale_url"),
            ("horizontal_upscale_media_id", "horizontal_upscale_url"),
        ]

        media_ids: list[str] = []
        media_hint_by_mid: dict[str, str] = {}
        for scene in scenes:
            for media_field, _ in slot_pairs:
                mid = scene.get(media_field)
                if isinstance(mid, str) and mid:
                    media_ids.append(mid)
                    if "image_media_id" in media_field:
                        media_hint_by_mid.setdefault(mid, "image")
                    elif (
                        "video_media_id" in media_field
                        or "upscale_media_id" in media_field
                    ):
                        media_hint_by_mid.setdefault(mid, "video")
        for char in characters:
            mid = char.get("media_id")
            if isinstance(mid, str) and mid:
                media_ids.append(mid)
                media_hint_by_mid.setdefault(mid, "image")

        unique_media_ids: list[str] = []
        seen_media: set[str] = set()
        for mid in media_ids:
            if mid in seen_media:
                continue
            seen_media.add(mid)
            unique_media_ids.append(mid)

        media_hints = [
            {
                "mediaId": mid,
                "mediaType": media_hint_by_mid.get(mid, ""),
            }
            for mid in unique_media_ids
        ]

        # First ask active Flow tab/cache for signed URLs (most reliable in Electron runtime).
        try:
            tab_updated, tab_source, tab_attempts, tab_error = await asyncio.wait_for(
                self._refresh_project_urls_via_flow_tab(
                    project_id,
                    media_hints=media_hints,
                ),
                timeout=10,
            )
        except asyncio.TimeoutError:
            tab_updated, tab_source, tab_attempts, tab_error = (0, None, [], "pull_project_urls timeout")
            logger.warning("refresh_project_urls: pull_project_urls timeout for project %s", project_id[:12])
        # Fallback to direct TRPC probes only when tab pull didn't refresh anything.
        trpc_updated, trpc_source = (0, None)
        if not tab_updated and not tab_error:
            try:
                trpc_updated, trpc_source = await asyncio.wait_for(
                    self._refresh_project_urls_via_trpc(project_id),
                    timeout=5,
                )
            except asyncio.TimeoutError:
                trpc_updated, trpc_source = (0, None)
                logger.warning("refresh_project_urls: trpc fallback timeout for project %s", project_id[:12])

        # Reload after TRPC pass so we can skip already refreshed media ids.
        videos = await crud.list_videos(project_id)
        scenes = []
        for video in videos:
            scenes.extend(await crud.list_scenes(video["id"]))
        characters = await crud.get_project_characters(project_id)

        existing_url_by_mid: dict[str, str] = {}
        for scene in scenes:
            for media_field, url_field in slot_pairs:
                mid = scene.get(media_field)
                url = scene.get(url_field)
                if (
                    isinstance(mid, str)
                    and mid
                    and isinstance(url, str)
                    and (_is_direct_media_url(url) or _has_local_media_file(url))
                ):
                    if _is_direct_media_url(url) and _is_signed_url_expired(url):
                        continue
                    existing_url_by_mid[mid] = url
        for char in characters:
            mid = char.get("media_id")
            url = char.get("reference_image_url")
            if (
                isinstance(mid, str)
                and mid
                and isinstance(url, str)
                and (_is_direct_media_url(url) or _has_local_media_file(url))
            ):
                if _is_direct_media_url(url) and _is_signed_url_expired(url):
                    continue
                existing_url_by_mid[mid] = url

        url_cache: dict[str, str | None] = {}
        failed = 0
        auth_failed = False
        errors: list[str] = []
        unresolved_media_ids: list[str] = []
        for mid in unique_media_ids:
            existing = existing_url_by_mid.get(mid)
            if existing:
                url_cache[mid] = existing
            else:
                unresolved_media_ids.append(mid)

        MAX_FOLLOWUP_MEDIA_READS = 12

        async def fetch_one_media(
            mid: str,
        ) -> tuple[str, str | None, str | None, bool, bool, bool]:
            result, mode = await self._get_media_with_retry(mid, project_id, timeout_sec=4.5)
            status = result.get("status", 500)
            is_server_failure = isinstance(status, int) and status >= 500
            if _is_ws_error(result) or (isinstance(status, int) and status >= 400):
                details = _extract_error_text(result) or str(result.get("data", ""))[:200]
                is_internal_failure = _is_internal_error_text(details)
                if is_internal_failure:
                    details = "Google Flow internal error (media có thể đã bị xóa hoặc chưa đồng bộ)"
                return (
                    mid,
                    None,
                    f"{details or f'HTTP_{status}'} [{mode}]",
                    bool(isinstance(status, int) and status == 401),
                    is_server_failure,
                    is_internal_failure,
                )

            url = self._extract_media_url_from_result(result, mid)
            if not url:
                return mid, None, f"no URL in get_media response [{mode}]", False, False, False
            if not _is_direct_media_url(url):
                return mid, None, f"non-direct URL in get_media response [{mode}]", False, False, False
            return mid, url, None, False, False, False

        quick_stop_due_internal = False
        skipped_followup_reads = 0

        def consume_fetch_results(
            rows: list[tuple[str, str | None, str | None, bool, bool, bool]],
        ) -> dict[str, int]:
            nonlocal failed, auth_failed
            internal_failures = 0
            server_failures = 0
            row_failures = 0
            for mid, fresh_url, err_text, got_401, is_server_failure, is_internal_failure in rows:
                if fresh_url:
                    url_cache[mid] = fresh_url
                    continue
                url_cache[mid] = None
                failed += 1
                row_failures += 1
                if got_401:
                    auth_failed = True
                if is_server_failure:
                    server_failures += 1
                if is_internal_failure or (err_text and "internal error" in err_text.lower()):
                    internal_failures += 1
                if len(errors) < 5:
                    errors.append(f"{mid[:8]}: {err_text or 'unknown error'}")
            return {
                "internal": internal_failures,
                "server": server_failures,
                "failed": row_failures,
                "total": len(rows),
            }

        if unresolved_media_ids:
            probe_ids = unresolved_media_ids[:4]
            probe_rows = await asyncio.gather(*(fetch_one_media(mid) for mid in probe_ids))
            probe_stats = consume_fetch_results(probe_rows)

            remaining_ids = [mid for mid in unresolved_media_ids if mid not in set(probe_ids)]
            probe_failed = probe_stats.get("failed", 0)
            probe_internal = probe_stats.get("internal", 0)
            probe_server = probe_stats.get("server", 0)
            severe_probe_failures = probe_internal + probe_server
            should_quick_stop = (
                bool(remaining_ids)
                and (
                    auth_failed
                    or (
                        len(probe_ids) >= 3
                        and probe_failed >= max(3, len(probe_ids) - 1)
                        and severe_probe_failures >= max(2, probe_failed - 1)
                    )
                )
            )

            if should_quick_stop:
                quick_stop_due_internal = True
                for mid in remaining_ids:
                    url_cache[mid] = None
                failed += len(remaining_ids)
            elif remaining_ids:
                followup_ids = remaining_ids[:MAX_FOLLOWUP_MEDIA_READS]
                skipped_ids = remaining_ids[MAX_FOLLOWUP_MEDIA_READS:]
                if skipped_ids:
                    skipped_followup_reads = len(skipped_ids)
                    for mid in skipped_ids:
                        url_cache[mid] = None
                    failed += len(skipped_ids)
                sem = asyncio.Semaphore(4)

                async def fetch_with_limit(mid: str):
                    async with sem:
                        return await fetch_one_media(mid)

                remaining_rows = await asyncio.gather(
                    *(fetch_with_limit(mid) for mid in followup_ids),
                )
                consume_fetch_results(remaining_rows)

        # Convert freshly fetched signed URLs to stable local proxy URLs when possible.
        for mid in unique_media_ids:
            fresh_url = url_cache.get(mid)
            if not isinstance(fresh_url, str) or not _is_direct_media_url(fresh_url):
                continue
            local_url = await self.cache_media_locally(mid, fresh_url, project_id=project_id)
            if local_url:
                url_cache[mid] = local_url

        refreshed = 0
        for scene in scenes:
            updates: dict[str, str] = {}
            for media_field, url_field in slot_pairs:
                mid = scene.get(media_field)
                if not isinstance(mid, str) or not mid:
                    continue
                fresh_url = url_cache.get(mid)
                if not fresh_url:
                    continue
                if scene.get(url_field) != fresh_url:
                    updates[url_field] = fresh_url
            if updates:
                await crud.update_scene(scene["id"], **updates)
                refreshed += 1

        chars_refreshed = 0
        for char in characters:
            mid = char.get("media_id")
            if not isinstance(mid, str) or not mid:
                continue
            fresh_url = url_cache.get(mid)
            if not fresh_url:
                continue
            if char.get("reference_image_url") != fresh_url:
                await crud.update_character(char["id"], reference_image_url=fresh_url)
                chars_refreshed += 1

        if refreshed or chars_refreshed:
            await event_bus.emit(
                "urls_refreshed",
                {"project_id": project_id, "scenes": refreshed, "characters": chars_refreshed},
            )

        result_payload = {
            "refreshed": refreshed,
            "characters_refreshed": chars_refreshed,
            "found": len(unique_media_ids),
            "failed": failed,
        }
        if quick_stop_due_internal:
            result_payload["fast_failover"] = True
        if skipped_followup_reads:
            result_payload["skipped_media_reads"] = skipped_followup_reads
        if trpc_updated:
            result_payload["trpc_refreshed"] = trpc_updated
            if trpc_source:
                result_payload["trpc_source"] = trpc_source
        if tab_updated:
            result_payload["tab_refreshed"] = tab_updated
            if tab_source:
                result_payload["tab_source"] = tab_source
        elif tab_attempts:
            # keep small payload for UI debugging
            result_payload["tab_attempts"] = tab_attempts[:10]
        if tab_error:
            result_payload["tab_error"] = tab_error
        if auth_failed:
            result_payload["note"] = "AUTH_EXPIRED: open Flow tab to refresh token then retry."
        elif quick_stop_due_internal and failed and not refreshed and not chars_refreshed:
            result_payload["note"] = (
                "Google Flow đang trả internal error cho media cũ. "
                "Đã dừng quét sâu để tránh treo; hãy mở đúng project trong cửa sổ Flow "
                "để extension bắt signed URL mới, rồi thử Làm mới URL lại."
            )
        elif skipped_followup_reads and failed:
            result_payload["note"] = (
                "Đã giới hạn số lượt đọc media để tránh bão API_500. "
                "Mở đúng project trong cửa sổ Flow rồi bấm Làm mới URL thêm lần nữa để lấy nốt."
            )
        elif failed and (refreshed or chars_refreshed):
            result_payload["note"] = "Một số media đã được làm mới, nhưng vẫn còn media lỗi từ Google Flow."
        elif failed and not refreshed and not chars_refreshed:
            result_payload["note"] = "Google Flow chưa trả URL mới cho media cũ. Hãy mở lại project trong cửa sổ Flow rồi thử lại."
        if errors:
            result_payload["errors"] = errors
        return result_payload

    async def _send(self, method: str, params: dict, timeout: float = 300) -> dict:
        """Send request to extension and wait for response.

        Always returns a dict. On error, returns {"error": "<reason>"} — callers
        must check result.get("error") or use _is_ws_error() before reading data.
        Never raises; exceptions are caught and returned as error dicts.
        """
        if not self._extension_ws:
            self._extension_ws = self._choose_live_ws()
        if self._extension_ws and getattr(self._extension_ws, "closed", False):
            self._extension_ws = self._choose_live_ws()

        ws_candidates = self._live_ws_candidates()
        if not ws_candidates:
            return {"error": "Extension not connected"}

        def _prefer_another_ws(result: dict, attempt_index: int) -> bool:
            if attempt_index >= len(ws_candidates) - 1:
                return False
            text = (_extract_error_text(result) or "").lower()
            status = result.get("status")

            # For runtime status probes, pick a richer responder if available.
            if method == "get_status":
                raw_data = result.get("data")
                if not isinstance(raw_data, dict):
                    raw_data = result.get("result")
                data = raw_data if isinstance(raw_data, dict) else {}
                has_runtime_fields = any(
                    key in data
                    for key in (
                        "flowTabId",
                        "flowTabUrl",
                        "mediaCacheSize",
                        "projectTabBindings",
                    )
                )
                if not has_runtime_fields:
                    return True
                return False

            # For Flow-runtime bound methods, retry another ws on tab/runtime errors.
            if method in ("api_request", "pull_project_urls", "solve_captcha", "refresh_token"):
                retry_markers = (
                    "no_flow_tab",
                    "flow_tab_not_ready",
                    "extension not connected",
                    "cannot access contents of the page",
                    "must request permission to access the respective host",
                )
                if any(marker in text for marker in retry_markers):
                    return True
                if isinstance(status, int) and status == 503 and "extension not connected" in text:
                    return True
            return False

        last_error: dict = {"error": "Extension not connected"}
        for idx, ws in enumerate(ws_candidates):
            self._extension_ws = ws
            req_id = str(uuid.uuid4())
            future = asyncio.get_running_loop().create_future()
            self._pending[req_id] = future

            try:
                await ws.send(json.dumps({
                    "id": req_id,
                    "method": method,
                    "params": params,
                }))
                result = await asyncio.wait_for(future, timeout=timeout)
                last_error = result
                if _prefer_another_ws(result, idx):
                    logger.info(
                        "WS candidate #%d returned sparse/unavailable response for %s; trying another extension ws",
                        idx + 1,
                        method,
                    )
                    continue
                return result
            except asyncio.TimeoutError:
                last_error = {"error": f"Timeout ({timeout}s) waiting for {method}"}
            except Exception as e:
                last_error = {"error": str(e)}
            finally:
                self._pending.pop(req_id, None)

        return last_error

    def _build_url(self, endpoint_key: str, **kwargs) -> str:
        """Build full API URL."""
        path = ENDPOINTS[endpoint_key].format(**kwargs)
        sep = "&" if "?" in path else "?"
        return f"{GOOGLE_FLOW_API}{path}{sep}key={GOOGLE_API_KEY}"

    def _client_context(self, project_id: str, user_paygate_tier: str = "PAYGATE_TIER_TWO") -> dict:
        """Build clientContext with recaptcha placeholder."""
        return {
            "projectId": str(project_id),
            "recaptchaContext": {
                "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
                "token": "",  # Extension injects real token
            },
            "sessionId": f";{int(time.time() * 1000)}",
            "tool": "PINHOLE",
            "userPaygateTier": user_paygate_tier,
        }

    # ─── High-level API Methods ──────────────────────────────

    async def create_project(self, project_title: str, tool_name: str = "PINHOLE") -> dict:
        """Create a project on Google Flow via tRPC endpoint.

        Returns the full response including projectId.
        """
        url = "https://labs.google/fx/api/trpc/project.createProject"
        body = {"json": {"projectTitle": project_title, "toolName": tool_name}}

        return await self._send("trpc_request", {
            "url": url,
            "method": "POST",
            "headers": {
                "content-type": "application/json",
                "accept": "*/*",
            },
            "body": body,
        }, timeout=30)

    async def generate_images(self, prompt: str, project_id: str,
                               aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT",
                               user_paygate_tier: str = "PAYGATE_TIER_TWO",
                               character_media_ids: list[str] = None,
                               image_model_key: str | None = None) -> dict:
        """Generate image(s).

        If character_media_ids is provided, uses edit_image flow (batchGenerateImages
        with imageInputs) — same endpoint, but includes character references.
        Without characters, uses plain generate_images.

        Response structure:
            data.media[].name = mediaId (used for video gen)
        """
        ts = int(time.time() * 1000)
        ctx = self._client_context(project_id, user_paygate_tier)

        selected_image_model = image_model_key or IMAGE_MODELS["NANO_BANANA_PRO"]

        request_item = {
            "clientContext": {**ctx, "sessionId": f";{ts}"},
            "seed": ts % 1000000,
            "structuredPrompt": {"parts": [{"text": prompt}]},
            "imageAspectRatio": aspect_ratio,
            "imageModelName": selected_image_model,
        }

        # Add character references if provided (edit_image flow)
        if character_media_ids:
            request_item["imageInputs"] = [
                {"name": mid, "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"}
                for mid in character_media_ids
            ]

        batch_id = f"{uuid.uuid4()}" if character_media_ids else None
        body = {
            "clientContext": ctx,
            "requests": [request_item],
        }
        if batch_id:
            body["mediaGenerationContext"] = {"batchId": batch_id}
            body["useNewMedia"] = True

        url = self._build_url("generate_images", project_id=project_id)
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "IMAGE_GENERATION",
        })

    async def edit_image(self, prompt: str, source_media_id: str,
                          project_id: str,
                          aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT",
                          user_paygate_tier: str = "PAYGATE_TIER_ONE",
                          character_media_ids: list[str] = None,
                          image_model_key: str | None = None) -> dict:
        """Edit an existing image using IMAGE_INPUT_TYPE_BASE_IMAGE.

        If character_media_ids is provided, appends them as IMAGE_INPUT_TYPE_REFERENCE
        after the base image. Order: [base_image, char_A, char_B, ...].
        This helps Google Flow detect characters for consistent edits.
        """
        ts = int(time.time() * 1000)
        ctx = self._client_context(project_id, user_paygate_tier)

        image_inputs = [
            {"name": source_media_id, "imageInputType": "IMAGE_INPUT_TYPE_BASE_IMAGE"}
        ]
        if character_media_ids:
            for mid in character_media_ids:
                image_inputs.append({"name": mid, "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"})

        selected_image_model = image_model_key or IMAGE_MODELS["NANO_BANANA_PRO"]

        request_item = {
            "clientContext": {**ctx, "sessionId": f";{ts}"},
            "seed": ts % 1000000,
            "structuredPrompt": {"parts": [{"text": prompt}]},
            "imageAspectRatio": aspect_ratio,
            "imageModelName": selected_image_model,
            "imageInputs": image_inputs,
        }

        body = {
            "clientContext": ctx,
            "mediaGenerationContext": {"batchId": f"{uuid.uuid4()}"},
            "useNewMedia": True,
            "requests": [request_item],
        }

        url = self._build_url("generate_images", project_id=project_id)
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "IMAGE_GENERATION",
        })

    async def generate_video(self, start_image_media_id: str, prompt: str,
                              project_id: str, scene_id: str,
                              aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
                              end_image_media_id: str = None,
                              user_paygate_tier: str = "PAYGATE_TIER_TWO",
                              video_model_key: str | None = None) -> dict:
        """Generate video from start image (i2v).

        Two sub-types:
        - frame_2_video (i2v): startImage only
        - start_end_frame_2_video (i2v_fl): startImage + endImage (for scene chaining)
        """
        gen_type = "start_end_frame_2_video" if end_image_media_id else "frame_2_video"
        candidates = _resolve_video_model_candidates(
            user_paygate_tier=user_paygate_tier,
            gen_type=gen_type,
            aspect_ratio=aspect_ratio,
            requested_model_key=video_model_key,
        )

        if not candidates:
            return {"error": f"No model for tier={user_paygate_tier} type={gen_type} ratio={aspect_ratio}"}

        endpoint_key = "generate_video_start_end" if end_image_media_id else "generate_video"
        url = self._build_url(endpoint_key)
        last_result: dict | None = None

        for idx, (source, model_key, ctx_tier) in enumerate(candidates):
            logger.info(
                "generate_video attempt %d/%d: gen_type=%s ratio=%s model=%s source=%s context_tier=%s requested_tier=%s",
                idx + 1,
                len(candidates),
                gen_type,
                aspect_ratio,
                model_key,
                source,
                ctx_tier,
                user_paygate_tier,
            )

            request = {
                "aspectRatio": aspect_ratio,
                "seed": int(time.time()) % 10000,
                "textInput": {"structuredPrompt": {"parts": [{"text": prompt}]}},
                "videoModelKey": model_key,
                "startImage": {"mediaId": start_image_media_id},
                "metadata": {"sceneId": scene_id},
            }
            if end_image_media_id:
                request["endImage"] = {"mediaId": end_image_media_id}

            body = {
                "mediaGenerationContext": {"batchId": f"{uuid.uuid4()}"},
                "clientContext": self._client_context(project_id, ctx_tier),
                "requests": [request],
                "useV2ModelConfig": True,
            }

            result = await self._send("api_request", {
                "url": url,
                "method": "POST",
                "headers": random_headers(),
                "body": body,
                "captchaAction": "VIDEO_GENERATION",
            }, timeout=60)

            last_result = result
            if not _is_model_access_denied(result):
                if idx > 0:
                    logger.info("generate_video recovered with fallback model=%s", model_key)
                return result

            logger.warning(
                "generate_video model denied for model=%s (%s): %s",
                model_key,
                source,
                _extract_error_text(result),
            )

        return last_result or {"error": "Video generation failed with all model candidates"}

    async def generate_video_from_references(self, reference_media_ids: list[str],
                                              prompt: str, project_id: str, scene_id: str,
                                              aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
                                              user_paygate_tier: str = "PAYGATE_TIER_TWO",
                                              video_model_key: str | None = None) -> dict:
        """Generate video from multiple reference images (r2v).

        Uses referenceImages instead of startImage — the model composes
        a video from all provided reference character images.

        Args:
            reference_media_ids: List of character media_ids (from uploadImage)
        """
        gen_type = "reference_frame_2_video"
        candidates = _resolve_video_model_candidates(
            user_paygate_tier=user_paygate_tier,
            gen_type=gen_type,
            aspect_ratio=aspect_ratio,
            requested_model_key=video_model_key,
        )

        if not candidates:
            return {"error": f"No model for tier={user_paygate_tier} type={gen_type} ratio={aspect_ratio}"}

        url = self._build_url("generate_video_references")
        last_result: dict | None = None

        for idx, (source, model_key, ctx_tier) in enumerate(candidates):
            logger.info(
                "generate_video_from_references attempt %d/%d: ratio=%s model=%s source=%s context_tier=%s requested_tier=%s",
                idx + 1,
                len(candidates),
                aspect_ratio,
                model_key,
                source,
                ctx_tier,
                user_paygate_tier,
            )

            request = {
                "aspectRatio": aspect_ratio,
                "seed": int(time.time()) % 10000,
                "textInput": {"structuredPrompt": {"parts": [{"text": prompt}]}},
                "videoModelKey": model_key,
                "referenceImages": [
                    {"mediaId": mid, "imageUsageType": "IMAGE_USAGE_TYPE_ASSET"}
                    for mid in reference_media_ids
                ],
                "metadata": {},
            }

            body = {
                "mediaGenerationContext": {"batchId": f"{uuid.uuid4()}"},
                "clientContext": self._client_context(project_id, ctx_tier),
                "requests": [request],
                "useV2ModelConfig": True,
            }

            result = await self._send("api_request", {
                "url": url,
                "method": "POST",
                "headers": random_headers(),
                "body": body,
                "captchaAction": "VIDEO_GENERATION",
            }, timeout=60)

            last_result = result
            if not _is_model_access_denied(result):
                if idx > 0:
                    logger.info("generate_video_from_references recovered with fallback model=%s", model_key)
                return result

            logger.warning(
                "generate_video_from_references model denied for model=%s (%s): %s",
                model_key,
                source,
                _extract_error_text(result),
            )

        return last_result or {"error": "Reference video generation failed with all model candidates"}

    async def upscale_video(self, media_id: str, scene_id: str,
                             aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
                             resolution: str = "VIDEO_RESOLUTION_4K") -> dict:
        """Upscale a video."""
        model_key = UPSCALE_MODELS.get(resolution, "veo_3_1_upsampler_4k")

        body = {
            "clientContext": {
                "sessionId": f";{int(time.time() * 1000)}",
                "recaptchaContext": {
                    "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
                    "token": "",
                },
            },
            "requests": [{
                "aspectRatio": aspect_ratio,
                "resolution": resolution,
                "seed": int(time.time()) % 100000,
                "metadata": {"sceneId": scene_id},
                "videoInput": {"mediaId": media_id},
                "videoModelKey": model_key,
            }],
        }

        url = self._build_url("upscale_video")
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        }, timeout=60)

    async def check_video_status(self, operations: list[dict]) -> dict:
        """Check status of video generation operations."""
        body = {"operations": operations}
        url = self._build_url("check_video_status")
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
        }, timeout=30)  # No captcha needed

    def _credits_cache_fresh(self, *, force: bool, max_age_sec: float | None = None) -> bool:
        if force or not self._credits_cache:
            return False
        if self._credits_cache_flow_key != (self._flow_key or ""):
            return False
        status = self._credits_cache.get("status") if isinstance(self._credits_cache, dict) else None
        is_error = _is_ws_error(self._credits_cache) or (isinstance(status, int) and status >= 400)
        ttl = float(FLOW_CREDITS_ERROR_TTL_SEC if is_error else (max_age_sec or FLOW_CREDITS_CACHE_TTL_SEC))
        return (time.time() - self._credits_cached_at) <= ttl

    async def get_credits(self, *, force: bool = False, max_age_sec: float | None = None) -> dict:
        """Get user credits and tier."""
        if self._credits_cache_fresh(force=force, max_age_sec=max_age_sec):
            logger.debug("Credits cache hit (age=%.1fs)", time.time() - self._credits_cached_at)
            return dict(self._credits_cache or {})

        if not force and self._credits_inflight and not self._credits_inflight.done():
            logger.debug("Credits request coalesced with in-flight call")
            return dict(await self._credits_inflight)

        async def _fetch_credits() -> dict:
            url = self._build_url("get_credits")
            result = await self._send("api_request", {
                "url": url,
                "method": "GET",
                "headers": read_headers(),
            }, timeout=15)
            self._credits_cache = dict(result)
            self._credits_cached_at = time.time()
            self._credits_cache_flow_key = self._flow_key or ""
            return result

        self._credits_inflight = asyncio.create_task(_fetch_credits())
        try:
            return dict(await self._credits_inflight)
        finally:
            if self._credits_inflight and self._credits_inflight.done():
                self._credits_inflight = None

    async def get_credits_uncached(self) -> dict:
        """Force a live credits fetch. Keep explicit for diagnostics only."""
        url = self._build_url("get_credits")
        return await self._send("api_request", {
            "url": url,
            "method": "GET",
            "headers": read_headers(),
        }, timeout=15)

    async def refresh_token(self) -> dict:
        """Ask extension to re-capture a fresh Flow auth token from the Flow tab."""
        return await self._send("refresh_token", {}, timeout=25)

    async def get_extension_status(self) -> dict:
        """Get runtime extension status (not just WS socket presence)."""
        if not self.connected:
            return {
                "connected": False,
                "agent_connected": False,
                "flow_key_present": bool(self._flow_key),
                "state": "off",
                "manual_disconnect": False,
                "runtime_connected": False,
                "token_auth_state": "unknown",
                "token_auth_checked_at": None,
                "token_auth_error": None,
            }

        result = await self._send("get_status", {}, timeout=2.5)
        if _is_ws_error(result):
            return {
                "connected": True,
                "agent_connected": False,
                "flow_key_present": bool(self._flow_key),
                "state": "off",
                "manual_disconnect": False,
                "runtime_connected": False,
                "error": _extract_error_text(result) or "STATUS_UNAVAILABLE",
                "token_auth_state": "unknown",
                "token_auth_checked_at": None,
                "token_auth_error": None,
            }

        raw_data = result.get("data")
        if not isinstance(raw_data, dict):
            raw_data = result.get("result")
        data = raw_data if isinstance(raw_data, dict) else result
        if not data or not isinstance(data, dict):
            logger.warning("get_extension_status unexpected payload: %s", str(result)[:260])
            data = {}
        elif not data.get("state") and not data.get("flowKeyPresent"):
            logger.warning("get_extension_status sparse payload: %s", str(result)[:260])
        agent_connected = bool(data.get("agentConnected", data.get("connected", self.connected)))
        state = str(data.get("state") or ("idle" if agent_connected else "off")).lower()
        manual_disconnect = bool(data.get("manualDisconnect", False))
        flow_key_present = bool(data.get("flowKeyPresent", self._flow_key))
        runtime_connected = agent_connected and not manual_disconnect and state != "off"
        return {
            "connected": self.connected,
            "agent_connected": agent_connected,
            "flow_key_present": flow_key_present,
            "state": state,
            "manual_disconnect": manual_disconnect,
            "runtime_connected": runtime_connected,
            "flow_tab_id": data.get("flowTabId"),
            "flow_tab_url": data.get("flowTabUrl"),
            "flow_tab_seen_at": data.get("flowTabSeenAt"),
            "token_age_ms": data.get("tokenAge"),
            "token_auth_state": data.get("tokenAuthState")
            or (data.get("metrics") or {}).get("tokenAuthState")
            or "unknown",
            "token_auth_checked_at": data.get("tokenAuthCheckedAt")
            or (data.get("metrics") or {}).get("tokenAuthCheckedAt"),
            "token_auth_error": data.get("tokenAuthError")
            or (data.get("metrics") or {}).get("tokenAuthError"),
            "metrics": data.get("metrics"),
            "media_cache_size": data.get("mediaCacheSize"),
            "project_tab_bindings": data.get("projectTabBindings"),
            "debug_flow_tabs": data.get("debugFlowTabs"),
        }

    async def validate_media_id(self, media_id: str) -> bool:
        """Check if a mediaId is still valid.

        Production calls: GET /v1/media/{mediaId}?key=...&clientContext.tool=PINHOLE
        Returns True on 200, False otherwise.
        """
        result = await self.get_media(media_id)
        status = result.get("status", 500)
        return isinstance(status, int) and status == 200

    async def get_media(
        self,
        media_id: str,
        project_id: str | None = None,
        *,
        timeout_sec: float = 20,
    ) -> dict:
        """Fetch media metadata from Google Flow.

        Returns the raw API response which contains a fresh signed URL
        in data.fifeUrl or data.servingUri.
        """
        async def _pull_from_project_tab() -> dict | None:
            if not project_id:
                return None
            now = time.time()
            cool_until = self._project_pull_cooldown_until.get(project_id, 0.0)
            if now < cool_until:
                return None
            self._project_pull_cooldown_until[project_id] = now + 1.2
            pull = await self._send(
                "pull_project_urls",
                {
                    "projectId": project_id,
                    "mediaHints": [{"mediaId": media_id, "mediaType": ""}],
                    "forceFresh": True,
                },
                timeout=max(12, min(30, timeout_sec)),
            )
            pull_status = pull.get("status")
            if _is_ws_error(pull) or (isinstance(pull_status, int) and pull_status >= 400):
                return None

            raw_data = pull.get("data")
            if not isinstance(raw_data, dict):
                raw_data = pull.get("result")
            data = raw_data if isinstance(raw_data, dict) else {}
            entries = data.get("entries") if isinstance(data.get("entries"), list) else []
            for row in entries:
                if not isinstance(row, dict):
                    continue
                if str(row.get("mediaId") or "").lower().strip() != media_id.lower():
                    continue
                url = str(row.get("url") or "").strip()
                if not _is_direct_media_url(url):
                    continue
                return {
                    "status": 200,
                    "data": {
                        "name": media_id,
                        "fifeUrl": url,
                        "url": url,
                        "_source": "pull_project_urls",
                    },
                }
            return None

        # Fast path: prefer URLs already visible in active Flow tab before hitting /v1/media.
        # This avoids intermittent API_500 storms for older media IDs.
        if project_id and timeout_sec >= 8:
            pulled = await _pull_from_project_tab()
            if pulled:
                return pulled

        base = f"{GOOGLE_FLOW_API}/v1/media/{media_id}?key={GOOGLE_API_KEY}&clientContext.tool=PINHOLE"
        candidates: list[tuple[str, str]] = []
        if project_id:
            candidates.append(("project", f"{base}&clientContext.projectId={project_id}"))
        candidates.append(("global", base))

        last_result: dict = {"error": "MEDIA_FETCH_FAILED"}
        for mode, url in candidates:
            result = await self._send("api_request", {
                "url": url,
                "method": "GET",
                "headers": read_headers(),
            }, timeout=timeout_sec)
            last_result = result
            status = result.get("status")
            if not _is_ws_error(result) and (not isinstance(status, int) or status < 400):
                direct_url = self._extract_media_url_from_result(result, media_id)
                if direct_url:
                    return result
                # HTTP 200 but no direct URL in payload: try scraping signed URLs from Flow tab.
                if project_id and timeout_sec >= 8:
                    pulled = await _pull_from_project_tab()
                    if pulled:
                        return pulled
                return result
            logger.info(
                "get_media failed (%s) media=%s status=%s err=%s",
                mode,
                media_id[:12],
                status,
                _extract_error_text(result)[:180],
            )

        # Fallback for image-like INTERNAL errors: ask extension for cached/project URLs.
        # Keep this path only for direct UI reads (long timeout), not bulk refresh loops.
        err_text = _extract_error_text(last_result)
        if project_id and timeout_sec >= 18 and _is_internal_error_text(err_text):
            pulled = await _pull_from_project_tab()
            if pulled:
                return pulled

        return last_result

    async def upload_image(self, image_base64: str, mime_type: str = "image/jpeg",
                            project_id: str = "", file_name: str = "image.jpg") -> dict:
        """Upload an image for use as start/end frame.

        Uses /v1/flow/uploadImage endpoint.
        Response: {media: {name: "uuid", ...}, workflow: {...}}
        We store media.name as the mediaId for video generation.
        """
        body = {
            "clientContext": {
                "projectId": project_id,
                "tool": "PINHOLE",
            },
            "fileName": file_name,
            "imageBytes": image_base64,
            "isHidden": False,
            "isUserUploaded": True,
            "mimeType": mime_type,
        }

        url = self._build_url("upload_image")
        result = await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
        }, timeout=60)

        # Extract media.name for convenience (used as mediaId in video gen)
        if not _is_ws_error(result):
            data = result.get("data", {})
            if isinstance(data, dict):
                media = data.get("media", {})
                if isinstance(media, dict) and media.get("name"):
                    result["_mediaId"] = media["name"]

        return result


def _is_ws_error(result: dict) -> bool:
    return bool(result.get("error")) or (isinstance(result.get("status"), int) and result["status"] >= 400)


# Singleton
_client: Optional[FlowClient] = None


def get_flow_client() -> FlowClient:
    global _client
    if _client is None:
        _client = FlowClient()
    return _client
