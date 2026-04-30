"""Direct Flow API endpoints — for manual operations outside the queue."""
from __future__ import annotations

import base64
import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent.config import OUTPUT_DIR
from agent.db import crud
from agent.materials import get_material
from agent.sdk.services.result_handler import parse_result
from agent.services.flow_client import get_flow_client

router = APIRouter(prefix="/flow", tags=["flow"])
logger = logging.getLogger(__name__)
_MANUAL_PROJECT_ID: str | None = None
_LOCAL_MEDIA_ROOT = OUTPUT_DIR.resolve()


class GenerateImageRequest(BaseModel):
    prompt: str
    project_id: str
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    character_media_ids: Optional[list[str]] = None
    image_model_key: Optional[str] = None


class GenerateVideoRequest(BaseModel):
    start_image_media_id: str
    prompt: str
    project_id: str
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    end_image_media_id: Optional[str] = None
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    video_model_key: Optional[str] = None


class GenerateVideoRefsRequest(BaseModel):
    reference_media_ids: list[str]
    prompt: str
    project_id: str
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    video_model_key: Optional[str] = None


class UpscaleVideoRequest(BaseModel):
    media_id: str
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    resolution: str = "VIDEO_RESOLUTION_4K"


class UploadImageRequest(BaseModel):
    file_path: str  # absolute path to local image file
    project_id: str = ""
    file_name: str = "image.png"


class CheckStatusRequest(BaseModel):
    operations: list[dict]


class EditImageRequest(BaseModel):
    prompt: str
    source_media_id: str
    project_id: str
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    image_model_key: Optional[str] = None


class ManualContextRequest(BaseModel):
    project_id: Optional[str] = None
    create_if_missing: bool = True
    user_paygate_tier: Optional[str] = None


class ManualImageItem(BaseModel):
    prompt: str
    aspect_ratio: Optional[str] = None
    style: Optional[str] = None
    character_media_ids: Optional[list[str]] = None
    image_model_key: Optional[str] = None


class ManualImageBatchRequest(BaseModel):
    project_id: Optional[str] = None
    material: Optional[str] = "realistic"
    custom_style: Optional[str] = None
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: Optional[str] = None
    image_model_key: Optional[str] = None
    items: list[ManualImageItem] = Field(default_factory=list)


class ManualVideoItem(BaseModel):
    prompt: str
    start_image_media_id: str
    end_image_media_id: Optional[str] = None
    scene_id: Optional[str] = None
    aspect_ratio: Optional[str] = None
    style: Optional[str] = None
    video_model_key: Optional[str] = None


class ManualVideoBatchRequest(BaseModel):
    project_id: Optional[str] = None
    material: Optional[str] = "realistic"
    custom_style: Optional[str] = None
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: Optional[str] = None
    video_model_key: Optional[str] = None
    items: list[ManualVideoItem] = Field(default_factory=list)


def _extract_first_url(payload: Any) -> str | None:
    def _is_direct_media_url(url: str) -> bool:
        low = (url or "").lower()
        if not low.startswith("http"):
            return False
        if "media.getmediaurlredirect" in low:
            return False
        if low.startswith("https://flow-content.google/"):
            return True
        if low.startswith("https://storage.googleapis.com/"):
            return True
        if "googleusercontent.com/" in low:
            return True
        return False

    def _extract_any_url(node: Any) -> str | None:
        if isinstance(node, dict):
            for key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri"):
                value = node.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
            for value in node.values():
                found = _extract_any_url(value)
                if found:
                    return found
            return None
        if isinstance(node, list):
            for item in node:
                found = _extract_any_url(item)
                if found:
                    return found
        return None

    if isinstance(payload, dict):
        for key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri"):
            value = payload.get(key)
            if isinstance(value, str) and _is_direct_media_url(value):
                return value
        for value in payload.values():
            found = _extract_first_url(value)
            if found:
                return found
        return _extract_any_url(payload)
    if isinstance(payload, list):
        for item in payload:
            found = _extract_first_url(item)
            if found:
                return found
        return _extract_any_url(payload)
    return None


