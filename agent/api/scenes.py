from fastapi import APIRouter, HTTPException
from agent.models.scene import Scene, SceneCreate, SceneUpdate
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.services.event_bus import event_bus
from agent.utils.paths import scene_tts_path
from agent.utils.slugify import slugify
from agent.config import OUTPUT_DIR
import json

router = APIRouter(prefix="/scenes", tags=["scenes"])

_repo = SQLiteRepository()


async def _project_slug_for_video(video_id: str) -> str | None:
    video = await _repo.get_video(video_id)
    if not video:
        return None
    project = await _repo.get_project(video.project_id)
    if not project:
        return None
    return slugify(project.name)


def _resolve_tts_audio_path(project_slug: str | None, scene_id: str, display_order: int) -> str | None:
    if not project_slug:
        return None
    tts_file = scene_tts_path(project_slug, display_order, scene_id)
    if tts_file.exists():
        return str(tts_file)
    legacy_tts = OUTPUT_DIR / project_slug / "tts" / f"{scene_id}.wav"
    if legacy_tts.exists():
        return str(legacy_tts)
    return None


def _scene_to_flat(sdk_scene, project_slug: str | None = None) -> dict:
    """Convert SDK Scene domain model to flat dict matching API response shape."""
    repo = SQLiteRepository()
    flat = repo._scene_to_updates(sdk_scene)
    flat["id"] = sdk_scene.id
    flat["video_id"] = sdk_scene.video_id
    flat["display_order"] = sdk_scene.display_order
    flat["parent_scene_id"] = sdk_scene.parent_scene_id
    flat["transition_prompt"] = sdk_scene.transition_prompt
    flat["chain_type"] = sdk_scene.chain_type
    flat["source"] = sdk_scene.source
    # API contract uses list[str], not JSON string.
    flat["character_names"] = sdk_scene.character_names
    tts_audio_path = _resolve_tts_audio_path(project_slug, sdk_scene.id, sdk_scene.display_order)
    narrator_text = (sdk_scene.narrator_text or "").strip()
    flat["tts_audio_path"] = tts_audio_path
    flat["tts_status"] = "COMPLETED" if tts_audio_path else ("PENDING" if narrator_text else "PENDING")
    flat["created_at"] = sdk_scene.created_at
    flat["updated_at"] = sdk_scene.updated_at
    return flat


@router.post("", response_model=Scene)
async def create(body: SceneCreate):
    # Auto-prepend material scene_prefix if project has a material set
    if body.video_id and body.prompt:
        video = await _repo.get_video(body.video_id)
        if video:
            from agent.db.crud import get_project
            project_row = await get_project(video.project_id)
            if project_row and project_row.get("material"):
                from agent.materials import get_material
                mat = get_material(project_row["material"])
                if mat and mat.get("scene_prefix"):
                    prefix = mat["scene_prefix"]
                    if not body.prompt.startswith(prefix):
                        body.prompt = f"{prefix} {body.prompt}"

    data = body.model_dump(exclude_none=True)

    # Auto-shift subsequent scenes when inserting
    if data.get("chain_type") == "INSERT" and data.get("video_id"):
        insert_order = data.get("display_order", 0)
        existing = await _repo.list_scenes(data["video_id"])
        # Shift scenes at or after insert_order in reverse to avoid collisions
        to_shift = sorted(
            [s for s in existing if s.display_order >= insert_order],
            key=lambda s: s.display_order,
            reverse=True,
        )
        for s in to_shift:
            await _repo.update("scene", s.id, display_order=s.display_order + 1)

    sdk_scene = await _repo.create_scene(**data)
    project_slug = await _project_slug_for_video(sdk_scene.video_id)
    scene = _scene_to_flat(sdk_scene, project_slug)
    await event_bus.emit("scene_created", {
        "id": sdk_scene.id,
        "video_id": sdk_scene.video_id,
        "display_order": sdk_scene.display_order,
    })
    return scene


@router.get("", response_model=list[Scene])
async def list_by_video(video_id: str):
    scenes = await _repo.list_scenes(video_id)
    project_slug = await _project_slug_for_video(video_id)
    return [_scene_to_flat(s, project_slug) for s in scenes]


@router.get("/{sid}", response_model=Scene)
async def get(sid: str):
    sdk_scene = await _repo.get_scene(sid)
    if not sdk_scene:
        raise HTTPException(404, "Scene not found")
    project_slug = await _project_slug_for_video(sdk_scene.video_id)
    return _scene_to_flat(sdk_scene, project_slug)


@router.patch("/{sid}", response_model=Scene)
async def update(sid: str, body: SceneUpdate):
    # Use exclude_unset (not exclude_none) so explicit null clears fields
    # e.g. {"vertical_video_url": null} → sets DB column to NULL
    data = body.model_dump(exclude_unset=True)
    if "character_names" in data and isinstance(data["character_names"], list):
        data["character_names"] = json.dumps(data["character_names"])
    row = await _repo.update("scene", sid, **data)
    if not row:
        raise HTTPException(404, "Scene not found")
    sdk_scene = _repo._row_to_scene(row)
    project_slug = await _project_slug_for_video(sdk_scene.video_id)
    scene = _scene_to_flat(sdk_scene, project_slug)
    await event_bus.emit("scene_updated", {
        "id": sdk_scene.id,
        "video_id": sdk_scene.video_id,
        "display_order": sdk_scene.display_order,
    })
    return scene


@router.delete("/{sid}")
async def delete(sid: str):
    scene = await _repo.get_scene(sid)
    if not await _repo.delete("scene", sid):
        raise HTTPException(404, "Scene not found")
    await event_bus.emit("scene_deleted", {
        "id": sid,
        "video_id": scene.video_id if scene else None,
    })
    return {"ok": True}


@router.delete("")
async def cleanup(video_id: str, source: str = "system"):
    """Delete all scenes with given source and re-compact display_order."""
    if source not in ("system", "user"):
        raise HTTPException(400, "Can only cleanup 'system' or 'user' scenes")
    scenes = await _repo.list_scenes(video_id)
    to_delete = [s for s in scenes if s.source == source]
    to_keep = sorted([s for s in scenes if s.source != source], key=lambda s: s.display_order)

    # Delete matching scenes
    for s in to_delete:
        await _repo.delete("scene", s.id)

    # Re-compact display_order (0, 1, 2, ...)
    for i, s in enumerate(to_keep):
        if s.display_order != i:
            await _repo.update("scene", s.id, display_order=i)

    return {"deleted": len(to_delete), "remaining": len(to_keep)}
