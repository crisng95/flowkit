"""FastAPI router for material (visual style) endpoints."""
import logging

from fastapi import APIRouter, HTTPException

from agent.models.material import MaterialCreateRequest, MaterialResponse
from agent.materials import (
    get_material,
    list_materials as _list_materials,
    register_material,
    MATERIALS,
    _BUILTIN_IDS,
)
from agent.db.crud import (
    create_material as crud_create_material,
    delete_material as crud_delete_material,
    list_materials as crud_list_materials,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["materials"])

MAX_CUSTOM_MATERIALS = 50


def _to_response(material: dict, is_builtin: bool | None = None) -> MaterialResponse:
    if is_builtin is None:
        is_builtin = material["id"] in _BUILTIN_IDS
    return MaterialResponse(
        id=material["id"],
        name=material["name"],
        style_instruction=material["style_instruction"],
        negative_prompt=material.get("negative_prompt"),
        scene_prefix=material.get("scene_prefix"),
        lighting=material.get("lighting", "Studio lighting, highly detailed"),
        is_builtin=is_builtin,
    )


@router.get("", response_model=list[MaterialResponse])
async def list_all():
    """List all materials (built-in + custom)."""
    return [_to_response(m) for m in _list_materials()]


@router.get("/{material_id}", response_model=MaterialResponse)
async def get(material_id: str):
    """Get material by ID."""
    material = get_material(material_id)
    if not material:
        raise HTTPException(404, f"Material '{material_id}' not found")
    return _to_response(material)


@router.post("", response_model=MaterialResponse, status_code=201)
async def create(body: MaterialCreateRequest):
    """Create a custom material. ID must not clash with built-in materials."""
    if body.id in _BUILTIN_IDS:
        raise HTTPException(400, f"Cannot override built-in material '{body.id}'")
    if get_material(body.id):
        raise HTTPException(409, f"Material '{body.id}' already exists")

    custom_count = sum(1 for mid in MATERIALS if mid not in _BUILTIN_IDS)
    if custom_count >= MAX_CUSTOM_MATERIALS:
        raise HTTPException(429, f"Custom material limit reached ({MAX_CUSTOM_MATERIALS})")

    material = {
        "id": body.id,
        "name": body.name,
        "style_instruction": body.style_instruction,
        "negative_prompt": body.negative_prompt,
        "scene_prefix": body.scene_prefix,
        "lighting": body.lighting,
    }
    register_material(material)
    await crud_create_material(
        id=body.id,
        name=body.name,
        style_instruction=body.style_instruction,
        negative_prompt=body.negative_prompt,
        scene_prefix=body.scene_prefix,
        lighting=body.lighting,
    )
    logger.info("Custom material registered: %s", body.id)
    return _to_response(material, is_builtin=False)


@router.delete("/{material_id}")
async def delete(material_id: str):
    """Delete a custom material. Built-in materials cannot be deleted."""
    if material_id in _BUILTIN_IDS:
        raise HTTPException(400, f"Cannot delete built-in material '{material_id}'")
    if material_id not in MATERIALS:
        raise HTTPException(404, f"Material '{material_id}' not found")
    del MATERIALS[material_id]
    await crud_delete_material(material_id)
    logger.info("Custom material deleted: %s", material_id)
    return {"ok": True}