def _walk_values(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_values(value)
        return
    if isinstance(node, list):
        for item in node:
            yield from _walk_values(item)


def _extract_project_id_from_flow_response(flow_result: dict) -> str | None:
    payload = flow_result.get("data", flow_result)
    candidates: list[str] = []
    for obj in _walk_values(payload):
        if not isinstance(obj, dict):
            continue
        pid = obj.get("projectId")
        if isinstance(pid, str) and pid.strip():
            candidates.append(pid.strip())
    unique = list(dict.fromkeys(candidates))
    if not unique:
        return None
    if len(unique) > 1:
        logger.warning("Multiple projectId candidates in Flow response, using first: %s", unique)
    return unique[0]


def _extract_flow_error_text(flow_result: dict) -> str | None:
    payload = flow_result.get("data", flow_result)
    for obj in _walk_values(payload):
        if not isinstance(obj, dict):
            continue
        err = obj.get("error")
        if isinstance(err, str) and err.strip():
            return err.strip()
        if isinstance(err, dict):
            msg = err.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
            err_json = err.get("json")
            if isinstance(err_json, dict):
                nested = err_json.get("message")
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()
    return None


def _is_internal_image_error(flow_result: dict, parsed_error: str | None) -> bool:
    candidates: list[str] = []
    if parsed_error:
        candidates.append(parsed_error)
    nested_error = _extract_flow_error_text(flow_result)
    if nested_error:
        candidates.append(nested_error)
    raw_error = flow_result.get("error")
    if isinstance(raw_error, str) and raw_error.strip():
        candidates.append(raw_error.strip())

    merged = " | ".join(candidates).lower()
    return "internal error" in merged or "internal error encountered" in merged


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().split())


def _compose_prompt(base_prompt: str, *style_parts: Optional[str]) -> str:
    base = _normalize_text(base_prompt)
    style = " ".join(part for part in (_normalize_text(p) for p in style_parts) if part)
    if style and base:
        return f"{style}. {base}"
    return style or base


def _resolve_material_prefix(material_id: Optional[str]) -> str:
    if not material_id:
        return ""
    material = get_material(material_id)
    if not material:
        raise HTTPException(400, f"Unknown material: '{material_id}'")
    return _normalize_text(material.get("scene_prefix") or material.get("style_instruction") or "")


def _extract_operations(raw: dict) -> list[dict]:
    data = raw.get("data", raw)
    if isinstance(data, dict):
        ops = data.get("operations")
        if isinstance(ops, list):
            return ops
    return []


def _flow_status_code(value: Any, default: int = 502) -> int:
    try:
        code = int(value)
    except Exception:
        return default
    return code if 400 <= code <= 599 else default


def _flow_error_detail(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, str) and err.strip():
            return err.strip()
        nested = payload.get("data")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
        if nested is not None:
            return str(nested)
    return str(payload)


def _derive_video_submit_status(operations: list[dict], parse_success: bool) -> str:
    if not operations:
        return "COMPLETED" if parse_success else "FAILED"
    statuses = [op.get("status") for op in operations if isinstance(op, dict)]
    if any(s == "MEDIA_GENERATION_STATUS_FAILED" for s in statuses):
        return "FAILED"
    if statuses and all(s == "MEDIA_GENERATION_STATUS_SUCCESSFUL" for s in statuses):
        return "COMPLETED"
    return "SUBMITTED"


def _resolve_local_media_path(raw_path: str) -> Path:
    if not raw_path:
        raise HTTPException(400, "path is required")
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        raise HTTPException(400, "path must be absolute")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(404, f"Local media not found: {raw_path}")
    except Exception:
        raise HTTPException(400, "Invalid local media path")

    try:
        resolved.relative_to(_LOCAL_MEDIA_ROOT)
    except ValueError:
        raise HTTPException(403, "Access denied for requested path")

    if not resolved.is_file():
        raise HTTPException(404, "Local media is not a file")
    return resolved


async def _resolve_user_tier(client, preferred: Optional[str]) -> str:
    if preferred and preferred.strip():
        return preferred.strip()
    try:
        result = await client.get_credits()
        data = result.get("data", result)
        tier = data.get("userPaygateTier")
        if isinstance(tier, str) and tier.strip():
            return tier.strip()
    except Exception:
        pass
    return "PAYGATE_TIER_ONE"


