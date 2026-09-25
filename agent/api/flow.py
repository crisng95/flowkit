"""Direct Flow API endpoints — for manual operations outside the queue."""
import base64
import mimetypes

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from typing import Literal, Optional

from agent.config import (
    FLOW_PROJECT_ID, FLOW_ALLOW_DEGRADED,
    FLOW_GENERATION_MIN_INTERVAL_S, FLOW_GENERATION_MAX_CONCURRENT,
    FLOW_UNUSUAL_ACTIVITY_COOLDOWN_S,
)
from agent.services.flow_client import get_flow_client
from agent.services.flow_project_session import current_session_project, ensure_session_project
from agent.services.omni_flash import (
    check_omni_flash_status,
    generate_omni_flash_first_frame_video,
    generate_omni_flash_first_last_video,
    generate_omni_flash_text_video,
    generate_omni_flash_video,
)

router = APIRouter(prefix="/flow", tags=["flow"])


class GenerateImageRequest(BaseModel):
    prompt: str
    project_id: str = ""
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    image_model: Optional[str] = None
    count: int = Field(default=1, ge=1, le=4)
    seed: Optional[int] = Field(default=None, ge=1, le=1_000_000_000)
    reference_media_ids: Optional[list[str]] = None
    character_media_ids: Optional[list[str]] = None


class GenerateVideoRequest(BaseModel):
    start_image_media_id: str
    prompt: str
    project_id: str = ""
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    end_image_media_id: Optional[str] = None
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    # Backward compatible: legacy requests remain Veo unless explicitly set.
    model_family: Literal["veo", "omni_flash"] = "veo"
    duration_s: int = 8
    resolution: Literal["360p", "720p"] = "720p"


class GenerateVideoRefsRequest(BaseModel):
    reference_media_ids: list[str]
    prompt: str
    project_id: str = ""
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    # Backward compatible: existing callers keep the Veo R2V path unless they
    # explicitly opt into Omni Flash.
    model_family: Literal["veo", "omni_flash"] = "veo"
    duration_s: int = 8
    resolution: Literal["360p", "720p"] = "720p"


class GenerateOmniFlashVideoRequest(BaseModel):
    reference_media_ids: list[str]
    prompt: str
    project_id: str = ""
    scene_id: str = ""
    duration_s: int = 8
    resolution: Literal["360p", "720p"] = "720p"
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"


class GenerateOmniFlashTextVideoRequest(BaseModel):
    prompt: str
    project_id: str = ""
    scene_id: str = ""
    duration_s: int = 8
    resolution: Literal["360p", "720p"] = "720p"
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"


class UpscaleVideoRequest(BaseModel):
    media_id: str
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    resolution: str = "VIDEO_RESOLUTION_4K"


class UploadImageRequest(BaseModel):
    image_base64: Optional[str] = Field(
        default=None,
        description=(
            "Recommended for external/API callers. Base64-encoded image bytes; "
            "avoids filesystem namespace and permission issues."
        ),
    )
    file_path: Optional[str] = Field(
        default=None,
        description=(
            "Server-local convenience mode only. The path is opened by the FlowKit "
            "service user and must be visible/readable inside its systemd namespace. "
            "Caller-local /tmp and protected home paths may not be accessible."
        ),
    )
    mime_type: Optional[str] = Field(
        default=None,
        description="Optional MIME override; otherwise inferred from file_name/file_path.",
    )
    project_id: str = Field(
        default="",
        description="Existing Flow project id, or empty to use/create the session project.",
    )
    file_name: str = Field(default="image.png", description="Filename sent to Google Flow.")


class CheckStatusRequest(BaseModel):
    operations: list[dict] = []
    # Omni/workflow-mode callers should pass workflow descriptors instead of
    # operation handles. If workflows is set, /check-status automatically uses
    # authenticated Flow project polling.
    workflows: Optional[list[dict]] = None
    project_id: str = ""
    include_encoded_video: bool = False


class CheckOmniStatusRequest(BaseModel):
    workflows: list[dict]
    project_id: str = ""
    include_encoded_video: bool = False


class EditImageRequest(BaseModel):
    prompt: str
    source_media_id: str
    project_id: str
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    image_model: Optional[str] = None
    count: int = Field(default=1, ge=1, le=4)
    seed: Optional[int] = Field(default=None, ge=1, le=1_000_000_000)
    reference_media_ids: Optional[list[str]] = None


class UpscaleImageRequest(BaseModel):
    media_id: str
    project_id: str
    quality: Literal["2k", "4k"] = "2k"


