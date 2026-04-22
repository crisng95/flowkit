"""Media helpers for concat stage."""

from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess


def canonical_clip_name(display_order: int, scene_id: str) -> str:
    return f"scene_{display_order:03d}_{scene_id}.mp4"


def prefer_scene_video_url(scene: dict, *, orientation: str, prefer_4k: bool) -> str | None:
    prefix = "vertical" if orientation.upper() == "VERTICAL" else "horizontal"
    upscale_key = f"{prefix}_upscale_url"
    video_key = f"{prefix}_video_url"
    if prefer_4k and scene.get(upscale_key):
        return scene[upscale_key]
    return scene.get(upscale_key) or scene.get(video_key)


def local_clip_path(output_dir: Path, display_order: int, scene_id: str) -> Path:
    return output_dir / "4k" / canonical_clip_name(display_order, scene_id)


def _media_docker_image() -> str | None:
    return os.environ.get("MEDIA_DOCKER_IMAGE") or None


def _media_docker_work_root() -> Path | None:
    value = os.environ.get("MEDIA_DOCKER_WORK_ROOT")
    return Path(value).resolve() if value else None


def _media_docker_mount_point() -> Path:
    return Path(os.environ.get("MEDIA_DOCKER_MOUNT_POINT", "/work"))


def _media_docker_user() -> str | None:
    uid = os.environ.get("FLOWKIT_UID")
    gid = os.environ.get("FLOWKIT_GID")
    if uid and gid:
        return f"{uid}:{gid}"
    return None


def _translate_media_path(path: Path) -> str:
    work_root = _media_docker_work_root()
    if not work_root:
        return str(path)
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(work_root)
    except ValueError:
        return str(path)
    return str((_media_docker_mount_point() / relative).as_posix())


def _media_tool_command(tool: str) -> list[str]:
    image = _media_docker_image()
    work_root = _media_docker_work_root()
    if image and work_root:
        command = [
            "docker",
            "run",
            "--rm",
        ]
        user = _media_docker_user()
        if user:
            command.extend(["--user", user])
        command.extend(
            [
                "-v",
                f"{str(work_root)}:{_media_docker_mount_point().as_posix()}",
                "--entrypoint",
                tool,
                image,
            ]
        )
        return command
    return [tool]


def probe_dimensions(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        _media_tool_command("ffprobe")
        + [
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            _translate_media_path(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    return int(video["width"]), int(video["height"])


def normalize_clip(source: Path, output: Path, width: int, height: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        _media_tool_command("ffmpeg")
        + [
            "-y",
            "-i",
            _translate_media_path(source),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-vf",
            f"scale={width}:{height}",
            "-r",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            _translate_media_path(output),
        ],
        check=True,
    )


def concat_clips(inputs: list[Path], output: Path) -> None:
    concat_file = output.parent / "concat.txt"
    concat_file.write_text("".join(f"file '{_translate_media_path(path)}'\n" for path in inputs), encoding="utf-8")
    try:
        subprocess.run(
            _media_tool_command("ffmpeg")
            + [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                _translate_media_path(concat_file),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                _translate_media_path(output),
            ],
            check=True,
        )
    finally:
        concat_file.unlink(missing_ok=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        _media_tool_command("ffprobe")
        + [
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            _translate_media_path(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())
