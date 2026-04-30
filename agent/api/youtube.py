"""YouTube upload endpoints."""
from __future__ import annotations

import asyncio
import importlib.util
import inspect
from pathlib import Path
from types import ModuleType
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.config import BASE_DIR, OUTPUT_DIR
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.services.event_bus import event_bus
from agent.utils.slugify import slugify

router = APIRouter(prefix="/youtube", tags=["youtube"])

_repo = SQLiteRepository()


class YouTubeUploadRequest(BaseModel):
    project_id: str
    video_id: str
    title: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    privacy_status: Literal["private", "unlisted", "public"] = "private"
    video_path: str | None = None
    channel_name: str | None = None
    schedule_at: str | None = None


class YouTubeUploadResponse(BaseModel):
    video_id: str
    url: str | None = None
    channel_name: str


def _load_youtube_module() -> ModuleType | None:
    module_path = BASE_DIR / "youtube" / "upload.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("flowkit_youtube_upload", module_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _detect_channel_name(explicit: str | None) -> str:
    if explicit:
        return explicit
    channels_dir = BASE_DIR / "youtube" / "channels"
    if not channels_dir.exists():
        raise HTTPException(400, "Missing youtube/channels directory. Configure a channel first.")

    channels = [p.name for p in channels_dir.iterdir() if p.is_dir()]
    if not channels:
        raise HTTPException(400, "No channel found under youtube/channels. Configure one and retry.")
    if len(channels) > 1:
        raise HTTPException(400, "Multiple channels detected. Please pass channel_name explicitly.")
    return channels[0]


def _resolve_video_path(
    requested_path: str | None,
    project_slug: str,
    orientation: str,
    sdk_video,
) -> Path:
    if requested_path:
        p = Path(requested_path).expanduser()
        if p.exists():
            return p
        raise HTTPException(400, f"video_path does not exist: {requested_path}")

    # Prefer explicit local final files.
    final_candidates = [
        OUTPUT_DIR / project_slug / f"{project_slug}_final_{orientation.lower()}_music.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_{orientation.lower()}.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_vertical_music.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_vertical.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_horizontal_music.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_horizontal.mp4",
    ]
    for candidate in final_candidates:
        if candidate.exists():
            return candidate

    # Fallback to video table local path.
    for candidate in (sdk_video.vertical_url, sdk_video.horizontal_url):
        if not candidate:
            continue
        p = Path(candidate)
        if p.exists():
            return p

    raise HTTPException(
        400,
        "Could not infer final video path. Please run concat first or pass video_path explicitly.",
    )


async def _call_upload_function(upload_fn, kwargs: dict):
    sig = inspect.signature(upload_fn)
    accepted_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in sig.parameters and value is not None
    }
    if inspect.iscoroutinefunction(upload_fn):
        return await upload_fn(**accepted_kwargs)
    return await asyncio.to_thread(upload_fn, **accepted_kwargs)


@router.post("/upload", response_model=YouTubeUploadResponse)
async def upload_to_youtube(body: YouTubeUploadRequest):
    sdk_video = await _repo.get_video(body.video_id)
    if not sdk_video:
        raise HTTPException(404, "Video not found")
    if sdk_video.project_id != body.project_id:
        raise HTTPException(400, "project_id does not match this video")

    project = await _repo.get_project(body.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    module = _load_youtube_module()
    if not module:
        raise HTTPException(
            501,
            "YouTube uploader is not installed (missing youtube/upload.py).",
        )
    upload_fn = getattr(module, "upload_video", None)
    if not callable(upload_fn):
        raise HTTPException(501, "youtube/upload.py is missing required function: upload_video")

    channel_name = _detect_channel_name(body.channel_name)
    orientation = (sdk_video.orientation or project.orientation or "VERTICAL").upper()
    project_slug = slugify(project.name)
    video_path = _resolve_video_path(body.video_path, project_slug, orientation, sdk_video)

    try:
        raw_result = await _call_upload_function(
            upload_fn,
            {
                "channel_name": channel_name,
                "video_path": str(video_path),
                "title": body.title.strip(),
                "description": body.description.strip(),
                "tags": body.tags,
                "privacy_status": body.privacy_status,
                "privacy": body.privacy_status,
                "schedule_at": body.schedule_at,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"YouTube upload failed: {e}") from e

    yt_video_id = None
    url = None

    if isinstance(raw_result, str):
        yt_video_id = raw_result
    elif isinstance(raw_result, dict):
        yt_video_id = (
            raw_result.get("video_id")
            or raw_result.get("youtube_id")
            or raw_result.get("id")
        )
        url = raw_result.get("url")
    elif isinstance(raw_result, tuple) and raw_result:
        yt_video_id = raw_result[0]
        if len(raw_result) > 1:
            url = raw_result[1]

    if not yt_video_id:
        raise HTTPException(502, "YouTube uploader returned no video_id")
    if not url:
        url = f"https://youtu.be/{yt_video_id}"

    await _repo.update(
        "video",
        body.video_id,
        youtube_id=yt_video_id,
        privacy=body.privacy_status,
        tags=",".join(body.tags) if body.tags else None,
    )
    await event_bus.emit("youtube_uploaded", {
        "video_id": body.video_id,
        "youtube_id": yt_video_id,
        "url": url,
        "channel_name": channel_name,
    })

    return YouTubeUploadResponse(video_id=yt_video_id, url=url, channel_name=channel_name)
