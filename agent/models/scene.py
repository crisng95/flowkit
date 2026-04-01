from pydantic import BaseModel
from typing import Optional
from agent.models.enums import ChainType, StatusType


class SceneCreate(BaseModel):
    video_id: str
    display_order: int = 0
    prompt: str
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    character_names: Optional[list[str]] = None
    parent_scene_id: Optional[str] = None
    chain_type: ChainType = "ROOT"


class SceneUpdate(BaseModel):
    prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    character_names: Optional[list[str]] = None
    chain_type: Optional[ChainType] = None
    display_order: Optional[int] = None

    vertical_image_url: Optional[str] = None
    vertical_image_media_id: Optional[str] = None
    vertical_image_status: Optional[StatusType] = None
    vertical_video_url: Optional[str] = None
    vertical_video_media_id: Optional[str] = None
    vertical_video_status: Optional[StatusType] = None
    vertical_upscale_url: Optional[str] = None
    vertical_upscale_media_id: Optional[str] = None
    vertical_upscale_status: Optional[StatusType] = None

    horizontal_image_url: Optional[str] = None
    horizontal_image_media_id: Optional[str] = None
    horizontal_image_status: Optional[StatusType] = None
    horizontal_video_url: Optional[str] = None
    horizontal_video_media_id: Optional[str] = None
    horizontal_video_status: Optional[StatusType] = None
    horizontal_upscale_url: Optional[str] = None
    horizontal_upscale_media_id: Optional[str] = None
    horizontal_upscale_status: Optional[StatusType] = None

    vertical_end_scene_media_id: Optional[str] = None
    horizontal_end_scene_media_id: Optional[str] = None

    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    duration: Optional[float] = None


class Scene(BaseModel):
    id: str
    video_id: str
    display_order: int = 0
    prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    character_names: Optional[list[str]] = None  # parsed from JSON
    parent_scene_id: Optional[str] = None
    chain_type: str = "ROOT"

    vertical_image_url: Optional[str] = None
    vertical_image_media_id: Optional[str] = None
    vertical_image_status: str = "PENDING"
    vertical_video_url: Optional[str] = None
    vertical_video_media_id: Optional[str] = None
    vertical_video_status: str = "PENDING"
    vertical_upscale_url: Optional[str] = None
    vertical_upscale_media_id: Optional[str] = None
    vertical_upscale_status: str = "PENDING"

    horizontal_image_url: Optional[str] = None
    horizontal_image_media_id: Optional[str] = None
    horizontal_image_status: str = "PENDING"
    horizontal_video_url: Optional[str] = None
    horizontal_video_media_id: Optional[str] = None
    horizontal_video_status: str = "PENDING"
    horizontal_upscale_url: Optional[str] = None
    horizontal_upscale_media_id: Optional[str] = None
    horizontal_upscale_status: str = "PENDING"

    vertical_end_scene_media_id: Optional[str] = None
    horizontal_end_scene_media_id: Optional[str] = None

    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    duration: Optional[float] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None