async def _resolve_direct_project(client, project_id: str) -> str:
    pid = str(project_id or "").strip()
    if pid:
        return pid
    try:
        session = await ensure_session_project(client)
    except Exception as exc:
        raise HTTPException(502, f"Could not create Flow session project: {exc}") from exc
    pid = str(session.get("project_id") or "")
    if not pid:
        raise HTTPException(502, "Flow session project did not return an id")
    return pid


@router.get("/status")
async def extension_status():
    """Extension health.

    `flow_key_present: false` is expected, not a fault: batchexecute
    authenticates in the page and there is no bearer token to capture.
    """
    client = get_flow_client()
    return {
        "connected": client.connected,
        # One transport now. The key stays so the documented pre-flight check
        # (CLAUDE.md) keeps reading {"transport": "batch", ...}.
        "transport": "batch",
        "flow_project_id": FLOW_PROJECT_ID or None,
        "allow_degraded": FLOW_ALLOW_DEGRADED,
        "flow_key_present": client._flow_key is not None,
        "generation_throttle": {
            "min_interval_s": FLOW_GENERATION_MIN_INTERVAL_S,
            "max_concurrent": FLOW_GENERATION_MAX_CONCURRENT,
            "unusual_activity_cooldown_s": FLOW_UNUSUAL_ACTIVITY_COOLDOWN_S,
            **client.generation_guard_status,
        },
        "session_project": current_session_project(),
    }


@router.post("/clear-hijack")
async def clear_hijack_cooldown():
    """Reset the generation cooldown triggered by extension_hijack_detected.

    Call this after deploying the bypass fix to immediately resume generation
    without waiting for the cooldown to expire.
    """
    import time as _time
    client = get_flow_client()
    old_until = client._generation_unusual_until
    client._generation_unusual_until = 0.0
    was_active = old_until > 0.0 and old_until > _time.monotonic()
    return {
        "cleared": True,
        "was_active": was_active,
    }


@router.get("/credits")
async def get_credits():
    """Get user credits from Google Flow."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.get_credits()
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result.get("data", result)


@router.post("/generate-image")
async def generate_image(body: GenerateImageRequest):
    """Generate 1-4 images with an explicit Flow image model."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    project_id = await _resolve_direct_project(client, body.project_id)
    data = body.model_dump(exclude={"reference_media_ids"})
    data["project_id"] = project_id
    refs = list(dict.fromkeys((body.reference_media_ids or []) + (body.character_media_ids or [])))
    data["character_media_ids"] = refs or None
    result = await client.generate_images(**data)
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/generate-video")
async def generate_video(body: GenerateVideoRequest):
    """Submit frame-conditioned video generation using Veo or Omni Flash.

    Existing callers default to Veo. For Omni set ``model_family=omni_flash``
    and ``duration_s`` to 4/6/8/10. With only ``start_image_media_id`` the
    request uses Omni First frame. When ``end_image_media_id`` is also present,
    it uses Omni First+Last frames.

    On the migrated batch transport, Omni frame-conditioned responses return
    ``flowkitPolling.mode=batch_operation`` and are polled through ``/check-status``.
    """
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    project_id = await _resolve_direct_project(client, body.project_id)

    if body.model_family == "omni_flash":
        try:
            common = dict(
                start_image_media_id=body.start_image_media_id,
                prompt=body.prompt,
                project_id=project_id,
                scene_id=body.scene_id,
                duration_s=body.duration_s,
                resolution=body.resolution,
                aspect_ratio=body.aspect_ratio,
                user_paygate_tier=body.user_paygate_tier,
            )
            if body.end_image_media_id:
                result = await generate_omni_flash_first_last_video(
                    end_image_media_id=body.end_image_media_id,
                    **common,
                )
            else:
                result = await generate_omni_flash_first_frame_video(**common)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        payload = body.model_dump(
            exclude={"model_family", "duration_s", "resolution"}, exclude_none=True
        )
        payload["project_id"] = project_id
        result = await client.generate_video(**payload)

    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/generate-video-refs")
