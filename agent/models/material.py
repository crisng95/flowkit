"""Pydantic models for material endpoints."""
from pydantic import BaseModel, Field
from typing import Optional


class MaterialResponse(BaseModel):
    id: str
    name: str
    style_instruction: str
    negative_prompt: Optional[str] = None
    scene_prefix: Optional[str] = None
    lighting: str = "Studio lighting, highly detailed"
    is_builtin: bool = True


class MaterialCreateRequest(BaseModel):
    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]{1,63}$")  # lowercase slug
    name: str = Field(..., min_length=1, max_length=100)
    style_instruction: str = Field(..., min_length=10, max_length=2000)
    negative_prompt: Optional[str] = Field(None, max_length=1000)
    scene_prefix: Optional[str] = Field(None, max_length=500)
    lighting: str = Field("Studio lighting, highly detailed", max_length=200)
