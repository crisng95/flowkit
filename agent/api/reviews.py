"""FastAPI router for video review endpoints."""
import logging
from fastapi import APIRouter, HTTPException, Query

from agent.models.review import VideoReview, SceneReview
from agent.services.video_reviewer import review_video, review_scene_video
from agent.db.crud import get_video, get_scene, get_project_characters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["reviews"])


@router.post("/{vid}/review", response_model=VideoReview)
async def review_video_endpoint(
    vid: str,
    project_id: str = Query(..., description="Project ID"),
    mode: str = Query("light", description="Review mode: light (4fps) or deep (8fps)"),
    orientation: str = Query("VERTICAL", description="Orientation: VERTICAL or HORIZONTAL"),
):
    """Review all scene videos in a video using Claude Vision frame analysis."""
    if mode not in ("light", "deep"):
        raise HTTPException(400, "mode must be 'light' or 'deep'")
    if orientation.upper() not in ("VERTICAL", "HORIZONTAL"):
        raise HTTPException(400, "orientation must be 'VERTICAL' or 'HORIZONTAL'")

    video = await get_video(vid)
    if not video:
        raise HTTPException(404, "Video not found")

    logger.info("Starting %s review for video %s (project %s, %s)", mode, vid, project_id, orientation)
    try:
        result = await review_video(vid, project_id, mode=mode, orientation=orientation.upper())
    except Exception as e:
        logger.exception("Review failed for video %s: %s", vid, e)
        raise HTTPException(500, f"Review failed: {e}")

    return result


@router.post("/{vid}/scenes/{sid}/review", response_model=SceneReview)
async def review_scene_endpoint(
    vid: str,
    sid: str,
    project_id: str = Query(..., description="Project ID"),
    mode: str = Query("light", description="Review mode: light (4fps) or deep (8fps)"),
    orientation: str = Query("VERTICAL", description="Orientation: VERTICAL or HORIZONTAL"),
):
    """Review a single scene video using Claude Vision frame analysis."""
    if mode not in ("light", "deep"):
        raise HTTPException(400, "mode must be 'light' or 'deep'")
    if orientation.upper() not in ("VERTICAL", "HORIZONTAL"):
        raise HTTPException(400, "orientation must be 'VERTICAL' or 'HORIZONTAL'")

    scene = await get_scene(sid)
    if not scene:
        raise HTTPException(404, "Scene not found")
    if scene.get("video_id") != vid:
        raise HTTPException(404, "Scene does not belong to this video")

    characters = await get_project_characters(project_id)

    logger.info("Starting %s review for scene %s (%s)", mode, sid, orientation)
    try:
        result = await review_scene_video(scene, characters, mode=mode, orientation=orientation.upper())
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Review failed for scene %s: %s", sid, e)
        raise HTTPException(500, f"Review failed: {e}")

    return result
