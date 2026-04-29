import asyncio
import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.config import OUTPUT_DIR, SHARED_OUTPUT_DIR
from agent.models.video import Video, VideoCreate, VideoUpdate
from agent.models.enums import ChainType, SceneSource
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.services.event_bus import event_bus
from agent.services.flow_client import get_flow_client
from agent.services.post_process import add_music, add_narration, merge_videos, trim_video
from agent.utils.paths import resolve_4k_file, scene_filename, scene_tts_path
from agent.utils.slugify import slugify
from agent.utils.orientation import normalize_orientation

router = APIRouter(prefix="/videos", tags=["videos"])

_repo = SQLiteRepository()
logger = logging.getLogger(__name__)


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
        "resolution": sdk_video.resolution,
        "youtube_id": sdk_video.youtube_id,
        "privacy": sdk_video.privacy,
        "tags": sdk_video.tags,
        "created_at": sdk_video.created_at,
        "updated_at": sdk_video.updated_at,
    }


class ConcatRequest(BaseModel):
    project_id: str | None = None
    orientation: str | None = None
    with_narrator: bool = True
    with_music: bool = False
    force_4k: bool = False
    fit_narrator: bool = False
    narrator_buffer: float = 0.5
    export_root_dir: str | None = None
    export_assets: bool = True


class ConcatResponse(BaseModel):
    output_path: str
    scenes: int
    orientation: str
    resolution: str
    with_narrator: bool
    with_music: bool
    fit_narrator: bool = False
    narrator_buffer: float = 0.5
    export_dir: str | None = None
    exported_images: int = 0
    exported_videos: int = 0
    failed_assets: int = 0


class DownloadAssetsRequest(BaseModel):
    project_id: str | None = None
    orientation: str | None = None
    rebind_scene_urls: bool = True


class DownloadAssetsResponse(BaseModel):
    ok: bool
    video_id: str
    orientation: str
    download_dir: str
    images_downloaded: int
    videos_downloaded: int
    scene_url_rebound: int
    failed: list[str] = []


class ScriptScenePayload(BaseModel):
    display_order: int | None = None
    prompt: str | None = None
    image_prompt: str | None = None
    video_prompt: str | None = None
    narrator_text: str | None = None
    character_names: list[str] | str | None = None
    transition_prompt: str | None = None
    chain_type: ChainType = "ROOT"
    source: SceneSource = "root"


class ScriptVideoMetaPayload(BaseModel):
    title: str | None = None
    description: str | None = None
    orientation: str | None = None


class ScriptImportRequest(BaseModel):
    format_version: int | None = None
    title: str | None = None
    description: str | None = None
    orientation: str | None = None
    video: ScriptVideoMetaPayload | None = None
    scenes: list[ScriptScenePayload]
    replace_existing: bool = True
    clear_requests: bool = True


class ScriptImportResponse(BaseModel):
    ok: bool
    video_id: str
    scenes_total: int
    deleted_scenes: int
    deleted_requests: int
    orientation: str
    title: str


def _probe_resolution(path: Path) -> tuple[int, int] | None:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    if "x" not in text:
        return None
    try:
        w, h = text.split("x", 1)
        return int(w), int(h)
    except ValueError:
        return None


