from pydantic import BaseModel
from typing import Optional


from agent.models.enums import EntityType


class CharacterCreate(BaseModel):
    name: str
    entity_type: EntityType = "character"
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    reference_image_url: Optional[str] = None
    media_id: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    entity_type: Optional[EntityType] = None
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    reference_image_url: Optional[str] = None
    media_id: Optional[str] = None


class Character(BaseModel):
    id: str
    name: str
    entity_type: str = "character"
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    reference_image_url: Optional[str] = None
    media_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