async def _resolve_manual_project_id(client, requested_project_id: Optional[str], create_if_missing: bool = True) -> str:
    global _MANUAL_PROJECT_ID

    if requested_project_id and requested_project_id.strip():
        _MANUAL_PROJECT_ID = requested_project_id.strip()
        return _MANUAL_PROJECT_ID

    if _MANUAL_PROJECT_ID:
        return _MANUAL_PROJECT_ID

    if not create_if_missing:
        raise HTTPException(400, "No project available. Provide project_id or create one first.")

    title = f"FlowKit Manual {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    flow_result = await client.create_project(title, "PINHOLE")
    if flow_result.get("error"):
        raise HTTPException(502, f"Flow createProject error: {flow_result['error']}")

    status = flow_result.get("status")
    if isinstance(status, int) and status >= 400:
        detail = _extract_flow_error_text(flow_result) or "Unknown Flow error"
        raise HTTPException(502, f"Flow createProject failed (HTTP {status}): {detail}")

    pid = _extract_project_id_from_flow_response(flow_result)
    if not pid:
        detail = _extract_flow_error_text(flow_result)
        if detail:
            raise HTTPException(502, f"Failed to parse Flow createProject response: {detail}")
        raise HTTPException(502, "Failed to parse Flow createProject response: projectId not found")

    _MANUAL_PROJECT_ID = pid
    logger.info("Manual flow project created: %s", pid)
    return pid


@router.get("/status")
async def extension_status():
    """Check if extension is connected."""
    client = get_flow_client()
    status = await client.get_extension_status()
    return status


@router.get("/local-media")
async def local_media(path: str = Query(..., description="Absolute local path under output/")):
    """Serve local generated media files to Electron renderer safely."""
    resolved = _resolve_local_media_path(path)
    mime = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
    return FileResponse(path=resolved, media_type=mime, filename=resolved.name)


@router.get("/credits")
async def get_credits(force: bool = Query(False)):
    """Get user credits from Google Flow."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.get_credits(force=force)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result.get("data", result)


@router.post("/generate-image")
async def generate_image(body: GenerateImageRequest):
    """Generate image directly (bypasses queue)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.generate_images(**body.model_dump())
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/generate-video")
async def generate_video(body: GenerateVideoRequest):
    """Submit video generation (returns operations for polling)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.generate_video(**body.model_dump(exclude_none=True))
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/generate-video-refs")
async def generate_video_refs(body: GenerateVideoRefsRequest):
    """Submit r2v video generation from reference images."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.generate_video_from_references(**body.model_dump())
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/upscale-video")
async def upscale_video(body: UpscaleVideoRequest):
    """Submit video upscale (returns operations for polling)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.upscale_video(**body.model_dump())
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/check-status")
async def check_status(body: CheckStatusRequest):
    """Check video generation status."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.check_video_status(body.operations)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result.get("data", result)


