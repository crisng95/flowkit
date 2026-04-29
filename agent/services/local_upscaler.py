"""Local 4K video upscaler using Real-ESRGAN + ffmpeg."""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from agent.config import API_HOST, API_PORT, BASE_DIR, OUTPUT_DIR
from agent.db import crud
from agent.services.flow_client import get_flow_client
from agent.utils.paths import scene_4k_path
from agent.utils.slugify import slugify

logger = logging.getLogger(__name__)

LOCAL_UPSCALE_SETUP_MARKER = "LOCAL_UPSCALE_SETUP_REQUIRED"
DEFAULT_LOCAL_UPSCALE_MODEL = os.environ.get("LOCAL_UPSCALE_MODEL", "realesrgan-x4plus").strip() or "realesrgan-x4plus"
DEFAULT_LOCAL_UPSCALE_SCALE = max(2, min(4, int(os.environ.get("LOCAL_UPSCALE_SCALE", "4"))))
DEFAULT_LOCAL_UPSCALE_TIMEOUT_SEC = int(os.environ.get("LOCAL_UPSCALE_TIMEOUT_SEC", "1800"))
DEFAULT_LOCAL_UPSCALE_PRESET = os.environ.get("LOCAL_UPSCALE_PRESET", "slow").strip() or "slow"

_API_PUBLIC_HOST = "127.0.0.1" if API_HOST in {"0.0.0.0", "::"} else API_HOST
_LOCAL_MEDIA_PROXY_BASE = f"http://{_API_PUBLIC_HOST}:{API_PORT}/api/flow/local-media"


@dataclass(frozen=True)
class LocalUpscaleTools:
    ffmpeg: str
    ffprobe: str
    realesrgan: str
    model_dir: Path
    model_name: str
    scale: int


def _extract_local_media_path(url: str | None) -> Path | None:
    if not isinstance(url, str):
        return None
    text = url.strip()
    if not text:
        return None

    if text.startswith("http://") or text.startswith("https://"):
        try:
            parsed = urlparse(text)
            if (parsed.hostname or "").lower() not in {"127.0.0.1", "localhost"}:
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


def _build_local_media_proxy_url(path: Path) -> str:
    return f"{_LOCAL_MEDIA_PROXY_BASE}?path={quote(str(path), safe='')}"


def _is_direct_media_url(url: str | None) -> bool:
    if not isinstance(url, str):
        return False
    text = url.strip().lower()
    if not text.startswith("http"):
        return False
    if "media.getmediaurlredirect" in text:
        return False
    if text.startswith("https://flow-content.google/"):
        return True
    if text.startswith("https://storage.googleapis.com/"):
        return True
    if "googleusercontent.com/" in text:
        return True
    return False


def _extract_first_direct_url(payload: Any) -> str | None:
    candidates: list[str] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("fifeUrl", "servingUri", "url", "imageUri", "videoUri"):
                val = node.get(key)
                if isinstance(val, str):
                    candidates.append(val)
            for val in node.values():
                _walk(val)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    for url in candidates:
        if _is_direct_media_url(url):
            return url
    return None