def _probe_duration(path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def _normalize_clip(input_path: Path, output_path: Path, width: int, height: int) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-r", "24",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        logger.error("Normalize failed for %s: %s", input_path, result.stderr[-300:])
        return False
    return True


def _extract_first_url(payload) -> str | None:
    def _is_direct_media_url(url: str) -> bool:
        low = (url or "").lower()
        if not low.startswith("http"):
            return False
        if "media.getmediaurlredirect" in low:
            return False
        if low.startswith("https://flow-content.google/"):
            return True
        if low.startswith("https://storage.googleapis.com/"):
            return True
        if "googleusercontent.com/" in low:
            return True
        return False

    if isinstance(payload, dict):
        for key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri"):
            value = payload.get(key)
            if isinstance(value, str) and _is_direct_media_url(value):
                return value
        for value in payload.values():
            found = _extract_first_url(value)
            if found:
                return found
        return None
    if isinstance(payload, list):
        for item in payload:
            found = _extract_first_url(item)
            if found:
                return found
        return None
    return None


async def _download_file(url: str, output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=180)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False
                output_path.write_bytes(await resp.read())
                return True
    except Exception:
        return False


async def _refresh_media_url(media_id: str | None) -> str | None:
    if not media_id:
        return None
    client = get_flow_client()
    if not client.connected:
        return None
    result = await client.get_media(media_id)
    if result.get("error"):
        return None
    return _extract_first_url(result.get("data", result))


def _find_music_file(project_slug: str) -> Path | None:
    project_music_dir = OUTPUT_DIR / project_slug / "music"
    candidates = []
    for root in (project_music_dir, SHARED_OUTPUT_DIR / "music"):
        if not root.exists():
            continue
        for pattern in ("*.wav", "*.mp3", "*.m4a"):
            candidates.extend(root.glob(pattern))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


async def _resolve_scene_source(scene, orientation: str, project_slug: str) -> Path:
    local_4k = resolve_4k_file(project_slug, scene.display_order, scene.id)
    if local_4k and local_4k.exists():
        return local_4k

    slot = scene.vertical if orientation == "VERTICAL" else scene.horizontal
    for candidate in (slot.upscale.url, slot.video.url):
        if not candidate or candidate.startswith("http"):
            continue
        p = Path(candidate)
        if p.exists():
            return p

    remote_url = slot.upscale.url or slot.video.url
    media_id = slot.upscale.media_id or slot.video.media_id
    if not remote_url:
        raise RuntimeError(f"Scene {scene.display_order + 1} has no generated {orientation.lower()} video")

    target = OUTPUT_DIR / project_slug / "4k" / f"scene_{scene.display_order:03d}_{scene.id}.mp4"
    ok = await _download_file(remote_url, target)
    if not ok:
        refreshed = await _refresh_media_url(media_id)
        if refreshed:
            ok = await _download_file(refreshed, target)
    if not ok or not target.exists():
        raise RuntimeError(f"Failed downloading scene {scene.display_order + 1} video source")
    return target


def _suffix_from_uri(uri: str | None, default_suffix: str) -> str:
    if not uri:
        return default_suffix
    try:
        parsed = urlparse(uri)
        suffix = Path(parsed.path).suffix.lower()
    except Exception:
        suffix = ""
    if 1 <= len(suffix) <= 8:
        return suffix
    return default_suffix


def _parse_character_names(raw: list[str] | str | None) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        # Try JSON first to support edited export payloads.
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = None
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        return [part.strip() for part in text.split(",") if part.strip()]
    return []


def _coalesce_script_text(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _build_local_media_proxy_url(path: Path) -> str:
    return f"http://127.0.0.1:8100/api/flow/local-media?path={quote(str(path), safe='')}"


def _extract_local_media_path(raw_url: str | None) -> Path | None:
    if not isinstance(raw_url, str):
        return None
    text = raw_url.strip()
    if not text:
        return None

    if text.startswith("http://") or text.startswith("https://"):
        try:
            parsed = urlparse(text)
            host = (parsed.hostname or "").lower()
            if host not in ("127.0.0.1", "localhost"):
                return None
            if parsed.path.rstrip("/") != "/api/flow/local-media":
                return None
            raw_path = (parse_qs(parsed.query).get("path") or [None])[0]
            if not isinstance(raw_path, str) or not raw_path.strip():
                return None
            candidate = Path(unquote(raw_path)).expanduser()
            return candidate if candidate.is_absolute() else None
        except Exception:
            return None

    if text.startswith("file://"):
        try:
            parsed = urlparse(text)
            candidate = Path(unquote(parsed.path)).expanduser()
            return candidate if candidate.is_absolute() else None
        except Exception:
            return None

    candidate = Path(text).expanduser()
    return candidate if candidate.is_absolute() else None


async def _copy_file(src: Path, dst: Path) -> bool:
    try:
        try:
            if src.resolve() == dst.resolve():
                return True
        except Exception:
            pass
        dst.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, src, dst)
        return True
    except Exception:
        return False


async def _materialize_media_to_local(
    *,
    source_url: str | None,
    media_id: str | None,
    default_suffix: str,
    target_base_path: Path,
) -> Path | None:
    local = _extract_local_media_path(source_url)
    if local and local.exists() and local.is_file():
        target = target_base_path.with_suffix(local.suffix or default_suffix)
        if await _copy_file(local, target):
            return target

    if source_url and source_url.startswith("http"):
        suffix = _suffix_from_uri(source_url, default_suffix)
        target = target_base_path.with_suffix(suffix)
        if await _download_file(source_url, target):
            return target

    refreshed = await _refresh_media_url(media_id)
    if refreshed:
        suffix = _suffix_from_uri(refreshed, default_suffix)
        target = target_base_path.with_suffix(suffix)
        if await _download_file(refreshed, target):
            return target

    return None


def _scene_local_sources(scene, orientation: str):
    primary_vertical = normalize_orientation(orientation) == "VERTICAL"
    ordered = (
        [("vertical", scene.vertical), ("horizontal", scene.horizontal)]
        if primary_vertical
        else [("horizontal", scene.horizontal), ("vertical", scene.vertical)]
    )

    image_source = None
    video_source = None
    for prefix, slot in ordered:
        if not image_source and (slot.image.url or slot.image.media_id):
            image_source = {
                "field": f"{prefix}_image_url",
                "status_field": f"{prefix}_image_status",
                "url": slot.image.url,
                "media_id": slot.image.media_id,
                "default_suffix": ".png",
                "kind": "image",
                "axis": prefix,
            }
        if not video_source:
            if slot.upscale.url or slot.upscale.media_id:
                video_source = {
                    "field": f"{prefix}_upscale_url",
                    "status_field": f"{prefix}_upscale_status",
                    "url": slot.upscale.url,
                    "media_id": slot.upscale.media_id,
                    "default_suffix": ".mp4",
                    "kind": "upscale",
                    "axis": prefix,
                }
            elif slot.video.url or slot.video.media_id:
                video_source = {
                    "field": f"{prefix}_video_url",
                    "status_field": f"{prefix}_video_status",
                    "url": slot.video.url,
                    "media_id": slot.video.media_id,
                    "default_suffix": ".mp4",
                    "kind": "video",
                    "axis": prefix,
                }
        if image_source and video_source:
            break

    return image_source, video_source


def _canonical_scene_target_base_path(project_slug: str, scene, source: dict) -> Path:
    kind = str(source.get("kind") or "image")
    axis = str(source.get("axis") or "horizontal")
    scene_idx = int(scene.display_order) + 1
    ext = "png" if kind == "image" else "mp4"
    canonical_name = scene_filename(scene_idx, scene.id, ext=ext)
    subdir = "images" if kind == "image" else ("upscale" if kind == "upscale" else "videos")
    return OUTPUT_DIR / project_slug / subdir / axis / canonical_name


async def _export_scene_assets(
    scenes: list,
    orientation: str,
    project_slug: str,
    export_dir: Path,
) -> tuple[int, int, int]:
    images_dir = export_dir / "images"
    videos_dir = export_dir / "videos"
    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    exported_images = 0
    exported_videos = 0
    failed_assets = 0

    for scene in scenes:
        scene_idx = int(scene.display_order) + 1
        file_base = f"scene_{scene_idx:03d}"
        slot = scene.vertical if orientation == "VERTICAL" else scene.horizontal

        # Export image
        image_local_ok = False
        image_url = slot.image.url
        image_media_id = slot.image.media_id
        image_local = None
        if image_url and not image_url.startswith("http"):
            p = Path(image_url)
            if p.exists():
                image_local = p

        image_suffix = _suffix_from_uri(image_url, ".png")
        image_target = images_dir / f"{file_base}{image_suffix}"
        if image_local and await _copy_file(image_local, image_target):
            image_local_ok = True
        elif image_url and image_url.startswith("http"):
            image_local_ok = await _download_file(image_url, image_target)
        if not image_local_ok and image_media_id:
            refreshed = await _refresh_media_url(image_media_id)
            if refreshed:
                refreshed_target = images_dir / f"{file_base}{_suffix_from_uri(refreshed, image_suffix)}"
                image_local_ok = await _download_file(refreshed, refreshed_target)
        if image_local_ok:
            exported_images += 1
        else:
            failed_assets += 1

        # Export video source in selected orientation (prefer local resolved path)
        video_local_ok = False
        try:
            scene_source = await _resolve_scene_source(scene, orientation, project_slug)
            video_target = videos_dir / f"{file_base}.mp4"
            video_local_ok = await _copy_file(scene_source, video_target)
        except Exception:
            video_local_ok = False
        if video_local_ok:
            exported_videos += 1
        else:
            failed_assets += 1

    return exported_images, exported_videos, failed_assets


@router.post("", response_model=Video)
async def create(body: VideoCreate):
    create_data = body.model_dump(exclude_none=True)
    if create_data.get("orientation"):
        create_data["orientation"] = normalize_orientation(create_data["orientation"])
    if "orientation" not in create_data or not create_data["orientation"]:
        project = await _repo.get_project(body.project_id)
        create_data["orientation"] = normalize_orientation(project.orientation if project else "VERTICAL")
    sdk_video = await _repo.create_video(**create_data)
    await event_bus.emit("video_created", {
        "id": sdk_video.id,
        "project_id": sdk_video.project_id,
        "orientation": sdk_video.orientation,
    })
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
    update_data = body.model_dump(exclude_unset=True)
    if update_data.get("orientation"):
        update_data["orientation"] = normalize_orientation(update_data["orientation"])
    row = await _repo.update("video", vid, **update_data)
    if not row:
        raise HTTPException(404, "Video not found")
    sdk_video = _repo._row_to_video(row)
    await event_bus.emit("video_updated", {
        "id": sdk_video.id,
        "project_id": sdk_video.project_id,
        "orientation": sdk_video.orientation,
    })
    return _video_to_flat(sdk_video)


@router.delete("/{vid}")
async def delete(vid: str):
    video = await _repo.get_video(vid)
    if not await _repo.delete("video", vid):
        raise HTTPException(404, "Video not found")
    await event_bus.emit("video_deleted", {"id": vid, "project_id": video.project_id if video else None})
    return {"ok": True}


@router.post("/{vid}/download-assets", response_model=DownloadAssetsResponse)
async def download_assets(vid: str, body: DownloadAssetsRequest):
    sdk_video = await _repo.get_video(vid)
    if not sdk_video:
        raise HTTPException(404, "Video not found")
    project = await _repo.get_project(sdk_video.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    if body.project_id and body.project_id != sdk_video.project_id:
        raise HTTPException(400, "project_id does not match this video")

    orientation = normalize_orientation(
        body.orientation or sdk_video.orientation or project.orientation or "VERTICAL"
    )
    scenes = sorted(await _repo.list_scenes(vid), key=lambda s: s.display_order)
    if not scenes:
        raise HTTPException(400, "No scenes found")

    project_slug = slugify(project.name) or f"project_{project.id[:8]}"
    video_slug = slugify(sdk_video.title) or f"video_{sdk_video.id[:8]}"
    video_order = int(sdk_video.display_order or 0) + 1
    legacy_download_dir = OUTPUT_DIR / project_slug / "downloads" / f"video_{video_order:03d}_{video_slug}"
    canonical_root_dir = OUTPUT_DIR / project_slug

    images_downloaded = 0
    videos_downloaded = 0
    scene_url_rebound = 0
    failed: list[str] = []

    for scene in scenes:
        scene_idx = int(scene.display_order) + 1
        image_source, video_source = _scene_local_sources(scene, orientation)

        if image_source:
            target = await _materialize_media_to_local(
                source_url=image_source["url"],
                media_id=image_source["media_id"],
                default_suffix=image_source["default_suffix"],
                target_base_path=_canonical_scene_target_base_path(project_slug, scene, image_source),
            )
            if target:
                images_downloaded += 1
                if body.rebind_scene_urls:
                    proxy_url = _build_local_media_proxy_url(target)
                    await _repo.update(
                        "scene",
                        scene.id,
                        **{
                            image_source["field"]: proxy_url,
                            image_source["status_field"]: "COMPLETED",
                        },
                    )
                    scene_url_rebound += 1
            else:
                failed.append(f"scene_{scene_idx:03d}: image")

        if video_source:
            target = await _materialize_media_to_local(
                source_url=video_source["url"],
                media_id=video_source["media_id"],
                default_suffix=video_source["default_suffix"],
                target_base_path=_canonical_scene_target_base_path(project_slug, scene, video_source),
            )
            if target:
                videos_downloaded += 1
                if body.rebind_scene_urls:
                    proxy_url = _build_local_media_proxy_url(target)
                    await _repo.update(
                        "scene",
                        scene.id,
                        **{
                            video_source["field"]: proxy_url,
                            video_source["status_field"]: "COMPLETED",
                        },
                    )
                    scene_url_rebound += 1
            else:
                failed.append(f"scene_{scene_idx:03d}: video")

    await event_bus.emit(
        "scene_updated",
        {
            "id": "download-assets",
            "video_id": vid,
            "display_order": 0,
        },
    )
    await event_bus.emit(
        "video_assets_downloaded",
        {
            "id": vid,
            "project_id": sdk_video.project_id,
            "orientation": orientation,
            "download_dir": str(canonical_root_dir),
            "images_downloaded": images_downloaded,
            "videos_downloaded": videos_downloaded,
        },
    )

    # Best-effort cleanup: old builds wrote duplicated local copies under output/<project>/downloads/.
    # We now persist canonical files under output/<project>/{images,videos,upscale}/...
    try:
        if legacy_download_dir.exists() and legacy_download_dir.is_dir():
            shutil.rmtree(legacy_download_dir)
    except Exception:
        # Non-fatal; local assets are already rebound to canonical paths above.
        pass

    return DownloadAssetsResponse(
        ok=True,
        video_id=vid,
        orientation=orientation,
        download_dir=str(canonical_root_dir),
        images_downloaded=images_downloaded,
        videos_downloaded=videos_downloaded,
        scene_url_rebound=scene_url_rebound,
        failed=failed,
    )


@router.get("/{vid}/script-export")
async def export_script(vid: str):
    sdk_video = await _repo.get_video(vid)
    if not sdk_video:
        raise HTTPException(404, "Video not found")
    project = await _repo.get_project(sdk_video.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    scenes = sorted(await _repo.list_scenes(vid), key=lambda s: s.display_order)
    return {
        "format_version": 1,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": {
            "id": project.id,
            "name": project.name,
            "orientation": project.orientation,
            "language": project.language,
            "material": project.material,
        },
        "video": {
            "id": sdk_video.id,
            "title": sdk_video.title,
            "description": sdk_video.description,
            "orientation": sdk_video.orientation or project.orientation,
        },
        "scenes": [
            {
                "display_order": scene.display_order,
                "prompt": scene.prompt,
                "image_prompt": scene.image_prompt,
                "video_prompt": scene.video_prompt,
                "narrator_text": scene.narrator_text,
                "character_names": scene.character_names or [],
                "transition_prompt": scene.transition_prompt,
                "chain_type": scene.chain_type,
                "source": scene.source,
            }
            for scene in scenes
        ],
    }


@router.post("/{vid}/script-import", response_model=ScriptImportResponse)
async def import_script(vid: str, body: ScriptImportRequest):
    if not body.scenes:
        raise HTTPException(400, "Script must include at least one scene")
    if not body.replace_existing:
        raise HTTPException(400, "Only replace_existing=true is supported")

    sdk_video = await _repo.get_video(vid)
    if not sdk_video:
        raise HTTPException(404, "Video not found")
    project = await _repo.get_project(sdk_video.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    normalized: list[dict[str, Any]] = []
    for i, scene in enumerate(body.scenes):
        prompt = _coalesce_script_text(
            scene.prompt,
            scene.image_prompt,
            scene.video_prompt,
            scene.narrator_text,
        )
        if not prompt:
            raise HTTPException(400, f"Scene #{i + 1} is missing prompt/image_prompt/video_prompt/narrator_text")
        normalized.append(
            {
                "order": scene.display_order if scene.display_order is not None else i,
                "prompt": prompt,
                "image_prompt": _coalesce_script_text(scene.image_prompt) or None,
                "video_prompt": _coalesce_script_text(scene.video_prompt) or None,
                "narrator_text": _coalesce_script_text(scene.narrator_text) or None,
                "character_names": _parse_character_names(scene.character_names) or None,
                "transition_prompt": _coalesce_script_text(scene.transition_prompt) or None,
                "chain_type": scene.chain_type or "ROOT",
                "source": scene.source or "root",
            }
        )

    # Stable sort by requested order then original index, then compact to 0..N-1.
    normalized = [item for _, item in sorted(enumerate(normalized), key=lambda pair: (pair[1]["order"], pair[0]))]
    for idx, item in enumerate(normalized):
        item["display_order"] = idx

    existing_scenes = await _repo.list_scenes(vid)
    deleted_scenes = 0
    for scene in existing_scenes:
        ok = await _repo.delete("scene", scene.id)
        if ok:
            deleted_scenes += 1

    deleted_requests = 0
    if body.clear_requests:
        req_rows = await _repo.list("request", video_id=vid)
        for row in req_rows:
            rid = row.get("id")
            if rid and await _repo.delete("request", rid):
                deleted_requests += 1

    for scene in normalized:
        await _repo.create_scene(
            video_id=vid,
            display_order=scene["display_order"],
            prompt=scene["prompt"],
            image_prompt=scene["image_prompt"],
            video_prompt=scene["video_prompt"],
            transition_prompt=scene["transition_prompt"],
            character_names=scene["character_names"],
            chain_type=scene["chain_type"],
            source=scene["source"],
            narrator_text=scene["narrator_text"],
        )

    # Reset derived/exported media for this video after script replacement.
    update_data: dict[str, Any] = {
        "status": "DRAFT",
        "vertical_url": None,
        "horizontal_url": None,
        "thumbnail_url": None,
        "duration": None,
        "resolution": None,
    }
    target_title = _coalesce_script_text(body.title, body.video.title if body.video else None)
    target_desc = _coalesce_script_text(body.description, body.video.description if body.video else None)
    target_ori_raw = _coalesce_script_text(body.orientation, body.video.orientation if body.video else None)
    if target_title:
        update_data["title"] = target_title
    if target_desc:
        update_data["description"] = target_desc
    if target_ori_raw:
        update_data["orientation"] = normalize_orientation(
            target_ori_raw,
            default=sdk_video.orientation or project.orientation or "VERTICAL",
        )
    row = await _repo.update("video", vid, **update_data)
    if not row:
        raise HTTPException(404, "Video not found")
    updated_video = _repo._row_to_video(row)

    await event_bus.emit(
        "video_updated",
        {
            "id": updated_video.id,
            "project_id": updated_video.project_id,
            "orientation": updated_video.orientation,
        },
    )
    await event_bus.emit(
        "scene_updated",
        {
            "id": "script-import",
            "video_id": vid,
            "display_order": 0,
        },
    )

    return ScriptImportResponse(
        ok=True,
        video_id=vid,
        scenes_total=len(normalized),
        deleted_scenes=deleted_scenes,
        deleted_requests=deleted_requests,
        orientation=updated_video.orientation or project.orientation or "VERTICAL",
        title=updated_video.title,
    )


@router.post("/{vid}/concat", response_model=ConcatResponse)
async def concat_video(vid: str, body: ConcatRequest):
    sdk_video = await _repo.get_video(vid)
    if not sdk_video:
        raise HTTPException(404, "Video not found")

    project = await _repo.get_project(sdk_video.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    if body.project_id and body.project_id != sdk_video.project_id:
        raise HTTPException(400, "project_id does not match this video")

    orientation = normalize_orientation(body.orientation or sdk_video.orientation or project.orientation or "VERTICAL")
    if orientation not in ("VERTICAL", "HORIZONTAL"):
        raise HTTPException(400, "orientation must be VERTICAL or HORIZONTAL")

    scenes = sorted(await _repo.list_scenes(vid), key=lambda s: s.display_order)
    if not scenes:
        raise HTTPException(400, "No scenes found")

    project_slug = slugify(project.name) or f"project_{project.id[:8]}"
    out_dir = OUTPUT_DIR / project_slug
    (out_dir / "4k").mkdir(parents=True, exist_ok=True)
    (out_dir / "narrated").mkdir(parents=True, exist_ok=True)
    (out_dir / "trimmed").mkdir(parents=True, exist_ok=True)
    (out_dir / "norm").mkdir(parents=True, exist_ok=True)

    # Resolve all scene sources first so we fail early if any scene is missing.
    source_paths: list[Path] = []
    for scene in scenes:
        try:
            source_paths.append(await _resolve_scene_source(scene, orientation, project_slug))
        except RuntimeError as e:
            raise HTTPException(400, str(e)) from e

    # Choose output resolution.
    if body.force_4k:
        width, height = ((2160, 3840) if orientation == "VERTICAL" else (3840, 2160))
    else:
        first_res = _probe_resolution(source_paths[0])
        if not first_res:
            width, height = ((1080, 1920) if orientation == "VERTICAL" else (1920, 1080))
        else:
            width, height = first_res

    normalized_paths: list[str] = []
    narrator_buffer = max(0.0, body.narrator_buffer)
    for scene, source in zip(scenes, source_paths):
        processing_source = source
        tts_path = scene_tts_path(project_slug, scene.display_order, scene.id)
        if not tts_path.exists():
            legacy_tts = out_dir / "tts" / f"{scene.id}.wav"
            if legacy_tts.exists():
                tts_path = legacy_tts

        if body.fit_narrator and tts_path.exists():
            tts_duration = _probe_duration(tts_path)
            video_duration = _probe_duration(processing_source)
            if tts_duration and video_duration:
                cut_duration = min(video_duration, tts_duration + narrator_buffer)
                if cut_duration > 0.05:
                    trimmed = out_dir / "trimmed" / f"scene_{scene.display_order:03d}_{scene.id}.mp4"
                    ok_trim = await asyncio.to_thread(
                        trim_video,
                        str(processing_source),
                        str(trimmed),
                        0.0,
                        cut_duration,
                    )
                    if not ok_trim:
                        raise HTTPException(500, f"Failed to trim scene {scene.display_order + 1} to narrator duration")
                    processing_source = trimmed

        if body.with_narrator:
            if tts_path.exists():
                narrated = out_dir / "narrated" / f"scene_{scene.display_order:03d}_{scene.id}.mp4"
                ok_mix = await asyncio.to_thread(
                    add_narration,
                    str(processing_source),
                    str(tts_path),
                    str(narrated),
                    replace_original=True,
                )
                if not ok_mix:
                    raise HTTPException(500, f"Failed to apply narration track for scene {scene.display_order + 1}")
                processing_source = narrated

        normalized = out_dir / "norm" / f"scene_{scene.display_order:03d}_{scene.id}.mp4"
        ok_norm = await asyncio.to_thread(_normalize_clip, processing_source, normalized, width, height)
        if not ok_norm:
            raise HTTPException(500, f"Failed to normalize scene {scene.display_order + 1}")
        normalized_paths.append(str(normalized))

    merged_output = out_dir / f"{project_slug}_final_{orientation.lower()}.mp4"
    ok_merge = await asyncio.to_thread(merge_videos, normalized_paths, str(merged_output))
    if not ok_merge:
        raise HTTPException(500, "Failed to concatenate scene videos")

    final_output = merged_output
    if body.with_music:
        music_path = _find_music_file(project_slug)
        if not music_path:
            raise HTTPException(400, "with_music=true but no music file found (expected output/<project>/music or output/_shared/music)")
        mixed_output = out_dir / f"{project_slug}_final_{orientation.lower()}_music.mp4"
        ok_music = await asyncio.to_thread(
            add_music,
            str(merged_output),
            str(music_path),
            str(mixed_output),
        )
        if not ok_music:
            raise HTTPException(500, "Failed to add background music")
        final_output = mixed_output

    export_dir_str: str | None = None
    exported_images = 0
    exported_videos = 0
    failed_assets = 0
    if body.export_assets and body.export_root_dir:
        try:
            export_root = Path(body.export_root_dir).expanduser().resolve()
            video_slug = slugify(sdk_video.title) or "video"
            video_order = int(sdk_video.display_order or 0) + 1
            project_export_dir = export_root / project_slug / f"video_{video_order:03d}_{video_slug}"
            final_dir = project_export_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            final_target = final_dir / f"final_{orientation.lower()}.mp4"
            if not await _copy_file(final_output, final_target):
                raise RuntimeError("Failed copying final video to export folder")

            exported_images, exported_videos, failed_assets = await _export_scene_assets(
                scenes=scenes,
                orientation=orientation,
                project_slug=project_slug,
                export_dir=project_export_dir,
            )
            export_dir_str = str(project_export_dir)
        except Exception as e:
            raise HTTPException(400, f"Export assets failed: {e}") from e

    update_fields = {
        "orientation": orientation,
        "resolution": f"{width}x{height}",
    }
    if orientation == "VERTICAL":
        update_fields["vertical_url"] = str(final_output)
    else:
        update_fields["horizontal_url"] = str(final_output)
    await _repo.update("video", vid, **update_fields)

    await event_bus.emit("video_concatenated", {
        "id": vid,
        "project_id": sdk_video.project_id,
        "orientation": orientation,
        "output_path": str(final_output),
        "export_dir": export_dir_str,
    })

    return ConcatResponse(
        output_path=str(final_output),
        scenes=len(scenes),
        orientation=orientation,
        resolution=f"{width}x{height}",
        with_narrator=body.with_narrator,
        with_music=body.with_music,
        fit_narrator=body.fit_narrator,
        narrator_buffer=narrator_buffer,
        export_dir=export_dir_str,
        exported_images=exported_images,
        exported_videos=exported_videos,
        failed_assets=failed_assets,
    )


@router.post("/{vid}/recompact")
async def recompact_scenes(vid: str):
    """Re-number scene display_order sequentially (0,1,2,...) to fix gaps."""
    scenes = await _repo.list_scenes(vid)
    if not scenes:
        raise HTTPException(404, "No scenes found for this video")
    sorted_scenes = sorted(scenes, key=lambda s: s.display_order)
    updated = 0
    for i, scene in enumerate(sorted_scenes):
        if scene.display_order != i:
            await _repo.update("scene", scene.id, display_order=i)
            updated += 1
    return {"total": len(sorted_scenes), "reordered": updated}
