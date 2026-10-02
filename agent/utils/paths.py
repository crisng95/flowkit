"""Centralized path resolver for project output directories and scene files."""
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from agent.config import OUTPUT_DIR


def file_url_to_path(url: str | None) -> "Path | None":
    """Turn a ``file://`` URL into a local ``Path``; ``None`` for anything else.

    Accepts both the RFC 8089 form ``Path.as_uri()`` produces
    (``file:///C:/x/y.png``, percent-encoded) and the naive
    ``"file://" + str(path)`` form the pipeline stores. The latter is fine on
    POSIX (``file:///tmp/y.png``) but on Windows ``urlparse`` files
    ``C:\\x\\y.png`` under *netloc* with an empty *path*, so reading only
    ``parsed.path`` made every local clip look missing.
    """
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    raw = (parsed.netloc or "") + parsed.path
    return Path(url2pathname(raw))


def project_dir(project_slug: str) -> Path:
    """Return the output directory for a given project slug."""
    return OUTPUT_DIR / project_slug


def scene_filename(display_order: int, scene_id: str, ext: str = "mp4") -> str:
    """Return canonical scene filename: scene_NNN_<scene_id>.<ext>."""
    return f"scene_{display_order:03d}_{scene_id}.{ext}"


def scene_4k_path(project_slug: str, display_order: int, scene_id: str) -> Path:
    """Return path to the 4K scene video file."""
    return project_dir(project_slug) / "4k" / scene_filename(display_order, scene_id)


def scene_tts_path(project_slug: str, display_order: int, scene_id: str) -> Path:
    """Return path to the TTS narration WAV for a scene."""
    return project_dir(project_slug) / "tts" / scene_filename(display_order, scene_id, ext="wav")


def scene_video_path(
    project_slug: str, display_order: int, scene_id: str, subdir: str = "scenes"
) -> Path:
    """Return path to a scene video file under an arbitrary subdir."""
    return project_dir(project_slug) / subdir / scene_filename(display_order, scene_id)


def resolve_4k_file(project_slug: str, display_order: int, scene_id: str) -> "Path | None":
    """Locate the 4K file for a scene.

    Checks canonical name (scene_NNN_<id>.mp4) first, then falls back to
    the legacy <scene_id>.mp4 name. Returns None if neither exists.
    """
    canonical = scene_4k_path(project_slug, display_order, scene_id)
    if canonical.exists():
        return canonical
    legacy = project_dir(project_slug) / "4k" / f"{scene_id}.mp4"
    if legacy.exists():
        return legacy
    return None