def _resolve_binary(env_var: str, candidates: list[str]) -> str | None:
    raw = (os.environ.get(env_var) or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if p.exists():
            return str(p.resolve())
        found = shutil.which(raw)
        if found:
            return found
    for cand in candidates:
        p = Path(cand).expanduser()
        if p.exists():
            return str(p.resolve())
        found = shutil.which(cand)
        if found:
            return found
    return None


def _runtime_platform() -> str:
    if os.name == "nt":
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    return sys.platform


def _runtime_root_candidates() -> list[Path]:
    roots: list[Path] = []
    env_root = (os.environ.get("LOCAL_UPSCALE_RUNTIME_ROOT") or "").strip()
    if env_root:
        roots.append(Path(env_root).expanduser())

    base = BASE_DIR / "third_party"
    roots.append(base / _runtime_platform())
    roots.append(base)

    dedup: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(root)
    return dedup


def _resolve_tools() -> LocalUpscaleTools:
    runtime_roots = _runtime_root_candidates()
    ffmpeg = _resolve_binary("LOCAL_UPSCALE_FFMPEG", ["ffmpeg"])
    ffprobe = _resolve_binary("LOCAL_UPSCALE_FFPROBE", ["ffprobe"])

    realesrgan_candidates = ["realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe"]
    for root in runtime_roots:
        realesrgan_candidates.extend(
            [
                str(root / "realesrgan" / "realesrgan-ncnn-vulkan"),
                str(root / "realesrgan" / "realesrgan-ncnn-vulkan.exe"),
            ]
        )

    realesrgan = _resolve_binary(
        "LOCAL_UPSCALE_BIN",
        realesrgan_candidates,
    )

    model_dir_env = (os.environ.get("LOCAL_UPSCALE_MODEL_DIR") or "").strip()
    if model_dir_env:
        model_dir = Path(model_dir_env).expanduser()
    else:
        default_model_dirs = [root / "realesrgan" / "models" for root in runtime_roots]
        default_model_dirs.append(BASE_DIR / "third_party" / "realesrgan" / "models")
        model_dir = next((path for path in default_model_dirs if path.exists()), default_model_dirs[0])

    model_name = DEFAULT_LOCAL_UPSCALE_MODEL
    scale = DEFAULT_LOCAL_UPSCALE_SCALE

    missing: list[str] = []
    if not ffmpeg:
        missing.append("ffmpeg")
    if not ffprobe:
        missing.append("ffprobe")
    if not realesrgan:
        missing.append("realesrgan-ncnn-vulkan")
    if not model_dir.exists():
        missing.append(f"model_dir:{model_dir}")
    else:
        model_file_candidates = [model_dir / f"{model_name}.param", model_dir / f"{model_name}.bin"]
        if not all(p.exists() for p in model_file_candidates):
            missing.append(f"model:{model_name} in {model_dir}")

    if missing:
        raise RuntimeError(
            f"{LOCAL_UPSCALE_SETUP_MARKER}: thiếu {'; '.join(missing)}. "
            "Thiết lập LOCAL_UPSCALE_BIN + LOCAL_UPSCALE_MODEL_DIR hoặc cài Real-ESRGAN ncnn."
        )

    return LocalUpscaleTools(
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        realesrgan=realesrgan,
        model_dir=model_dir,
        model_name=model_name,
        scale=scale,
    )


async def _run_cmd(cmd: list[str], *, timeout_sec: int, cwd: Path | None = None) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, f"timeout after {timeout_sec}s: {' '.join(cmd[:4])}..."
    if proc.returncode != 0:
        out_tail = (stdout or b"")[-240:].decode("utf-8", errors="ignore")
        err_tail = (stderr or b"")[-480:].decode("utf-8", errors="ignore")
        return False, (err_tail or out_tail or f"exit {proc.returncode}").strip()
    return True, ""


async def _probe_avg_fps(ffprobe_bin: str, source: str) -> str:
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        source,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            err = (stderr or b"").decode("utf-8", errors="ignore").strip()
            logger.warning("ffprobe fps failed: %s", err[-240:] if err else f"exit {proc.returncode}")
            return "30"
        fps = (stdout or b"").decode("utf-8", errors="ignore").strip()
        return fps or "30"
    except Exception:
        return "30"


async def _resolve_source_video(scene: dict, orientation: str, project_id: str | None) -> str | None:
    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    video_url = scene.get(f"{prefix}_video_url")
    media_id = scene.get(f"{prefix}_video_media_id")

    local_path = _extract_local_media_path(video_url)
    if local_path and local_path.exists() and local_path.is_file():
        return str(local_path)

    client = get_flow_client()
    normalized_pid = str(project_id or "").strip().lower() or None

    if isinstance(media_id, str) and media_id:
        local_url = await client.find_local_media_url(media_id, project_id=normalized_pid)
        local_path = _extract_local_media_path(local_url)
        if local_path and local_path.exists() and local_path.is_file():
            return str(local_path)

    if isinstance(media_id, str) and media_id and _is_direct_media_url(video_url):
        local_url = await client.cache_media_locally(media_id, video_url, project_id=normalized_pid)
        local_path = _extract_local_media_path(local_url)
        if local_path and local_path.exists() and local_path.is_file():
            return str(local_path)

    if isinstance(media_id, str) and media_id and client.connected:
        media_resp = await client.get_media(media_id, project_id=normalized_pid, timeout_sec=20)
        if not media_resp.get("error"):
            payload = media_resp.get("data", media_resp)
            fresh_url = _extract_first_direct_url(payload)
            if _is_direct_media_url(fresh_url):
                local_url = await client.cache_media_locally(media_id, fresh_url, project_id=normalized_pid)
                local_path = _extract_local_media_path(local_url)
                if local_path and local_path.exists() and local_path.is_file():
                    return str(local_path)
                return fresh_url

    if _is_direct_media_url(video_url):
        return video_url
    return None


async def upscale_scene_video_local(
    scene: dict,
    orientation: str,
    *,
    project_id: str | None = None,
) -> dict:
    """Upscale a scene video to 4K locally and return a Flow-like operation payload."""
    try:
        tools = _resolve_tools()
    except Exception as exc:
        return {"error": str(exc)}

    scene_id = str(scene.get("id") or "")
    if not scene_id:
        return {"error": "Missing scene id for local upscale"}

    source = await _resolve_source_video(scene, orientation, project_id)
    if not source:
        return {"error": "No source video available for local upscale"}

    video = await crud.get_video(scene.get("video_id")) if scene.get("video_id") else None
    project = await crud.get_project((video or {}).get("project_id")) if video and video.get("project_id") else None
    project_seed = (
        (project or {}).get("name")
        or (video or {}).get("project_id")
        or scene.get("video_id")
        or "project"
    )
    project_slug = slugify(str(project_seed)) or "project"
    display_order = int(scene.get("display_order") or 0) + 1
    output_path = scene_4k_path(project_slug, display_order, scene_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    target_w, target_h = (2160, 3840) if orientation == "VERTICAL" else (3840, 2160)
    fps = await _probe_avg_fps(tools.ffprobe, source)

    tmp_root = OUTPUT_DIR / "_tmp" / "local_upscale"
    tmp_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"{scene_id[:10]}_", dir=str(tmp_root)) as td:
        workdir = Path(td)
        frames_in = workdir / "frames_in"
        frames_up = workdir / "frames_up"
        frames_in.mkdir(parents=True, exist_ok=True)
        frames_up.mkdir(parents=True, exist_ok=True)

        extract_cmd = [
            tools.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            source,
            "-vsync",
            "0",
            str(frames_in / "frame_%08d.png"),
        ]
        ok, msg = await _run_cmd(extract_cmd, timeout_sec=900)
        if not ok:
            return {"error": f"Local upscale extract failed: {msg}"}

        upscale_cmd = [
            tools.realesrgan,
            "-i",
            str(frames_in),
            "-o",
            str(frames_up),
            "-n",
            tools.model_name,
            "-s",
            str(tools.scale),
            "-f",
            "png",
            "-m",
            str(tools.model_dir),
        ]
        ok, msg = await _run_cmd(upscale_cmd, timeout_sec=DEFAULT_LOCAL_UPSCALE_TIMEOUT_SEC)
        if not ok:
            return {"error": f"Local upscale Real-ESRGAN failed: {msg}"}

        encode_cmd = [
            tools.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            fps,
            "-i",
            str(frames_up / "frame_%08d.png"),
            "-i",
            source,
            "-map",
            "0:v:0",
            "-map",
            "1:a?",
            "-vf",
            (
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,"
                "unsharp=5:5:0.8:3:3:0.35"
            ),
            "-c:v",
            "libx264",
            "-preset",
            DEFAULT_LOCAL_UPSCALE_PRESET,
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]
        ok, msg = await _run_cmd(encode_cmd, timeout_sec=900)
        if not ok:
            return {"error": f"Local upscale encode failed: {msg}"}

    if not output_path.exists():
        return {"error": "Local upscale failed: output file missing"}

    local_url = _build_local_media_proxy_url(output_path)
    return {
        "data": {
            "operations": [
                {
                    "operation": {
                        "name": f"local-upscale-{scene_id[:8]}",
                        "metadata": {
                            "video": {
                                "fifeUrl": local_url,
                            }
                        },
                    },
                    "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                }
            ]
        }
    }


def local_upscale_health() -> dict:
    """Return availability of local 4K upscaler dependencies."""
    try:
        tools = _resolve_tools()
        return {
            "ready": True,
            "ffmpeg": tools.ffmpeg,
            "ffprobe": tools.ffprobe,
            "realesrgan": tools.realesrgan,
            "model_dir": str(tools.model_dir),
            "model_name": tools.model_name,
            "scale": tools.scale,
        }
    except Exception as exc:
        return {
            "ready": False,
            "error": str(exc),
        }
