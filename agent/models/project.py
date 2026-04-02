from pydantic import BaseModel
from typing import Optional
from agent.models.enums import ProjectStatus, PaygateTier, EntityType


class CharacterInput(BaseModel):
    """Reference entity stub provided at project creation time."""
    name: str
    entity_type: EntityType = "character"
    description: Optional[str] = None
    voice_description: Optional[str] = None  # max ~30 words, characters/creatures only


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    story: Optional[str] = None
    language: str = "en"
    user_paygate_tier: PaygateTier = "PAYGATE_TIER_ONE"
    tool_name: str = "PINHOLE"
    characters: Optional[list[CharacterInput]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    story: Optional[str] = None
    thumbnail_url: Optional[str] = None
    language: Optional[str] = None
    status: Optional[ProjectStatus] = None
    user_paygate_tier: Optional[PaygateTier] = None


class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    story: Optional[str] = None
    thumbnail_url: Optional[str] = None
    language: str = "en"
    status: str = "ACTIVE"
    user_paygate_tier: str = "PAYGATE_TIER_TWO"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