@router.post("/refresh-urls/{project_id}")
async def refresh_project_urls(project_id: str):
    """Bulk refresh all media URLs for a project via per-media get_media calls."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.refresh_project_urls(project_id)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result


@router.get("/media/{media_id}")
async def get_media(
    media_id: str,
    project_id: Optional[str] = Query(
        default=None,
        description="Optional Flow project_id context. Pass app project ID to avoid cross-project lookup.",
    ),
):
    """Get media metadata + fresh signed URL from Google Flow.

    Returns the raw response which should contain a fresh fifeUrl/servingUri.
    Use this to refresh expired GCS signed URLs.
    """
    client = get_flow_client()
    local_url = await client.find_local_media_url(media_id, project_id=project_id)
    if local_url:
        return {"url": local_url, "fifeUrl": local_url, "servingUri": local_url, "source": "local_cache"}
    if not client.connected:
        raise HTTPException(503, "Extension not connected")

    result = await client.get_media(media_id, project_id=project_id)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    status = result.get("status", 200)
    if isinstance(status, int) and status >= 400:
        raise HTTPException(status, result.get("data", "Media not found"))
    payload = result.get("data", result)
    fresh_url = _extract_first_url(payload)
    if isinstance(fresh_url, str) and "media.getMediaUrlRedirect" in fresh_url:
        fresh_url = None
    if isinstance(fresh_url, str):
        local_cached = await client.cache_media_locally(media_id, fresh_url, project_id=project_id)
        if isinstance(local_cached, str) and local_cached:
            fresh_url = local_cached
    if isinstance(payload, dict):
        merged = dict(payload)
        if fresh_url:
            merged["url"] = fresh_url
        return merged
    if fresh_url:
        return {"data": payload, "url": fresh_url}
    return payload


@router.post("/edit-image")
async def edit_image(body: EditImageRequest):
    """Edit an existing image using IMAGE_INPUT_TYPE_BASE_IMAGE (bypasses queue)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.edit_image(
        body.prompt, body.source_media_id, body.project_id,
        aspect_ratio=body.aspect_ratio,
        user_paygate_tier=body.user_paygate_tier,
        image_model_key=body.image_model_key,
    )
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/upload-image")
async def upload_image(body: UploadImageRequest):
    """Upload a local image file to Google Flow and get a media_id."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    try:
        with open(body.file_path, "rb") as f:
            image_bytes = f.read()
    except FileNotFoundError:
        raise HTTPException(404, f"File not found: {body.file_path}")
    b64 = base64.b64encode(image_bytes).decode()
    mime = mimetypes.guess_type(body.file_path)[0] or "image/png"
    try:
        result = await client.upload_image(b64, mime_type=mime, project_id=body.project_id, file_name=body.file_name)
    except Exception as exc:
        raise HTTPException(502, f"Flow upload request failed: {exc}")

    if not isinstance(result, dict):
        raise HTTPException(502, f"Unexpected upload response type: {type(result).__name__}")

    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(_flow_status_code(result.get("status"), 502), _flow_error_detail(result))
    media_id = result.get("_mediaId")
    if not media_id:
        raise HTTPException(502, "Upload succeeded but no media_id returned")

    media_url: str | None = None
    try:
        media_resp = await client.get_media(
            media_id,
            project_id=(body.project_id or None),
        )
        if not media_resp.get("error"):
            media_url = _extract_first_url(media_resp.get("data", media_resp))
    except Exception as exc:
        # Non-fatal: upload is already successful; URL can be refreshed later.
        logger.warning("upload_image get_media failed for %s: %s", media_id, exc)

    return {"media_id": media_id, "url": media_url, "raw": result.get("data", result)}


@router.post("/manual/context")
async def manual_context(body: ManualContextRequest):
    """Resolve runtime context for standalone manual generation pages."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    project_id = await _resolve_manual_project_id(client, body.project_id, create_if_missing=body.create_if_missing)
    tier = await _resolve_user_tier(client, body.user_paygate_tier)
    return {
        "project_id": project_id,
        "user_paygate_tier": tier,
        "project_source": "manual_cache_or_active",
    }


