"""Media helpers for master assembly."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess


def concat_lines(paths: list[Path]) -> list[str]:
    return [f"file '{path}'" for path in paths]


def write_concat_file(paths: list[Path], concat_path: Path) -> None:
    concat_path.write_text("\n".join(concat_lines(paths)) + "\n", encoding="utf-8")


def concat_videos(paths: list[Path], output_path: Path) -> None:
    concat_path = output_path.parent / "master.concat.txt"
    write_concat_file(paths, concat_path)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            check=True,
        )
    finally:
        concat_path.unlink(missing_ok=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def probe_dimensions(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    return int(video["width"]), int(video["height"])


def build_master_manifest(project: dict, chapter_artifacts: list[dict], final_uri: str, final_duration_seconds: float) -> dict:
    return {
        "project_id": project["id"],
        "project_slug": project["project_slug"],
        "source_title": project["source_title"],
        "target_duration_seconds": project["target_duration_seconds"],
        "master_output_uri": final_uri,
        "master_duration_seconds": final_duration_seconds,
        "chapters": [
            {
                "chapter_id": artifact["chapter_id"],
                "chapter_index": artifact["chapter_index"],
                "storage_uri": artifact["storage_uri"],
            }
            for artifact in chapter_artifacts
        ],
    }
