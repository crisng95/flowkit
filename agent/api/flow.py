"""Direct Flow API endpoints — for manual operations outside the queue."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agent.services.flow_client import get_flow_client

router = APIRouter(prefix="/flow", tags=["flow"])


class EntityReference(BaseModel):
    handle: str        # tên entity dùng trong prompt: "{handle}"
    media_id: str      # UUID ảnh ref trên Flow


class GenerateImageRequest(BaseModel):
    prompt: str
    project_id: str
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    character_media_ids: Optional[list[str]] = None
    # Tham chiếu có handle: prompt nhúng "{handle}" → structuredPrompt tách thành part riêng
    references: Optional[list[EntityReference]] = None
    image_model: Optional[str] = None   # override model key (vd "GEM_PIX_2", "NARWHAL")
    # Hai cờ của _build_structured_parts, phơi ra đây vì endpoint này là chỗ soi lỗi 400
    # INVALID_ARGUMENT: bật/tắt được thì đo thẳng được prompt nào vỡ vì reference part trùng.
    dedupe_refs: bool = True            # bind mỗi ảnh MỘT lần (lần nhắc đầu)
    bind_unreferenced: bool = False     # ảnh prompt không gọi tên vẫn được bind


class GenerateVideoRequest(BaseModel):
    start_image_media_id: str
    prompt: str
    project_id: str
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    end_image_media_id: Optional[str] = None
    user_paygate_tier: str = "PAYGATE_TIER_ONE"


class GenerateVideoRefsRequest(BaseModel):
    reference_media_ids: list[str]
    prompt: str
    project_id: str
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    # prompt nhúng "{handle}" → structuredPrompt tách part riêng cho từng reference
    references: Optional[list[EntityReference]] = None
    video_model: Optional[str] = None   # override model key (vd "veo_3_1_r2v_lite")


class GenerateVideoOmniRequest(BaseModel):
    prompt: str
    project_id: str
    reference_media_ids: list[str]
    duration_s: int = 8                 # 4 | 6 | 8 | 10
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE"  # chỉ PORTRAIT/LANDSCAPE
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    # prompt nhúng "{handle}" → structuredPrompt tách part riêng cho từng reference
    references: Optional[list[EntityReference]] = None


class GenerateVideoVeoLiteRequest(BaseModel):
    """Veo 3.1 Lite [Lower Priority] — 0 credit, chỉ Gemini Ultra (PAYGATE_TIER_TWO).

    Kiểu sinh suy ra từ ảnh truyền vào: start+end → nội suy hai khung, chỉ start → i2v,
    không start → "inference" r2v (cần ≥1 reference)."""
    prompt: str
    project_id: str
    scene_id: str = ""
    start_media_id: Optional[str] = None
    end_media_id: Optional[str] = None
    reference_media_ids: Optional[list[str]] = None
    # prompt nhúng "{handle}" → structuredPrompt tách part riêng cho từng reference
    references: Optional[list[EntityReference]] = None
    duration_s: int = 8                 # 4 | 6 | 8 — xem VEO_LITE_DURATION_FIELD
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE"
    user_paygate_tier: str = "PAYGATE_TIER_TWO"


class UpscaleVideoRequest(BaseModel):
    media_id: str
    scene_id: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    # Bỏ trống → suy ra theo tier (ONE → 1080p, TWO → 4K). Xin 4K trên tier ONE bị từ chối.
    resolution: Optional[str] = None
    project_id: str = ""
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    workflow_id: Optional[str] = None


class UploadImageRequest(BaseModel):
    file_path: str  # absolute path to local image file
    project_id: str = ""
    file_name: str = "image.png"


class CheckStatusRequest(BaseModel):
    # [{"name": <mediaId>, "projectId": <flowProjectId>}]
    media: list[dict]


class EditImageRequest(BaseModel):
    prompt: str
    source_media_id: str
    project_id: str
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"


class ChangeDisplaynameMediaRequest(BaseModel):
    media_id: str
    project_id: str
    display_name: str


class CreateProjectRequest(BaseModel):
    project_title: str
    tool_name: str = "PINHOLE"


@router.get("/status")
async def extension_status():
    """Check if extension is connected."""
    client = get_flow_client()
    return {
        "connected": client.connected,
        "flow_key_present": client._flow_key is not None,
        "account": client.identity,
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


@router.post("/create-project")
async def create_project(body: CreateProjectRequest):
    """Create a Google Flow project via tRPC (does not use GOOGLE_API_KEY)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.create_project(body.project_title, tool_name=body.tool_name)
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
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


