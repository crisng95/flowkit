"""Scene chaining logic — continuation scenes from parent video."""
import logging
from agent.db import crud

logger = logging.getLogger(__name__)


async def create_continuation_scene(video_id: str, parent_scene_id: str, prompt: str,
                                     character_names: list[str] = None, display_order: int = None) -> dict:
    parent = await crud.get_scene(parent_scene_id)
    if not parent:
        raise ValueError(f"Parent scene {parent_scene_id} not found")

    if display_order is None:
        scenes = await crud.list_scenes(video_id)
        display_order = parent["display_order"] + 1
        for s in scenes:
            if s["display_order"] >= display_order and s["id"] != parent_scene_id:
                await crud.update_scene(s["id"], display_order=s["display_order"] + 1)

    scene = await crud.create_scene(
        video_id=video_id,
        display_order=display_order,
        prompt=prompt,
        character_names=character_names,
        parent_scene_id=parent_scene_id,
        chain_type="CONTINUATION",
    )

    updates = {}
    if parent.get("vertical_video_media_id"):
        updates["vertical_end_scene_media_id"] = parent["vertical_video_media_id"]
    if parent.get("horizontal_video_media_id"):
        updates["horizontal_end_scene_media_id"] = parent["horizontal_video_media_id"]

    if updates:
        scene = await crud.update_scene(scene["id"], **updates)

    logger.info("Created continuation scene %s from parent %s", scene["id"], parent_scene_id)
    return scene
