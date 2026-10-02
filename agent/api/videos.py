import asyncio
import logging
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.utils.paths import file_url_to_path
from agent.config import OUTPUT_DIR
from agent.db import crud
from agent.models.video import Video, VideoCreate, VideoUpdate
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.services.post_process import (
    add_music,
    add_narration,
    merge_videos,
    normalize_clip,
    probe_duration,
    trim_video,
)
from agent.utils.slugify import slugify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])

_repo = SQLiteRepository()


def _video_to_flat(sdk_video) -> dict:
    """Convert SDK Video domain model to flat dict matching API response shape."""
    return {
        "id": sdk_video.id,
        "project_id": sdk_video.project_id,
        "title": sdk_video.title,
        "description": sdk_video.description,
        "display_order": sdk_video.display_order,
        "status": sdk_video.status,
        "orientation": sdk_video.orientation,
        "vertical_url": sdk_video.vertical_url,
        "horizontal_url": sdk_video.horizontal_url,
        "thumbnail_url": sdk_video.thumbnail_url,
        "duration": sdk_video.duration,
        "target_duration_s": sdk_video.target_duration_s,
        "resolution": sdk_video.resolution,
        "youtube_id": sdk_video.youtube_id,
        "privacy": sdk_video.privacy,
        "tags": sdk_video.tags,
        "created_at": sdk_video.created_at,
        "updated_at": sdk_video.updated_at,
    }


@router.post("", response_model=Video)
async def create(body: VideoCreate):
    sdk_video = await _repo.create_video(**body.model_dump(exclude_none=True))
    return _video_to_flat(sdk_video)


@router.get("", response_model=list[Video])
async def list_by_project(project_id: str):
    videos = await _repo.list_videos(project_id)
    return [_video_to_flat(v) for v in videos]


@router.get("/{vid}", response_model=Video)
async def get(vid: str):
    sdk_video = await _repo.get_video(vid)
    if not sdk_video:
        raise HTTPException(404, "Video not found")
    return _video_to_flat(sdk_video)