@router.post("/generate-video-omni")
async def generate_video_omni(body: GenerateVideoOmniRequest):
    """Submit Omni Flash video generation (r2v, variable duration; returns operations)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.generate_video_omni(**body.model_dump(exclude_none=True))
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/generate-video-veo-lite")
async def generate_video_veo_lite(body: GenerateVideoVeoLiteRequest):
    """Submit Veo 3.1 Lite [Lower Priority] video generation (0 credit, Ultra only)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.generate_video_veo_lite(**body.model_dump(exclude_none=True))
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/upscale/video")
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
    """Trạng thái render của các media video.

    `media` = [{"name": <mediaId>, "projectId": <flowProjectId>}] — contract MỚI; shape cũ
    (`operations` + `sceneId`) bị Flow trả 400."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.check_video_status(body.media)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result.get("data", result)


# @router.post("/refresh-urls/{project_id}")
# async def refresh_project_urls(project_id: str):
#     """Bulk refresh all media URLs for a project via per-media get_media calls."""
#     client = get_flow_client()
#     if not client.connected:
#         raise HTTPException(503, "Extension not connected")
#     result = await client.refresh_project_urls(project_id)
#     if result.get("error"):
#         raise HTTPException(502, result["error"])
#     return result


# @router.get("/media/{media_id}")
# async def get_media(media_id: str):
#     """Get media metadata + fresh signed URL from Google Flow.

#     Returns the raw response which should contain a fresh fifeUrl/servingUri.
#     Use this to refresh expired GCS signed URLs.
#     """
#     client = get_flow_client()
#     if not client.connected:
#         raise HTTPException(503, "Extension not connected")
#     result = await client.get_media(media_id)
#     if result.get("error"):
#         raise HTTPException(502, result["error"])
#     status = result.get("status", 200)
#     if isinstance(status, int) and status >= 400:
#         raise HTTPException(status, result.get("data", "Media not found"))
#     return result.get("data", result)


@router.get("/media/{primary_media_id}")
async def get_direct_media(primary_media_id: str):
    """Get media metadata + fresh signed URL from Google Flow.

    Returns the raw response which should contain a fresh fifeUrl/servingUri.
    Use this to refresh expired GCS signed URLs.
    """
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.get_direct_media(primary_media_id)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    status = result.get("status", 200)
    if isinstance(status, int) and status >= 400:
        raise HTTPException(status, result.get("data", "Media not found"))
    return result.get("data", result)


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
    )
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.post("/upload-image")
async def upload_image(body: UploadImageRequest):
    """Upload a local image file to Google Flow and get a media_id."""
    import base64, mimetypes
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
    result = await client.upload_image(b64, mime_type=mime, project_id=body.project_id, file_name=body.file_name)
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    media_id = result.get("_mediaId")
    return {"media_id": media_id, "raw": result.get("data", result)}


@router.patch("/change-displayname")
async def change_displayname(body: ChangeDisplaynameMediaRequest):
    """change displayname (bypasses queue)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.change_display_name(
        body.media_id, body.project_id, body.display_name,
    )
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.get("/change-project-cover/{project_id}/{media_id}")
async def change_project_cover(project_id: str, media_id: str):
    """change project cover (bypasses queue)."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.change_project_cover(project_id, media_id)
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))
    return result.get("data", result)


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    """Bulk refresh all media URLs for a project via per-media get_media calls."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.get_project(project_id)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result

@router.get("/projects")
async def get_projects():
    """Bulk refresh all media URLs for a project via per-media get_media calls."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.get_projects()
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result


@router.get("/delete-project/{project_id}")
async def delete_project(project_id: str):
    """Delete a project on Google Flow via tRPC endpoint."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.delete_project(project_id)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result


# @router.get("/upscale/image/{project_id}/{media_id}")
# async def upscale_image(project_id: str, media_id: str, resolution: str = "UPSAMPLE_IMAGE_RESOLUTION_2K"):
#     """Upscale an image on Google Flow via API endpoint."""
#     client = get_flow_client()
#     if not client.connected:
#         raise HTTPException(503, "Extension not connected")
#     result = await client.upscale_image(media_id, project_id, resolution)
#     if result.get("error"):
#         raise HTTPException(502, result["error"])
#     return result