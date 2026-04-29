"""Shared result parsing + DB update helpers for SDK direct execution and background processor."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote, urlparse

import aiohttp

from agent.config import API_HOST, API_PORT, OUTPUT_DIR
from agent.db import crud
from agent.utils.paths import scene_filename
from agent.utils.slugify import slugify
from agent.worker._parsing import (
    _extract_media_id,
    _extract_output_url,
    _is_direct_media_url,
    _is_error,
)

if TYPE_CHECKING:
    from agent.sdk.models.media import GenerationResult

logger = logging.getLogger(__name__)

_API_PUBLIC_HOST = "127.0.0.1" if API_HOST in {"0.0.0.0", "::"} else API_HOST
_LOCAL_MEDIA_PROXY_BASE = f"http://{_API_PUBLIC_HOST}:{API_PORT}/api/flow/local-media"
_IMAGE_EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/avif": "avif",
}
_VIDEO_EXT_BY_MIME = {
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
    "video/x-matroska": "mkv",
}


def _build_local_media_proxy_url(path: Path) -> str:
    encoded = quote(str(path), safe="")
    return f"{_LOCAL_MEDIA_PROXY_BASE}?path={encoded}"


def _is_persistable_local_url(url: str | None) -> bool:
    if not isinstance(url, str):
        return False
    text = url.strip()
    if not text:
        return False
    if text.startswith("http://") or text.startswith("https://"):
        try:
            parsed = urlparse(text)
            if (parsed.hostname or "").lower() not in {"127.0.0.1", "localhost"}:
                return False
            return parsed.path.rstrip("/") == "/api/flow/local-media"
        except Exception:
            return False
    if text.startswith("file://"):
        return True
    return Path(text).is_absolute()


def _guess_media_ext(url: str, content_type: str | None, kind: str) -> str:
    if content_type:
        mime = content_type.split(";", 1)[0].strip().lower()
        if kind == "video" and mime in _VIDEO_EXT_BY_MIME:
            return _VIDEO_EXT_BY_MIME[mime]
        if kind == "image" and mime in _IMAGE_EXT_BY_MIME:
            return _IMAGE_EXT_BY_MIME[mime]
    try:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix.lower().lstrip(".")
        if kind == "video" and suffix in {"mp4", "webm", "mov", "mkv"}:
            return suffix
        if kind == "image" and suffix in {"jpg", "jpeg", "png", "webp", "gif", "bmp", "avif"}:
            return "jpg" if suffix == "jpeg" else suffix
    except Exception:
        pass
    return "mp4" if kind == "video" else "png"


async def _download_media(url: str, target_base_path: Path, kind: str = "image") -> Path | None:
    target_base_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=420 if kind == "video" else 180)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                ext = _guess_media_ext(url, resp.headers.get("content-type"), kind)
                target_path = target_base_path.with_suffix(f".{ext}")
                target_path.write_bytes(await resp.read())
                return target_path
    except Exception as exc:
        logger.warning("Failed downloading local %s copy from %s: %s", kind, url, exc)
        return None


async def _resolve_scene_local_image_url(scene_id: str, orientation: str, remote_url: str | None) -> str | None:
    if not _is_direct_media_url(remote_url):
        return None
    scene = await crud.get_scene(scene_id)
    if not scene:
        return None
    video = await crud.get_video(scene.get("video_id")) if scene.get("video_id") else None
    project = await crud.get_project(video.get("project_id")) if video and video.get("project_id") else None

    project_seed = (
        (project or {}).get("name")
        or (video or {}).get("project_id")
        or scene.get("video_id")
        or "project"
    )
    project_slug = slugify(str(project_seed)) or "project"
    axis = "vertical" if orientation == "VERTICAL" else "horizontal"
    display_order = int(scene.get("display_order") or 0) + 1
    canonical_name = scene_filename(display_order, scene_id, ext="png")
    local_path = OUTPUT_DIR / project_slug / "images" / axis / canonical_name

    downloaded = await _download_media(remote_url, local_path, "image")
    if not downloaded:
        return None
    return _build_local_media_proxy_url(downloaded)


async def _resolve_scene_local_video_url(
    scene_id: str,
    orientation: str,
    remote_url: str | None,
    *,
    kind: str = "video",
) -> str | None:
    if not _is_direct_media_url(remote_url):
        return None
    scene = await crud.get_scene(scene_id)
    if not scene:
        return None
    video = await crud.get_video(scene.get("video_id")) if scene.get("video_id") else None
    project = await crud.get_project(video.get("project_id")) if video and video.get("project_id") else None

    project_seed = (
        (project or {}).get("name")
        or (video or {}).get("project_id")
        or scene.get("video_id")
        or "project"
    )
    project_slug = slugify(str(project_seed)) or "project"
    axis = "vertical" if orientation == "VERTICAL" else "horizontal"
    display_order = int(scene.get("display_order") or 0) + 1
    canonical_name = scene_filename(display_order, scene_id, ext="mp4")
    subdir = "videos" if kind == "video" else "upscale"
    local_path = OUTPUT_DIR / project_slug / subdir / axis / canonical_name

    downloaded = await _download_media(remote_url, local_path, "video")
    if not downloaded:
        return None
    return _build_local_media_proxy_url(downloaded)


async def _resolve_character_local_image_url(character_id: str, remote_url: str | None) -> str | None:
    if not _is_direct_media_url(remote_url):
        return None
    char = await crud.get_character(character_id)
    slug = slugify(str((char or {}).get("name") or "character")) or "character"
    local_path = OUTPUT_DIR / "_shared" / "refs" / f"{slug}_{character_id}.png"
    downloaded = await _download_media(remote_url, local_path, "image")
    if not downloaded:
        return None
    return _build_local_media_proxy_url(downloaded)


def _extract_first_direct_url(payload: object) -> str | None:
    candidates: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri"):
                value = node.get(key)
                if isinstance(value, str):
                    candidates.append(value)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    for url in candidates:
        if _is_direct_media_url(url):
            return url
    return None


async def _fallback_local_cache_via_media_id(
    media_id: str | None,
    remote_url_hint: str | None,
    *,
    project_id: str | None = None,
) -> str | None:
    if not media_id:
        return None
    try:
        from agent.services.flow_client import get_flow_client

        client = get_flow_client()
        normalized_project_id = str(project_id or "").strip().lower() or None

        if _is_direct_media_url(remote_url_hint):
            cached = await client.cache_media_locally(
                media_id,
                remote_url_hint,
                project_id=normalized_project_id,
            )
            if cached:
                return cached

        if not client.connected:
            return None

        media_resp = await client.get_media(
            media_id,
            project_id=normalized_project_id,
            timeout_sec=18,
        )
        if media_resp.get("error"):
            return None
        status = media_resp.get("status", 200)
        if isinstance(status, int) and status >= 400:
            return None

        payload = media_resp.get("data", media_resp)
        fresh_url = _extract_first_direct_url(payload)
        if not _is_direct_media_url(fresh_url):
            return None
        cached = await client.cache_media_locally(
            media_id,
            fresh_url,
            project_id=normalized_project_id,
        )
        return cached or fresh_url
    except Exception as exc:
        logger.debug("Fallback local cache failed for media %s: %s", str(media_id)[:12], exc)
        return None


def parse_result(raw: dict, req_type: str) -> GenerationResult:
    """Parse a raw FlowClient/OperationService response into a GenerationResult."""
    from agent.sdk.models.media import GenerationResult

    if _is_error(raw):
        error_msg = raw.get("error")
        if not error_msg:
            data = raw.get("data", {})
            if isinstance(data, dict):
                ef = data.get("error", "Unknown error")
                error_msg = ef.get("message", str(ef)[:200]) if isinstance(ef, dict) else str(ef)
            else:
                error_msg = "Unknown error"
        return GenerationResult(success=False, error=str(error_msg), raw=raw)

    media_id = _extract_media_id(raw, req_type)
    url = _extract_output_url(raw, req_type)
    return GenerationResult(success=True, media_id=media_id, url=url, raw=raw)


async def apply_scene_result(
    scene_id: str | None,
    req_type: str,
    orientation: str,
    result: GenerationResult,
) -> None:
    """Update scene DB fields after a successful generation.

    Handles cascade: image regen clears video+upscale, video regen clears upscale.
    This is the shared version of processor.py's _update_scene_from_result.
    """
    if not scene_id or not result.success:
        return

    p = "vertical" if orientation == "VERTICAL" else "horizontal"
    direct_url = result.url if _is_direct_media_url(result.url) else None
    persisted_url = result.url if _is_persistable_local_url(result.url) else direct_url
    updates = {}
    scene_cache: dict | None = None
    project_id_cache: str | None = None

    async def _scene_project_id() -> str | None:
        nonlocal scene_cache, project_id_cache
        if project_id_cache is not None:
            return project_id_cache or None
        scene_cache = scene_cache or await crud.get_scene(scene_id)
        video = await crud.get_video(scene_cache.get("video_id")) if scene_cache and scene_cache.get("video_id") else None
        project_id_cache = str((video or {}).get("project_id") or "").strip()
        return project_id_cache or None

    if req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE"):
        local_proxy_url = await _resolve_scene_local_image_url(scene_id, orientation, direct_url)
        if (not local_proxy_url) and result.media_id:
            local_proxy_url = await _fallback_local_cache_via_media_id(
                result.media_id,
                direct_url,
                project_id=await _scene_project_id(),
            )
        if local_proxy_url:
            persisted_url = local_proxy_url
        updates.update({
            f"{p}_image_media_id": result.media_id,
            f"{p}_image_url": persisted_url,
            f"{p}_image_status": "COMPLETED",
            # Cascade: clear downstream
            f"{p}_video_media_id": None, f"{p}_video_url": None, f"{p}_video_status": "PENDING",
            f"{p}_upscale_media_id": None, f"{p}_upscale_url": None, f"{p}_upscale_status": "PENDING",
        })
        # Chain cascade: update parent's end_scene_media_id so its video
        # transitions to this child's new image
        scene = scene_cache or await crud.get_scene(scene_id)
        if scene and scene.get("parent_scene_id") and result.media_id:
            await crud.update_scene(
                scene["parent_scene_id"],
                **{f"{p}_end_scene_media_id": result.media_id},
            )
    elif req_type in ("GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
        local_proxy_url = await _resolve_scene_local_video_url(scene_id, orientation, direct_url, kind="video")
        if (not local_proxy_url) and result.media_id:
            local_proxy_url = await _fallback_local_cache_via_media_id(
                result.media_id,
                direct_url,
                project_id=await _scene_project_id(),
            )
        if local_proxy_url:
            persisted_url = local_proxy_url
        updates.update({
            f"{p}_video_media_id": result.media_id,
            f"{p}_video_url": persisted_url,
            f"{p}_video_status": "COMPLETED",
            # Cascade: clear upscale
            f"{p}_upscale_media_id": None, f"{p}_upscale_url": None, f"{p}_upscale_status": "PENDING",
        })
    elif req_type in ("UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL"):
        local_proxy_url = await _resolve_scene_local_video_url(scene_id, orientation, direct_url, kind="upscale")
        if (not local_proxy_url) and result.media_id:
            local_proxy_url = await _fallback_local_cache_via_media_id(
                result.media_id,
                direct_url,
                project_id=await _scene_project_id(),
            )
        if local_proxy_url:
            persisted_url = local_proxy_url
        updates.update({
            f"{p}_upscale_media_id": result.media_id,
            f"{p}_upscale_url": persisted_url,
            f"{p}_upscale_status": "COMPLETED",
        })

    if updates:
        await crud.update_scene(scene_id, **updates)


async def apply_character_result(
    character_id: str,
    result: GenerationResult,
) -> None:
    """Update character DB fields after a successful reference image generation."""
    if not result.success:
        return
    updates = {}
    if result.media_id:
        updates["media_id"] = result.media_id
    direct_url = result.url if _is_direct_media_url(result.url) else None
    local_ref: str | None = None
    if direct_url:
        local_ref = await _resolve_character_local_image_url(character_id, direct_url)
    if (not local_ref) and result.media_id:
        local_ref = await _fallback_local_cache_via_media_id(
            result.media_id,
            direct_url,
            project_id=None,
        )
    if local_ref or direct_url:
        updates["reference_image_url"] = local_ref or direct_url
    if updates:
        await crud.update_character(character_id, **updates)