async def generate_video_refs(body: GenerateVideoRefsRequest):
    """Submit reference-to-video generation using Veo or Gemini Omni Flash.

    Existing requests default to ``model_family=veo``. Set
    ``model_family=omni_flash`` and ``duration_s`` to 4/6/8/10 to use Omni.
    Migrated Omni Ingredients/R2V returns ``flowkitPolling.mode=batch_operation``;
    poll its operations through ``/check-status``.
    """
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    project_id = await _resolve_direct_project(client, body.project_id)

    if body.model_family == "omni_flash":
        try:
            result = await generate_omni_flash_video(
                reference_media_ids=body.reference_media_ids,
                prompt=body.prompt,
                project_id=project_id,
                scene_id=body.scene_id,
                duration_s=body.duration_s,
                resolution=body.resolution,
                aspect_ratio=body.aspect_ratio,
                user_paygate_tier=body.user_paygate_tier,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        payload = body.model_dump(exclude={"model_family", "duration_s", "resolution"})
        payload["project_id"] = project_id
        result = await client.generate_video_from_references(**payload)

    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/generate-video-omni-text")
async def generate_video_omni_text(body: GenerateOmniFlashTextVideoRequest):
    """Submit Omni 1.1 Flash text-to-video on flow.google.com.

    Durations 4/6/8/10 seconds map to Flow's ``abra_t2v_<N>s`` models.
    """
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    project_id = await _resolve_direct_project(client, body.project_id)
    try:
        payload = body.model_dump()
        payload["project_id"] = project_id
        result = await generate_omni_flash_text_video(**payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if result.get("error") or (
        isinstance(result.get("status"), int) and result["status"] >= 400
    ):
        raise HTTPException(
            result.get("status", 502),
            result.get("error", result.get("data")),
        )
    return result.get("data", result)


@router.post("/generate-video-omni")
async def generate_video_omni(body: GenerateOmniFlashVideoRequest):
    """Submit Gemini Omni Flash reference-to-video generation.

    The response includes ``flowkitPolling.workflows`` for the correct
    workflow/media polling path.
    """
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    project_id = await _resolve_direct_project(client, body.project_id)
    try:
        payload = body.model_dump()
        payload["project_id"] = project_id
        result = await generate_omni_flash_video(**payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
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
    """Check Veo operation status or Omni workflow/media status.

    Veo: pass ``operations``.
    Omni Flash: pass ``workflows`` from submit ``flowkitPolling.workflows``.
    """
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")

    if body.workflows:
        try:
            return await check_omni_flash_status(
                body.workflows,
                include_encoded_video=body.include_encoded_video,
                project_id=body.project_id,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc

    if not body.operations:
        raise HTTPException(400, "Provide operations for Veo or workflows for Omni Flash")

    result = await client.check_video_status(body.operations)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    if isinstance(result.get("status"), int) and result["status"] >= 400:
        raise HTTPException(result["status"], result.get("data", "Flow polling failed"))
    return result.get("data", result)


@router.post("/check-omni-status")
async def check_omni_status(body: CheckOmniStatusRequest):
    """Poll Gemini Omni Flash jobs via workflow primary media IDs."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    try:
        return await check_omni_flash_status(
            body.workflows,
            include_encoded_video=body.include_encoded_video,
            project_id=body.project_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc


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
async def get_media(media_id: str):
    """Get media metadata + fresh signed URL from Google Flow.

    Returns the raw response which may contain ``video.encodedVideo`` for
    workflow-backed video generations.
    """
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.get_media(media_id)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    status = result.get("status", 200)
    if isinstance(status, int) and status >= 400:
        raise HTTPException(status, result.get("data", "Media not found"))
    return result.get("data", result)


@router.post("/edit-image")
async def edit_image(body: EditImageRequest):
    """Edit an existing image using the current Flow BASE_IMAGE wire input."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.edit_image(
        body.prompt,
        body.source_media_id,
        body.project_id,
        aspect_ratio=body.aspect_ratio,
        user_paygate_tier=body.user_paygate_tier,
        character_media_ids=body.reference_media_ids,
        image_model=body.image_model,
        count=body.count,
        seed=body.seed,
    )
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/export-image")
@router.post("/upscale-image", include_in_schema=False)
async def export_image(body: UpscaleImageRequest):
    """Download a generated Flow image at 2K (or plan-gated 4K)."""
    import base64
    import binascii

    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.upscale_image(
        body.media_id,
        body.project_id,
        resolution=body.quality.upper(),
    )
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    data = result.get("data", result)
    try:
        content = base64.b64decode(data["encodedImage"], validate=True)
    except (KeyError, TypeError, binascii.Error) as exc:
        raise HTTPException(502, "Flow image upscale returned invalid image data") from exc
    quality = body.quality.lower()
    return Response(
        content=content,
        media_type=data.get("contentType", "image/jpeg"),
        headers={
            "Content-Disposition": f'attachment; filename="flow-{body.media_id}-{quality}.jpg"',
            "X-Flow-Image-Quality": quality,
        },
    )


async def _upload_image_bytes(
    client,
    image_bytes: bytes,
    *,
    project_id: str,
    mime_type: str,
    file_name: str,
) -> dict:
    """Upload bytes through the shared Flow path and return the public response."""
    if not image_bytes:
        raise HTTPException(422, "image payload is empty")
    resolved_project_id = await _resolve_direct_project(client, project_id)
    b64 = base64.b64encode(image_bytes).decode()
    result = await client.upload_image(
        b64,
        mime_type=mime_type,
        project_id=resolved_project_id,
        file_name=file_name,
    )
    if result.get("error") or (
        isinstance(result.get("status"), int) and result["status"] >= 400
    ):
        raise HTTPException(
            result.get("status", 502),
            result.get("error", result.get("data")),
        )
    media_id = result.get("_mediaId")
    return {
        "media_id": media_id,
        "project_id": resolved_project_id,
        "raw": result.get("data", result),
    }


def _read_server_local_image(file_path: str) -> bytes:
    """Read a path from FlowKit's own service namespace with useful API errors."""
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except FileNotFoundError as exc:
        raise HTTPException(
            404,
            (
                "Server-local file is not visible to the FlowKit service: "
                f"{file_path}. External callers should use image_base64 or "
                "/api/flow/upload-image-file; caller-local /tmp paths may be hidden "
                "by systemd PrivateTmp."
            ),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            403,
            (
                "File is not readable by FlowKit service: "
                f"{file_path}. The path must be readable by the service user; "
                "external callers should use image_base64 or /api/flow/upload-image-file."
            ),
        ) from exc
    except IsADirectoryError as exc:
        raise HTTPException(422, f"file_path is a directory, not an image file: {file_path}") from exc
    except OSError as exc:
        raise HTTPException(422, f"Could not read server-local file {file_path}: {exc}") from exc


@router.post(
    "/upload-image",
    summary="Upload image bytes or a server-local image",
    description=(
        "JSON upload endpoint. External/API callers should send image_base64. "
        "file_path is a server-local convenience mode only: the path is opened by "
        "the FlowKit service user and must be visible inside its systemd namespace."
    ),
)
async def upload_image(body: UploadImageRequest):
    """Upload image bytes to Google Flow; prefer image_base64 for external callers."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    if body.image_base64:
        try:
            image_bytes = base64.b64decode(body.image_base64, validate=True)
        except Exception as exc:
            raise HTTPException(422, "image_base64 is not valid base64") from exc
        if not image_bytes:
            raise HTTPException(422, "image_base64 is empty")
        mime = body.mime_type or mimetypes.guess_type(body.file_name)[0] or "image/png"
    elif body.file_path:
        image_bytes = _read_server_local_image(body.file_path)
        if not image_bytes:
            raise HTTPException(422, f"Server-local image is empty: {body.file_path}")
        mime = body.mime_type or mimetypes.guess_type(body.file_path)[0] or "image/png"
    else:
        raise HTTPException(
            422,
            "image_base64 is recommended; alternatively provide server-local file_path",
        )

    return await _upload_image_bytes(
        client,
        image_bytes,
        project_id=body.project_id,
        mime_type=mime,
        file_name=body.file_name,
    )


@router.post(
    "/upload-image-file",
    summary="Upload an image file with multipart/form-data",
    description=(
        "Recommended direct-file endpoint for external callers. The uploaded bytes are "
        "read from the HTTP request, so the caller does not need to share a filesystem "
        "namespace with the FlowKit service. Leave project_id empty to use/create the "
        "session project."
    ),
)
async def upload_image_file(
    file: UploadFile = File(..., description="Image file bytes from the caller."),
    project_id: str = Form(
        default="",
        description="Existing Flow project id, or empty to use/create the session project.",
    ),
    file_name: Optional[str] = Form(
        default=None,
        description="Optional filename override sent to Google Flow.",
    ),
    mime_type: Optional[str] = Form(
        default=None,
        description="Optional MIME override; defaults to upload Content-Type or filename inference.",
    ),
):
    """Upload a multipart file without requiring server-local filesystem access."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(422, "uploaded image file is empty")
    resolved_name = file_name or file.filename or "image.png"
    resolved_mime = (
        mime_type
        or file.content_type
        or mimetypes.guess_type(resolved_name)[0]
        or "image/png"
    )
    return await _upload_image_bytes(
        client,
        image_bytes,
        project_id=project_id,
        mime_type=resolved_mime,
        file_name=resolved_name,
    )