@router.post("/manual/images")
async def manual_generate_images(body: ManualImageBatchRequest):
    """Generate standalone images from many prompts (not tied to scene/request queue)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    if not body.items:
        raise HTTPException(400, "items is required")

    project_id = await _resolve_manual_project_id(client, body.project_id, create_if_missing=True)
    tier = await _resolve_user_tier(client, body.user_paygate_tier)
    material_prefix = _resolve_material_prefix(body.material)
    shared_custom_style = _normalize_text(body.custom_style)

    items_out: list[dict] = []
    for index, item in enumerate(body.items):
        full_prompt = _compose_prompt(item.prompt, material_prefix, shared_custom_style, item.style)
        if not full_prompt:
            items_out.append({
                "index": index,
                "status": "FAILED",
                "error": "Prompt is empty after style merge",
                "prompt": item.prompt,
                "full_prompt": full_prompt,
                "media_id": None,
                "url": None,
            })
            continue

        selected_image_model = _normalize_text(item.image_model_key or body.image_model_key) or None
        raw = await client.generate_images(
            prompt=full_prompt,
            project_id=project_id,
            aspect_ratio=item.aspect_ratio or body.aspect_ratio,
            user_paygate_tier=tier,
            character_media_ids=item.character_media_ids,
            image_model_key=selected_image_model,
        )
        parsed = parse_result(raw, "GENERATE_IMAGE")

        # Flow đôi khi trả "Internal error encountered" khi model key không phù hợp.
        # Thử lại 1 lần bằng model mặc định để tăng tỷ lệ thành công.
        retried_with_default_model = False
        if (
            not parsed.success
            and selected_image_model
            and _is_internal_image_error(raw, parsed.error)
        ):
            retry_raw = await client.generate_images(
                prompt=full_prompt,
                project_id=project_id,
                aspect_ratio=item.aspect_ratio or body.aspect_ratio,
                user_paygate_tier=tier,
                character_media_ids=item.character_media_ids,
                image_model_key=None,
            )
            retry_parsed = parse_result(retry_raw, "GENERATE_IMAGE")
            retried_with_default_model = True
            if retry_parsed.success:
                raw = retry_raw
                parsed = retry_parsed
                selected_image_model = None
            else:
                retry_error_text = retry_parsed.error or _extract_flow_error_text(retry_raw)
                if retry_error_text:
                    parsed.error = retry_error_text

        url = parsed.url or _extract_first_url(raw.get("data", raw))
        items_out.append({
            "index": index,
            "status": "COMPLETED" if parsed.success else "FAILED",
            "error": parsed.error if not parsed.success else None,
            "prompt": item.prompt,
            "full_prompt": full_prompt,
            "aspect_ratio": item.aspect_ratio or body.aspect_ratio,
            "image_model_key": selected_image_model,
            "retried_with_default_model": retried_with_default_model,
            "media_id": parsed.media_id,
            "url": url,
        })

    return {
        "project_id": project_id,
        "user_paygate_tier": tier,
        "material": body.material,
        "custom_style": body.custom_style,
        "image_model_key": _normalize_text(body.image_model_key) or None,
        "total": len(items_out),
        "items": items_out,
    }


@router.post("/manual/videos")
async def manual_generate_videos(body: ManualVideoBatchRequest):
    """Submit standalone videos from prompts + start/end frame media IDs."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    if not body.items:
        raise HTTPException(400, "items is required")

    project_id = await _resolve_manual_project_id(client, body.project_id, create_if_missing=True)
    tier = await _resolve_user_tier(client, body.user_paygate_tier)
    material_prefix = _resolve_material_prefix(body.material)
    shared_custom_style = _normalize_text(body.custom_style)

    items_out: list[dict] = []
    for index, item in enumerate(body.items):
        full_prompt = _compose_prompt(item.prompt, material_prefix, shared_custom_style, item.style)
        if not full_prompt:
            items_out.append({
                "index": index,
                "status": "FAILED",
                "error": "Prompt is empty after style merge",
                "prompt": item.prompt,
                "full_prompt": full_prompt,
                "operations": [],
                "media_id": None,
                "url": None,
            })
            continue

        selected_video_model = _normalize_text(item.video_model_key or body.video_model_key) or None
        scene_id = item.scene_id or str(uuid.uuid4())
        raw = await client.generate_video(
            start_image_media_id=item.start_image_media_id,
            prompt=full_prompt,
            project_id=project_id,
            scene_id=scene_id,
            aspect_ratio=item.aspect_ratio or body.aspect_ratio,
            end_image_media_id=item.end_image_media_id,
            user_paygate_tier=tier,
            video_model_key=selected_video_model,
        )

        parsed = parse_result(raw, "GENERATE_VIDEO")
        operations = _extract_operations(raw)
        status = _derive_video_submit_status(operations, parsed.success)
        url = parsed.url or _extract_first_url(raw.get("data", raw))
        error_text = parsed.error
        if status == "FAILED" and not error_text:
            error_text = _extract_flow_error_text(raw) or "Video generation failed"

        items_out.append({
            "index": index,
            "status": status,
            "error": error_text,
            "prompt": item.prompt,
            "full_prompt": full_prompt,
            "scene_id": scene_id,
            "aspect_ratio": item.aspect_ratio or body.aspect_ratio,
            "video_model_key": selected_video_model,
            "start_image_media_id": item.start_image_media_id,
            "end_image_media_id": item.end_image_media_id,
            "operations": operations,
            "media_id": parsed.media_id,
            "url": url,
        })

    return {
        "project_id": project_id,
        "user_paygate_tier": tier,
        "material": body.material,
        "custom_style": body.custom_style,
        "video_model_key": _normalize_text(body.video_model_key) or None,
        "total": len(items_out),
        "items": items_out,
    }
