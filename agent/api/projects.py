import logging
from fastapi import APIRouter, HTTPException
from agent.models.project import Project, ProjectCreate, ProjectUpdate
from agent.models.character import Character
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.services.flow_client import get_flow_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


COMPOSITION_GUIDELINES = {
    "character": (
        "COMPOSITION: Full body shot from head to toe, standing upright and straight (not tilted or leaning). "
        "Centered in frame with balanced composition. Front-facing view, looking directly at camera. "
        "Neutral simple background that doesn't distract from the subject. "
        "Proper proportions and anatomy. Character perfectly vertical, not skewed or rotated."
    ),
    "location": (
        "COMPOSITION: Establishing shot showing the full environment. "
        "Balanced level composition with straight horizon. Clear focal point. "
        "Atmospheric and richly detailed. Show depth and spatial layout."
    ),
    "creature": (
        "COMPOSITION: Full body shot showing the creature's complete form. "
        "Emphasize natural stance (quadrupedal on all fours, bipedal upright, etc.). "
        "Centered with clear view of distinctive features. Neutral background. "
        "Proper scale and proportions relative to body structure."
    ),
    "visual_asset": (
        "COMPOSITION: Clear detailed view showing the asset's complete form. "
        "Appropriate angle to showcase distinctive features and functional elements. "
        "Centered with proper scale reference. Neutral background. "
        "Show key details, materials, and surface textures."
    ),
    "generic_troop": (
        "COMPOSITION: Military/tactical pose showing readiness. "
        "Full or three-quarter body view. Centered composition. "
        "Neutral background. Proper perspective and proportions."
    ),
    "faction": (
        "COMPOSITION: Military/tactical pose showing readiness. "
        "Full or three-quarter body view. Centered composition. "
        "Neutral background. Proper perspective and proportions."
    ),
}


_STYLE_COMPAT_MAP = {
    "3d": "3d_pixar",
    "3D": "3d_pixar",
    "photorealistic": "realistic",
}


def _resolve_material_id(value: str) -> str:
    """Map legacy style strings to material IDs. Returns value unchanged if no mapping."""
    return _STYLE_COMPAT_MAP.get(value, value)


def _build_character_profile(char_name: str, char_desc: str | None, story: str | None,
                              entity_type: str = "character", material_id: str = "3d_pixar") -> dict:
    """Build a rich profile (description + image_prompt) for any reference entity.

    The image_prompt generates a reference image used as mediaId for all
    scene generations. Visual appearance is defined HERE, not in scene prompts.
    Scene prompts should only describe actions/environment/composition.

    story may be None — in that case the description omits story context and
    the image_prompt uses a simpler prefix.
    """
    from agent.materials import get_material
    material = get_material(material_id)
    if not material:
        raise ValueError(f"Unknown material: {material_id}")

    base_desc = char_desc or char_name
    composition = COMPOSITION_GUIDELINES.get(entity_type, COMPOSITION_GUIDELINES["character"])

    if story:
        description = f"{char_name}: {base_desc}. Story context: {story}"
        image_prefix = f"Single reference image of {base_desc}. "
        single_image_note = "ONE single image only, NOT a multi-panel grid or multiple views. "
    else:
        description = base_desc
        image_prefix = f"Reference image of {base_desc}. "
        single_image_note = ""

    style_instruction = material["style_instruction"]
    if material.get("negative_prompt"):
        style_instruction += f" {material['negative_prompt']}"
    lighting = material.get("lighting", "Studio lighting, highly detailed")

    image_prompt = (
        f"{image_prefix}"
        f"{style_instruction} "
        f"{composition} "
        f"{single_image_note}"
        f"{lighting}"
    )

    return {"description": description, "image_prompt": image_prompt}


async def _detect_user_tier(client) -> str:
    """Auto-detect user paygate tier from Flow credits API."""
    try:
        result = await client.get_credits()
        data = result.get("data", result)
        tier = data.get("userPaygateTier", "PAYGATE_TIER_ONE")
        logger.info("Auto-detected user tier: %s", tier)
        return tier
    except Exception as e:
        logger.warning("Failed to detect tier, defaulting to TIER_ONE: %s", e)
        return "PAYGATE_TIER_ONE"


