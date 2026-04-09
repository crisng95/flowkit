"""FastAPI router for video review endpoints."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from agent.models.review import VideoReview, SceneReview
from agent.services.video_reviewer import review_video, review_scene_video
from agent.db.crud import get_video, get_scene, get_project_characters, list_scenes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["reviews"])


@router.post("/{vid}/review", response_model=VideoReview)
async def review_video_endpoint(
    vid: str,
    project_id: str = Query(..., description="Project ID"),
    mode: str = Query("light", description="Review mode: light (4fps) or deep (8fps)"),
    orientation: Optional[str] = Query(None, description="Orientation: VERTICAL or HORIZONTAL (auto-detected if omitted)"),
):
    """Review all scene videos in a video using Claude Vision frame analysis."""
    if mode not in ("light", "deep"):
        raise HTTPException(400, "mode must be 'light' or 'deep'")
    if orientation and orientation.upper() not in ("VERTICAL", "HORIZONTAL"):
        raise HTTPException(400, "orientation must be 'VERTICAL' or 'HORIZONTAL'")

    video = await get_video(vid)
    if not video:
        raise HTTPException(404, "Video not found")

    # Use video-level orientation first, then fall back to scene auto-detect
    if not orientation:
        if video.get("orientation"):
            orientation = video["orientation"]
        else:
            orientation = await _detect_orientation(vid)
    else:
        orientation = orientation.upper()

    logger.info("Starting %s review for video %s (project %s, %s)", mode, vid, project_id, orientation)
    try:
        result = await review_video(vid, project_id, mode=mode, orientation=orientation)
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
    orientation: Optional[str] = Query(None, description="Orientation: VERTICAL or HORIZONTAL (auto-detected if omitted)"),
):
    """Review a single scene video using Claude Vision frame analysis."""
    if mode not in ("light", "deep"):
        raise HTTPException(400, "mode must be 'light' or 'deep'")
    if orientation and orientation.upper() not in ("VERTICAL", "HORIZONTAL"):
        raise HTTPException(400, "orientation must be 'VERTICAL' or 'HORIZONTAL'")

    scene = await get_scene(sid)
    if not scene:
        raise HTTPException(404, "Scene not found")
    if scene.get("video_id") != vid:
        raise HTTPException(404, "Scene does not belong to this video")

    # Use video-level orientation first, then fall back to scene auto-detect
    if not orientation:
        video = await get_video(vid)
        if video and video.get("orientation"):
            orientation = video["orientation"]
        else:
            orientation = await _detect_orientation(vid)
    else:
        orientation = orientation.upper()

    characters = await get_project_characters(project_id)

    logger.info("Starting %s review for scene %s (%s)", mode, sid, orientation)
    try:
        result = await review_scene_video(scene, characters, mode=mode, orientation=orientation, project_id=project_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Review failed for scene %s: %s", sid, e)
        raise HTTPException(500, f"Review failed: {e}")

    return result


async def _detect_orientation(video_id: str) -> str:
    """Auto-detect orientation from scene video status fields."""
    scenes = await list_scenes(video_id)
    for scene in scenes:
        if scene.get("horizontal_video_status") == "COMPLETED" and scene.get("horizontal_video_url"):
            return "HORIZONTAL"
        if scene.get("vertical_video_status") == "COMPLETED" and scene.get("vertical_video_url"):
            return "VERTICAL"
    # Fallback: check image status
    for scene in scenes:
        if scene.get("horizontal_image_status") == "COMPLETED":
            return "HORIZONTAL"
        if scene.get("vertical_image_status") == "COMPLETED":
            return "VERTICAL"
    return "VERTICAL"
