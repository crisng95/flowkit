"""FlowProvider — MediaProvider adapter for Google Flow (Chrome extension).

Wraps :class:`FlowClient` and exposes the provider interface.  All Flow
submit + poll logic lives here; OperationService only builds ProviderJobs.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import ssl
from typing import Optional

import aiohttp

from agent import config
from agent.config import VIDEO_POLL_INTERVAL, VIDEO_POLL_TIMEOUT
from agent.db import crud
from agent.services.omni_flash import (
    OMNI_FLASH_VALID_DURATIONS,
    generate_omni_flash_first_frame_video,
    generate_omni_flash_first_last_video,
)


def _omni_duration(requested) -> int:
    """Round a requested clip length up to the next Omni Flash step (4/6/8/10s).

    Rounding *down* would clip narration; anything past the max is capped.
    None/0 falls back to OMNI_FLASH_DURATION_S.
    """
    if not requested:
        return int(config.OMNI_FLASH_DURATION_S)
    want = float(requested)
    for step in OMNI_FLASH_VALID_DURATIONS:
        if step >= want - 1e-6:
            return step
    return OMNI_FLASH_VALID_DURATIONS[-1]
from agent.sdk.services.provider_base import (
    KIND_EDIT_IMAGE,
    KIND_IMAGE,
    KIND_UPSCALE,
    KIND_VIDEO,
    KIND_VIDEO_REFS,
    MediaProvider,
    ProviderCapabilities,
    ProviderJob,
)
from agent.utils.paths import scene_4k_path
from agent.utils.slugify import slugify
from agent.worker._parsing import (
    _extract_operations,
    _extract_uuid_from_url,
    _is_error,
)

logger = logging.getLogger(__name__)


def _save_raw_bytes(
    operations: list[dict], scene_id: str, project_slug: str, display_order: int
) -> str | None:
    """If operations contain rawBytes (inline 4K video), save to disk and return path."""
    for op in operations:
        raw_b64 = op.get("rawBytes")
        if not raw_b64:
            continue
        # Guard against extremely large payloads (>500MB base64 ≈ ~685M chars)
        if len(raw_b64) > 685_000_000:
            logger.warning("rawBytes too large (%d chars), skipping", len(raw_b64))
            continue
        try:
            video_data = base64.b64decode(raw_b64)
            path = scene_4k_path(project_slug, display_order, scene_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(video_data)
            logger.info("Saved rawBytes 4K video: %s (%d bytes)", path, len(video_data))
            return str(path)
        except Exception as e:
            logger.warning("Failed to save rawBytes: %s", e)
    return None


async def _poll_workflows(
    client,
    operations: list[dict],
    timeout: int,
) -> dict:
    """Poll workflow-mode operations (Low Priority). Flow returns MP4 binary
    inline as base64 in `video.encodedVideo` — decode and save to disk, then
    synthesize an OLD-schema success response with a file:// URL.

    The response shape is:
      {"name": "<media_id>", "video": {"encodedVideo": "<base64 MP4>", ...}}

    Detection logic:
    - "ready" = response is a dict with keys {"name","video"} where video.encodedVideo
      starts with AAAAI... (MP4 ftyp header in base64)
    - "still gen" = response missing video block, or encodedVideo missing/empty
    """
    poll_interval = VIDEO_POLL_INTERVAL
    elapsed = 0
    completed = {}  # media_id → local_path

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        for op in operations:
            mid = op.get("_primary_media_id", "")
            if not mid or mid in completed:
                continue
            media_resp = await client.get_media(mid)
            status = media_resp.get("status")
            if status != 200:
                logger.debug("Workflow media %s not ready (status=%s)", mid[:8], status)
                continue

            # Direct top-level (not wrapped in `data`)
            payload = media_resp.get("data", media_resp) if isinstance(media_resp.get("data"), dict) and "video" in media_resp.get("data", {}) else media_resp
            video_block = payload.get("video", {}) if isinstance(payload, dict) else {}
            encoded = video_block.get("encodedVideo", "") if isinstance(video_block, dict) else ""

            if not encoded:
                continue
            try:
                binary = base64.b64decode(encoded)
            except Exception as e:
                logger.warning("Workflow media %s: failed to decode encodedVideo: %s", mid[:8], e)
                continue
            # Validate MP4 magic: real video starts with `ftyp` box at bytes 4-8.
            # While generating, Flow returns metadata payload (~1-2KB) — skip until real MP4.
            is_mp4 = len(binary) >= 12 and binary[4:8] == b"ftyp"
            if not is_mp4:
                logger.debug("Workflow media %s still generating (got %d bytes, not MP4)",
                             mid[:8], len(binary))
                continue
            out_dir = "output/_workflow_videos"
            os.makedirs(out_dir, exist_ok=True)
            out_path = f"{out_dir}/{mid}.mp4"
            with open(out_path, "wb") as f:
                f.write(binary)
            completed[mid] = {"path": out_path, "size": len(binary)}
            logger.info("Workflow media %s ready: saved %d bytes → %s",
                        mid[:8], len(binary), out_path)

        if len(completed) == len(operations):
            synth_ops = []
            for op in operations:
                mid = op.get("_primary_media_id", "")
                wf_name = op.get("operation", {}).get("name", "")
                local = completed.get(mid, {}).get("path", "")
                # Use file:// so downstream sees a URL-shaped string
                local_url = f"file://{os.path.abspath(local)}" if local else ""
                synth_ops.append({
                    "operation": {
                        "name": wf_name,
                        "metadata": {"video": {"mediaId": mid, "fifeUrl": local_url}},
                    },
                    "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                })
            logger.info("All %d workflow(s) completed after %ds", len(operations), elapsed)
            return {"data": {"operations": synth_ops}}

    logger.warning("Workflow polling timed out after %ds. Done=%d/%d",
                   timeout, len(completed), len(operations))
    return {"error": f"Workflow polling timeout after {timeout}s"}


async def _poll_operations(
    client,
    operations: list[dict],
    timeout: int = VIDEO_POLL_TIMEOUT,
) -> dict:
    """Poll until all operations complete or timeout.

    Two polling paths:
    - OLD schema → check_video_status(operations)
    - Workflow mode (Low Priority) → poll get_media(primaryMediaId) until ready
    """
    if not operations:
        return {"error": "No operations to poll"}

    # Workflow-mode polling: poll media endpoint for each primaryMediaId
    if all(op.get("_workflow_mode") for op in operations):
        return await _poll_workflows(client, operations, timeout)

    poll_interval = VIDEO_POLL_INTERVAL
    elapsed = 0
    current_ops = operations
    # The batch path attaches the operation's own grumble ("Media not found.")
    # to a still-pending round. It is a diagnostic, not a verdict — finished
    # jobs report it too — so it is only worth quoting if we time out.
    last_complaint = None

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        status_result = await client.check_video_status(current_ops)
        if _is_error(status_result):
            logger.warning("Status poll error: %s", status_result.get("error"))
            continue

        data = status_result.get("data", status_result)
        ops = data.get("operations", [])
        if not ops:
            continue

        current_ops = ops
        all_done = True
        has_error = False
        error_msg = ""

        for op in ops:
            if op.get("complaint"):
                last_complaint = op["complaint"]
            status = op.get("status", "")
            if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                continue
            elif status == "MEDIA_GENERATION_STATUS_FAILED":
                op_name = op.get('operation', {}).get('name', '?')
                # Log full operation for debugging failure reason
                import json as _json
                logger.error("Operation FAILED: name=%s full=%s", op_name, _json.dumps(op)[:1000])
                error_msg = f"Operation failed: {op_name}"
                has_error = True
                break
            else:
                all_done = False

        if has_error:
            return {"error": error_msg}
        if all_done:
            logger.info("All %d operations completed after %ds", len(ops), elapsed)
            return {"data": data}

    detail = f": {last_complaint}" if last_complaint else ""
    return {"error": f"Polling timeout after {timeout}s{detail}"}


async def _upload_character_image(client, char: dict, project_id: str) -> str | None:
    """Download character reference image and upload to Google Flow to get media_id."""
    ref_url = char.get("reference_image_url")
    if not ref_url:
        return None

    try:
        try:
            import certifi
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ssl_ctx = ssl.create_default_context()
        async with aiohttp.ClientSession() as session:
            async with session.get(ref_url, ssl=ssl_ctx) as resp:
                if resp.status != 200:
                    logger.error("Failed to download character image: HTTP %d", resp.status)
                    return None
                image_bytes = await resp.read()
                content_type = resp.headers.get("content-type", "image/jpeg")

        if "png" in content_type:
            mime = "image/png"
        elif "gif" in content_type:
            mime = "image/gif"
        else:
            mime = "image/jpeg"

        ext = mime.split("/")[-1]
        file_name = f"{char.get('name', 'character')}.{ext}"

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        result = await client.upload_image(
            encoded, mime_type=mime, project_id=project_id, file_name=file_name,
        )

        if result.get("_mediaId"):
            return result["_mediaId"]

        data = result.get("data", {})
        if isinstance(data, dict):
            media = data.get("media", {})
            if isinstance(media, dict) and media.get("name"):
                return media["name"]

        return None
    except Exception as e:
        logger.exception("Failed to upload character image: %s", e)
        return None


class FlowProvider(MediaProvider):
    """Google Flow backend — direct provider via the Chrome extension."""

    name = "flow"
    display_name = "Google Flow"
    capabilities = ProviderCapabilities(
        generate_image=True,
        edit_image=True,
        generate_video_i2v=True,
        generate_video_r2v=True,
        upscale=True,
        max_concurrent=config.FLOW_MAX_CONCURRENT,
        cooldown_s=config.FLOW_COOLDOWN_S,
    )

    def __init__(self, client) -> None:
        self._client = client

    def is_available(self) -> bool:
        """Flow is available only while the Chrome extension is connected."""
        try:
            return bool(self._client.connected)
        except Exception:
            return False

    # ── MediaProvider interface ──────────────────────────────────────────

    async def run(self, job: ProviderJob) -> dict:
        if job.kind == KIND_IMAGE:
            return await self._run_image(job)
        if job.kind == KIND_EDIT_IMAGE:
            return await self._run_edit_image(job)
        if job.kind == KIND_VIDEO:
            return await self._run_video(job)
        if job.kind == KIND_VIDEO_REFS:
            return await self._run_video_refs(job)
        if job.kind == KIND_UPSCALE:
            return await self._run_upscale(job)
        if job.kind == KIND_AUDIO:
            return {"error": "TTS/audio is not supported by the flow provider — "
                             "use the assistant provider or local TTS"}
        return {"error": f"FlowProvider: unknown job kind '{job.kind}'"}

    def needs_media_id_registration(self) -> bool:
        # Flow tracks media by UUID media_id — generated images must be
        # uploaded back to obtain one.
        return True

    async def register_existing_image(
        self, url: str, *, name: str = "", project_id: str = ""
    ) -> dict:
        mid = await _upload_character_image(
            self._client, {"name": name, "reference_image_url": url}, project_id
        )
        if mid:
            return {"data": {"media": [{"name": mid}], "url": url}}
        # Fallback: Flow sometimes returns UUID-bearing URLs directly.
        uuid_from_url = _extract_uuid_from_url(url)
        if uuid_from_url:
            logger.info("FlowProvider: extracted UUID from URL for '%s'", name)
            return {"data": {"media": [{"name": uuid_from_url}], "url": url}}
        return {"error": f"FlowProvider: could not register image for '{name}'"}

    # ── kind implementations ─────────────────────────────────────────────

    async def _run_image(self, job: ProviderJob) -> dict:
        ex = job.extra
        return await self._client.generate_images(
            prompt=job.prompt,
            project_id=ex.get("project_id", "0"),
            aspect_ratio=ex.get("aspect", "IMAGE_ASPECT_RATIO_PORTRAIT"),
            user_paygate_tier=ex.get("tier", "PAYGATE_TIER_TWO"),
            character_media_ids=ex.get("character_media_ids"),
        )

    async def _run_edit_image(self, job: ProviderJob) -> dict:
        ex = job.extra
        if not ex.get("source_media_id"):
            return {"error": "No source image to edit — generate a scene image first"}
        return await self._client.edit_image(
            prompt=job.prompt,
            source_media_id=ex.get("source_media_id", ""),
            project_id=ex.get("project_id", "0"),
            aspect_ratio=ex.get("aspect", "IMAGE_ASPECT_RATIO_PORTRAIT"),
            user_paygate_tier=ex.get("tier", "PAYGATE_TIER_ONE"),
            character_media_ids=ex.get("character_media_ids"),
        )

    async def _run_video(self, job: ProviderJob) -> dict:
        """i2v: submit + poll. Re-polls a previous submission on retry."""
        ex = job.extra
        request_id = ex.get("request_id", "")

        existing_op = None
        if request_id:
            req_row = await crud.get_request(request_id)
            existing_op = req_row.get("request_id") if req_row else None

        # A bare uuid is the operation id, and looking it up in the project
        # listing is exactly what the status poll does — resubmitting instead
        # would abandon a running render and pay for a second one.
        if existing_op:
            logger.info("Video gen already submitted (op=%s), re-polling", existing_op[:30])
            operations = [{"operation": {"name": existing_op}, "status": "MEDIA_GENERATION_STATUS_PENDING"}]
            return await _poll_operations(self._client, operations)

        # The project's video_model_family picks the Flow family. Omni Flash
        # returns the same batch-operation shape as Veo, so polling and the
        # retry-repoll guard above are shared.
        if ex.get("model_family") == "omni_flash":
            common = dict(
                start_image_media_id=ex.get("start_media_id", ""),
                prompt=job.prompt,
                project_id=ex.get("project_id", "0"),
                scene_id=ex.get("scene_id", ""),
                duration_s=_omni_duration(ex.get("duration_s")),
                resolution=ex.get("resolution") or config.OMNI_FLASH_RESOLUTION,
                aspect_ratio=ex.get("aspect", "VIDEO_ASPECT_RATIO_PORTRAIT"),
                user_paygate_tier=ex.get("tier", "PAYGATE_TIER_TWO"),
            )
            end_id = ex.get("end_media_id")
            if end_id:
                submit_result = await generate_omni_flash_first_last_video(
                    end_image_media_id=end_id, **common)
            else:
                submit_result = await generate_omni_flash_first_frame_video(**common)
        else:
            submit_result = await self._client.generate_video(
                start_image_media_id=ex.get("start_media_id", ""),
                prompt=job.prompt,
                project_id=ex.get("project_id", "0"),
                scene_id=ex.get("scene_id", ""),
                aspect_ratio=ex.get("aspect", "VIDEO_ASPECT_RATIO_PORTRAIT"),
                end_image_media_id=ex.get("end_media_id"),
                user_paygate_tier=ex.get("tier", "PAYGATE_TIER_TWO"),
            )

        if _is_error(submit_result):
            logger.error("[DEBUG] Video gen submit_result IS_ERROR: %s", str(submit_result)[:2000])
            return submit_result

        operations = _extract_operations(submit_result)
        if not operations:
            logger.error("[DEBUG] Video gen NO_OPERATIONS submit_result: %s", str(submit_result)[:2000])
            return {"error": "Video gen returned no operations"}

        op_name = operations[0].get("operation", {}).get("name", "")
        if request_id:
            await crud.update_request(request_id, request_id=op_name)

        status = operations[0].get("status", "")
        if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
            logger.info("Video gen completed immediately")
            return submit_result
        if status == "MEDIA_GENERATION_STATUS_FAILED":
            return {"error": "Video generation failed immediately"}

        logger.info("Video gen submitted, polling %d operations...", len(operations))
        return await _poll_operations(self._client, operations)

    async def _run_video_refs(self, job: ProviderJob) -> dict:
        """r2v: submit + poll. Re-polls a previous submission on retry."""
        ex = job.extra
        request_id = ex.get("request_id", "")
        ref_ids = ex.get("ref_media_ids", [])

        if not ref_ids:
            return {"error": "No valid reference media_ids for r2v"}

        # Check if already submitted (op_name saved from previous attempt)
        existing_op = None
        if request_id:
            req_row = await crud.get_request(request_id)
            existing_op = req_row.get("request_id") if req_row else None

        if existing_op:
            logger.info("R2V already submitted (op=%s), re-polling", existing_op[:30])
            operations = [{"operation": {"name": existing_op}, "status": "MEDIA_GENERATION_STATUS_PENDING"}]
            return await _poll_operations(self._client, operations)

        submit_result = await self._client.generate_video_from_references(
            reference_media_ids=ref_ids,
            prompt=job.prompt,
            project_id=ex.get("project_id", "0"),
            scene_id=ex.get("scene_id", ""),
            aspect_ratio=ex.get("aspect", "VIDEO_ASPECT_RATIO_PORTRAIT"),
            user_paygate_tier=ex.get("tier", "PAYGATE_TIER_TWO"),
        )

        if _is_error(submit_result):
            return submit_result

        operations = _extract_operations(submit_result)
        if not operations:
            return {"error": "R2V returned no operations"}

        op_name = operations[0].get("operation", {}).get("name", "")
        if request_id:
            await crud.update_request(request_id, request_id=op_name)

        status = operations[0].get("status", "")
        if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
            logger.info("R2V completed immediately")
            return submit_result
        if status == "MEDIA_GENERATION_STATUS_FAILED":
            return {"error": "R2V failed immediately"}

        logger.info("R2V submitted with %d refs, polling %d operations...", len(ref_ids), len(operations))
        return await _poll_operations(self._client, operations)

    async def _run_upscale(self, job: ProviderJob) -> dict:
        ex = job.extra
        request_id = ex.get("request_id", "")

        existing_op = None
        if request_id:
            req_row = await crud.get_request(request_id)
            existing_op = req_row.get("request_id") if req_row else None

        if existing_op:
            # Already submitted — just re-poll
            logger.info("Upscale already submitted (op=%s), re-polling", existing_op[:30])
            operations = [{"operation": {"name": existing_op}, "status": "MEDIA_GENERATION_STATUS_PENDING"}]
            return await _poll_operations(self._client, operations, timeout=300)

        submit_result = await self._client.upscale_video(
            media_id=ex.get("video_media_id", ""),
            scene_id=ex.get("scene_id", ""),
            aspect_ratio=ex.get("aspect", "VIDEO_ASPECT_RATIO_PORTRAIT"),
        )

        if _is_error(submit_result):
            return submit_result

        operations = _extract_operations(submit_result)
        if not operations:
            return {"error": "Upscale returned no operations"}

        # Check for inline rawBytes (4K video data returned directly)
        project_slug = ex.get("project_slug") or slugify(ex.get("project_id", "unnamed"))
        display_order = ex.get("display_order", 0)
        scene_id = ex.get("scene_id", "")
        raw_path = _save_raw_bytes(operations, scene_id, project_slug, display_order)
        if raw_path:
            logger.info("Upscale returned inline 4K video, saved to %s", raw_path)
            # Inject saved path into result for downstream parsing
            if not operations[0].get("operation"):
                operations[0]["operation"] = {}
            operations[0]["operation"].setdefault("metadata", {}).setdefault("video", {})["fifeUrl"] = raw_path
            operations[0]["status"] = "MEDIA_GENERATION_STATUS_SUCCESSFUL"
            return {"data": {"operations": operations}}

        op_name = operations[0].get("operation", {}).get("name", "")
        if request_id:
            await crud.update_request(request_id, request_id=op_name)

        status = operations[0].get("status", "")
        if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
            logger.info("Upscale completed immediately")
            return submit_result
        if status == "MEDIA_GENERATION_STATUS_FAILED":
            return {"error": "Upscale failed immediately"}

        logger.info("Upscale submitted, polling %d operations...", len(operations))
        poll_result = await _poll_operations(self._client, operations, timeout=300)

        # Check poll result for rawBytes too
        poll_data = poll_result.get("data", poll_result)
        poll_ops = poll_data.get("operations", [])
        if poll_ops:
            raw_path = _save_raw_bytes(poll_ops, scene_id, project_slug, display_order)
            if raw_path:
                logger.info("Poll returned inline 4K video, saved to %s", raw_path)
                poll_ops[0].setdefault("operation", {}).setdefault("metadata", {}).setdefault("video", {})["fifeUrl"] = raw_path

        return poll_result


# Re-exported for any code still importing from operations (moved here).
__all__ = [
    "FlowProvider",
    "_poll_operations",
    "_poll_workflows",
    "_save_raw_bytes",
    "_upload_character_image",
]