def _get_repo() -> SQLiteRepository:
    return SQLiteRepository()


@router.post("", response_model=Project)
async def create(body: ProjectCreate):
    from agent.materials import get_material

    # Step 1: Create project on Google Flow to get the real projectId
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected — cannot create project on Google Flow")

    # Resolve material (support legacy style field + material field)
    material_id = _resolve_material_id(body.material)
    material = get_material(material_id)
    if not material:
        raise HTTPException(400, f"Unknown material: '{material_id}'. Use GET /api/materials to list available materials.")

    # Validate characters before any API calls to avoid orphan projects
    characters_input_raw = body.model_dump(exclude_none=True).get("characters")
    if characters_input_raw:
        names = [c["name"] for c in characters_input_raw]
        if len(names) != len(set(names)):
            dupes = [n for n in names if names.count(n) > 1]
            raise HTTPException(400, f"Duplicate character names: {list(set(dupes))}")

    detected_tier = await _detect_user_tier(client)

    flow_result = await client.create_project(body.name, body.tool_name)
    if flow_result.get("error"):
        raise HTTPException(502, f"Flow API error: {flow_result['error']}")

    try:
        data = flow_result.get("data", {})
        result = data["result"]["data"]["json"]["result"]
        flow_project_id = result["projectId"]
    except (KeyError, TypeError) as e:
        logger.error("Unexpected Flow response: %s", flow_result)
        raise HTTPException(502, f"Failed to parse Flow response: {e}")

    logger.info("Flow project created: %s", flow_project_id)

    repo = _get_repo()

    # Step 2: Create local project with the Flow-assigned ID and detected tier
    create_data = body.model_dump(exclude_none=True)
    create_data.pop("tool_name", None)
    create_data.pop("style", None)
    characters_input = create_data.pop("characters", None)

    project = await repo.create_project(
        id=flow_project_id,
        name=create_data["name"],
        description=create_data.get("description"),
        story=create_data.get("story"),
        language=create_data.get("language", "en"),
        user_paygate_tier=detected_tier,
        material=material_id,
    )

    # Step 3: Create reference entities (characters, locations, assets) with profiles
    if characters_input:
        for char_input in characters_input:
            etype = char_input.get("entity_type", "character")
            profile = _build_character_profile(
                char_input["name"],
                char_input.get("description"),
                body.story,
                entity_type=etype,
                material_id=material_id,
            )
            description = profile["description"]
            image_prompt = profile["image_prompt"]
            char = await repo.create_character(
                name=char_input["name"],
                entity_type=etype,
                description=description,
                image_prompt=image_prompt,
                voice_description=char_input.get("voice_description"),
            )
            await repo.link_character_to_project(flow_project_id, char.id)
            logger.info("%s '%s' created and linked: %s", etype, char_input["name"], char.id)

    return project


@router.get("", response_model=list[Project])
async def list_all(status: str = None):
    repo = _get_repo()
    rows = await repo.list("project", **({} if status is None else {"status": status}))
    return [repo._row_to_project(r) for r in rows]


@router.get("/{pid}", response_model=Project)
async def get(pid: str):
    repo = _get_repo()
    p = await repo.get_project(pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.patch("/{pid}", response_model=Project)
async def update(pid: str, body: ProjectUpdate):
    repo = _get_repo()
    row = await repo.update("project", pid, **body.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(404, "Project not found")
    return repo._row_to_project(row)


@router.delete("/{pid}")
async def delete(pid: str):
    repo = _get_repo()
    if not await repo.delete_project(pid):
        raise HTTPException(404, "Project not found")
    return {"ok": True}


@router.post("/{pid}/characters/{cid}")
async def link_character(pid: str, cid: str):
    repo = _get_repo()
    if not await repo.link_character_to_project(pid, cid):
        raise HTTPException(400, "Failed to link character")
    return {"ok": True}


@router.delete("/{pid}/characters/{cid}")
async def unlink_character(pid: str, cid: str):
    repo = _get_repo()
    if not await repo.unlink_character_from_project(pid, cid):
        raise HTTPException(404, "Link not found")
    return {"ok": True}


@router.get("/{pid}/characters", response_model=list[Character])
async def get_characters(pid: str):
    repo = _get_repo()
    return await repo.get_project_characters(pid)
