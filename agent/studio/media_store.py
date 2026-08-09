"""Local media cache for Flow Studio.

Resolves a Flow media id → signed URL (via the extension) and downloads the bytes
to ./media so the web app can display from local files instead of hitting Flow on
every render. Includes the URL-fetch throttle from video-app.md §5.2 (rest after a
burst of lookups) since /media/{id} is itself rate-limited.
"""
import asyncio
import logging
import os
import random
from pathlib import Path

import httpx

from agent.config import BASE_DIR
from agent.services.flow_client import get_flow_client

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(os.environ.get("STUDIO_MEDIA_DIR", BASE_DIR / "media"))
THUMB_DIR = MEDIA_DIR / "_thumbs"

# URL-fetch throttle: Flow's /media/{id} is rate-limited, so resolving signed URLs is
# (a) capped at a few concurrent calls — a gallery firing dozens of <img> at once must
# not translate into dozens of simultaneous Flow hits — and (b) rested after each burst.
_URL_BURST = 6
_URL_CONCURRENCY = 3
_url_lock = asyncio.Lock()
_url_sem = asyncio.Semaphore(_URL_CONCURRENCY)
_url_count = 0


async def _throttle_url_fetch() -> None:
    global _url_count
    async with _url_lock:
        _url_count += 1
        if _url_count % _URL_BURST == 0:
            await asyncio.sleep(random.uniform(2, 6))


async def resolve_url(media_id: str) -> str | None:
    """media_id → fresh signed URL (None if invalid/not ready). Concurrency-limited +
    throttled to avoid tripping Flow's media rate limit on bursty galleries."""
    client = get_flow_client()
    if not client.connected:
        return None
    async with _url_sem:
        await _throttle_url_fetch()
        result = await client.get_direct_media(media_id)
    data = result.get("data", result) if isinstance(result, dict) else {}
    if isinstance(data, dict) and data.get("redirected"):
        return data.get("url")
    return None


async def _download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
            resp = await c.get(url)
        if resp.status_code >= 400:
            logger.warning("media download %s → %s", url[:60], resp.status_code)
            return False
        dest.write_bytes(resp.content)
        return True
    except httpx.RequestError as e:
        logger.warning("media download failed: %s", e)
        return False


async def ensure_local(media_id: str, project_id: str, ext: str = "png",
                       *, attempts: int = 1) -> str | None:
    """Ensure ./media/<project_id>/<media_id>.<ext> exists; return web path or None.

    `attempts` > 1 retries the resolve+download with backoff — a FRESHLY generated media
    (esp. in a concurrent batch) is often not immediately resolvable / trips Flow's media
    rate limit, and a one-shot resolve then returns None. Retrying here saves the download
    instead of leaving image_path NULL (which used to make the caller REGENERATE the image —
    burning a render slot and spawning duplicate Flow media)."""
    rel = Path(project_id) / f"{media_id}.{ext}"
    dest = MEDIA_DIR / rel
    if dest.exists() and dest.stat().st_size > 0:
        return f"/media/{rel.as_posix()}"
    for attempt in range(max(1, attempts)):
        url = await resolve_url(media_id)
        if url and await _download(url, dest):
            return f"/media/{rel.as_posix()}"
        if attempt < attempts - 1:
            await asyncio.sleep(random.uniform(2, 5) * (attempt + 1))   # let Flow settle
    return None


async def save_from_url(media_id: str, project_id: str, ext: str, url: str) -> str | None:
    """Download a known URL (e.g. video fifeUrl from poll) to the local cache."""
    rel = Path(project_id) / f"{media_id}.{ext}"
    dest = MEDIA_DIR / rel
    if dest.exists() and dest.stat().st_size > 0:
        return f"/media/{rel.as_posix()}"
    if await _download(url, dest):
        return f"/media/{rel.as_posix()}"
    return None


_URL_KEYS = ("fifeUrl", "servingBaseUri", "servingUri", "servingUrl",
             "directUrl", "downloadUrl", "url", "uri")


def direct_url_in(obj) -> str | None:
    """First directly-downloadable http(s) URL inside a generated-media item. An image-gen
    response already carries the result's URL, so we can download it straight away instead of
    a separate, rate-limited get_direct_media resolve. Search a SINGLE generated-media item
    only (not the whole payload) so we never pick up a reference/input image's URL."""
    if isinstance(obj, dict):
        for k in _URL_KEYS:
            v = obj.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
        for v in obj.values():
            hit = direct_url_in(v)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = direct_url_in(v)
            if hit:
                return hit
    return None


async def save_media(media_id: str, project_id: str, ext: str,
                     url: str | None = None, *, attempts: int = 6) -> str | None:
    """Cache a freshly generated media. PREFER the direct `url` from the gen response (no
    rate-limited resolve) — fall back to get_direct_media (with retries) only if there is no
    url or that download failed. This is what stops a concurrent batch from tripping Flow's
    media rate limit on every frame (which used to leave image_path NULL → regenerate)."""
    if not media_id:
        return None
    if url:
        web = await save_from_url(media_id, project_id, ext, url)
        if web:
            return web
    return await ensure_local(media_id, project_id, ext, attempts=attempts)


def sniff_ext(data: bytes, default: str = "png") -> str:
    """Image extension from magic bytes — the upsample response ships raw base64 with no
    mime type, and writing a JPEG as .png confuses ffmpeg/Resolve on import."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return default


def save_bytes(name: str, project_id: str, data: bytes) -> str:
    """Write raw image bytes to ./media/<project_id>/<name>.<sniffed ext>; return web path.
    Used for media Flow hands back inline (base64) instead of behind a signed URL."""
    rel = Path(project_id) / f"{name}.{sniff_ext(data)}"
    dest = MEDIA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return f"/media/{rel.as_posix()}"


_LOCAL_EXTS = ("png", "jpg", "jpeg", "webp")


def find_local(media_key: str, project_id: str | None = None) -> Path | None:
    """An already-downloaded copy of this media on disk, if any — checked before any
    online resolve so a gallery serves from the per-project cache instead of hitting
    Flow's rate-limited /media/{id}. Looks in <project_id>/ first, then any project."""
    if project_id:
        for ext in _LOCAL_EXTS:
            p = MEDIA_DIR / project_id / f"{media_key}.{ext}"
            if p.exists() and p.stat().st_size > 0:
                return p
    for ext in _LOCAL_EXTS:
        for p in MEDIA_DIR.glob(f"*/{media_key}.{ext}"):
            if p.is_file() and p.stat().st_size > 0:
                return p
    return None


async def ensure_thumb(media_key: str, project_id: str | None = None) -> Path | None:
    """Ensure a cached thumbnail for a Flow media key; return local file path.

    Prefers any existing local copy (per-project cache) over an online resolve, so the
    gallery only hits Flow for images that were never downloaded."""
    dest = THUMB_DIR / f"{media_key}.png"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    local = find_local(media_key, project_id)
    if local:
        return local
    url = await resolve_url(media_key)
    if not url:
        return None
    if await _download(url, dest):
        return dest
    return None