@router.patch("/{vid}", response_model=Video)
async def update(vid: str, body: VideoUpdate):
    row = await _repo.update("video", vid, **body.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(404, "Video not found")
    sdk_video = _repo._row_to_video(row)
    return _video_to_flat(sdk_video)


@router.delete("/{vid}")
async def delete(vid: str):
    if not await _repo.delete("video", vid):
        raise HTTPException(404, "Video not found")
    return {"ok": True}


# ── Concat / finalize ──────────────────────────────────────────────────

class ConcatRequest(BaseModel):
    orientation: Optional[str] = Field(None, description="VERTICAL|HORIZONTAL; defaults to the video's orientation")
    target_duration_s: Optional[float] = Field(None, gt=0, description="Trim the merged video to this length")
    output_filename: Optional[str] = None


class ConcatResponse(BaseModel):
    video_id: str
    output_path: str
    url: str
    duration: Optional[float] = None
    target_duration_s: Optional[float] = None
    trimmed: bool = False
    scenes_used: int = 0
    scenes_missing: list[str] = []


class FinalizeRequest(BaseModel):
    orientation: Optional[str] = None
    target_duration_s: Optional[float] = Field(None, gt=0)
    music_path: Optional[str] = None
    narration_path: Optional[str] = None
    music_volume: float = 0.3


class FinalizeResponse(BaseModel):
    video_id: str
    output_path: str
    url: str
    duration: Optional[float] = None
    status: str = "COMPLETED"
    steps: list[str] = []


def _resolve_media_local(url: str, tmpdir: Path) -> Optional[str]:
    """Resolve a media URL to a local file path (downloading http(s) when needed)."""
    if not url:
        return None
    local = file_url_to_path(url)
    if local is not None:
        return str(local) if local.is_file() else None
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        dest = tmpdir / f"dl_{abs(hash(url)) % 10**8}{Path(parsed.path).suffix or '.mp4'}"
        try:
            urllib.request.urlretrieve(url, dest)
            return str(dest)
        except Exception as e:
            logger.warning("concat: failed to download %s: %s", url, e)
            return None
    p = Path(url)
    return str(p) if p.is_file() else None


async def _assemble_video(vid: str, orientation: Optional[str],
                          target_duration_s: Optional[float],
                          output_filename: Optional[str],
                          tag: str) -> dict:
    """Concat scene clips for one orientation; returns assembly details."""
    sdk_video = await _repo.get_video(vid)
    if not sdk_video:
        raise HTTPException(404, "Video not found")

    orientation = (orientation or sdk_video.orientation or "VERTICAL").upper()
    if orientation not in ("VERTICAL", "HORIZONTAL"):
        raise HTTPException(400, "orientation must be VERTICAL or HORIZONTAL")

    scenes = await crud.list_scenes(vid)
    if not scenes:
        raise HTTPException(404, "No scenes found for video")

    project = await crud.get_project(sdk_video.project_id)
    project_slug = slugify((project or {}).get("name") or "project")
    out_dir = OUTPUT_DIR / project_slug / "final"
    out_dir.mkdir(parents=True, exist_ok=True)

    url_key = f"{orientation.lower()}_video_url"
    tmpdir = Path(tempfile.mkdtemp(prefix="concat_"))
    clips: list[str] = []
    missing: list[str] = []
    try:
        for scene in scenes:
            local = await asyncio.to_thread(
                _resolve_media_local, scene.get(url_key), tmpdir)
            if not local:
                missing.append(scene["id"])
                continue
            norm = tmpdir / f"norm_{scene['id']}.mp4"
            ok = await asyncio.to_thread(normalize_clip, local, str(norm))
            if not ok:
                missing.append(scene["id"])
                continue
            clips.append(str(norm))

        if not clips:
            raise HTTPException(
                400, f"No usable {orientation.lower()} clips "
                     f"({len(missing)} scenes missing video)")

        fname = output_filename or f"{slugify(sdk_video.title) or 'video'}_{tag}_{orientation.lower()}.mp4"
        final_path = out_dir / fname
        merged = await asyncio.to_thread(merge_videos, clips, str(final_path))
        if not merged:
            raise HTTPException(502, "ffmpeg concat failed")

        duration = await asyncio.to_thread(probe_duration, str(final_path))
        target = target_duration_s or sdk_video.target_duration_s
        trimmed = False
        if target and duration and duration > target:
            trimmed_path = out_dir / f"{final_path.stem}_trimmed.mp4"
            ok = await asyncio.to_thread(
                trim_video, str(final_path), str(trimmed_path), 0, target)
            if ok:
                final_path = trimmed_path
                duration = target
                trimmed = True
            else:
                logger.warning("concat: trim to %ss failed, keeping full length", target)

        url = "file://" + str(final_path.resolve())
        updates: dict = {f"{orientation.lower()}_url": url, "duration": duration}
        if target is not None:
            updates["target_duration_s"] = target
        await crud.update_video(vid, **updates)
        return {
            "video_id": vid,
            "output_path": str(final_path),
            "url": url,
            "duration": duration,
            "target_duration_s": target,
            "trimmed": trimmed,
            "scenes_used": len(clips),
            "scenes_missing": missing,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@router.post("/{vid}/concat", response_model=ConcatResponse)
async def concat_video(vid: str, body: ConcatRequest):
    """Merge scene clips (display_order) into one video file.

    Provider-neutral: clips may be file:// URLs (assistant provider) or
    https:// URLs (Flow) — remote clips are downloaded first and every clip
    is normalized to uniform h264/AAC before concat.
    """
    return await _assemble_video(
        vid, body.orientation, body.target_duration_s,
        body.output_filename, tag="concat")


@router.post("/{vid}/finalize", response_model=FinalizeResponse)
async def finalize_video(vid: str, body: FinalizeRequest):
    """Full finish: concat (+ optional trim) → music/narration mix → COMPLETED."""
    asm = await _assemble_video(
        vid, body.orientation, body.target_duration_s, None, tag="final")
    steps = [f"concat ({asm['scenes_used']} scenes)"]
    if asm["trimmed"]:
        steps.append(f"trimmed to {asm['target_duration_s']}s")

    final_path = Path(asm["output_path"])
    if body.music_path:
        mixed = final_path.parent / f"{final_path.stem}_music.mp4"
        ok = await asyncio.to_thread(
            add_music, str(final_path), body.music_path, str(mixed),
            body.music_volume)
        if not ok:
            raise HTTPException(502, "ffmpeg music mix failed")
        final_path = mixed
        steps.append("music mix")
    if body.narration_path:
        mixed = final_path.parent / f"{final_path.stem}_narrated.mp4"
        ok = await asyncio.to_thread(
            add_narration, str(final_path), body.narration_path, str(mixed))
        if not ok:
            raise HTTPException(502, "ffmpeg narration mix failed")
        final_path = mixed
        steps.append("narration mix")

    duration = await asyncio.to_thread(probe_duration, str(final_path))
    url = "file://" + str(final_path.resolve())
    orientation = (body.orientation or "").upper()
    updates: dict = {"status": "COMPLETED"}
    if duration is not None:
        updates["duration"] = duration
    if orientation in ("VERTICAL", "HORIZONTAL"):
        updates[f"{orientation.lower()}_url"] = url
    else:
        # keep the concat orientation's URL in sync
        key = "vertical_url" if "_vertical" in asm["output_path"] else "horizontal_url"
        updates[key] = url
    await crud.update_video(vid, **updates)

    return FinalizeResponse(
        video_id=vid, output_path=str(final_path), url=url,
        duration=duration, steps=steps)
