from pydantic import BaseModel, model_validator
from typing import Optional
from agent.models.enums import RequestType, Orientation


class RequestCreate(BaseModel):
    type: RequestType
    orientation: Optional[Orientation] = None
    scene_id: Optional[str] = None
    character_id: Optional[str] = None
    project_id: Optional[str] = None
    video_id: Optional[str] = None
    source_media_id: Optional[str] = None

    @model_validator(mode="after")
    def check_required_fields(self) -> "RequestCreate":
        req_type = self.type
        if req_type in ("GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"):
            if not self.character_id:
                raise ValueError(f"character_id is required for {req_type}")
            if not self.project_id:
                raise ValueError(f"project_id is required for {req_type}")
        elif req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE",
                          "GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
            if not self.scene_id:
                raise ValueError(f"scene_id is required for {req_type}")
            if not self.project_id:
                raise ValueError(f"project_id is required for {req_type}")
            if not self.video_id:
                raise ValueError(f"video_id is required for {req_type}")
        return self


class Request(BaseModel):
    id: str
    project_id: Optional[str] = None
    video_id: Optional[str] = None
    scene_id: Optional[str] = None
    character_id: Optional[str] = None
    type: str
    orientation: Optional[str] = None
    status: str = "PENDING"
    request_id: Optional[str] = None
    media_id: Optional[str] = None
    output_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    next_retry_at: Optional[str] = None
    source_media_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
