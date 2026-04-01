from pydantic import BaseModel
from typing import Optional
from agent.models.enums import RequestType, Orientation


class RequestCreate(BaseModel):
    type: RequestType
    orientation: Optional[Orientation] = None
    scene_id: Optional[str] = None
    character_id: Optional[str] = None
    project_id: Optional[str] = None
    video_id: Optional[str] = None


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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
