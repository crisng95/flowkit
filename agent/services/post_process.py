"""Post-processing: trim, merge, add music via ffmpeg."""
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def trim_video(input_path: str, output_path: str, start: float, end: float) -> bool:
    """Trim video to [start, end] seconds."""
    duration = end - start
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ss", str(start), "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-force_key_frames", "expr:gte(t,0)",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Trim failed: %s", result.stderr[-200:])
        return False
    return True


def merge_videos(video_paths: list[str], output_path: str) -> bool:
    """Concatenate videos using ffmpeg concat demuxer."""
    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for p in video_paths:
            f.write(f"file '{p}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "copy", "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    Path(concat_file).unlink(missing_ok=True)
    if result.returncode != 0:
        logger.error("Merge failed: %s", result.stderr[-200:])
        return False
    return True


def add_music(video_path: str, music_path: str, output_path: str,
              music_volume: float = 0.3, fade_in: float = 2.0, fade_out: float = 3.0) -> bool:
    """Overlay background music on video."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    try:
        duration = float(probe.stdout.strip())
    except (ValueError, AttributeError):
        logger.error("ffprobe failed for %s: %s", video_path, probe.stderr[-200:] if probe.stderr else "no output")
        return False
    fade_start = max(0, duration - fade_out)

    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", music_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-filter_complex",
        f"[0:a]volume=1.0[orig];[1:a]volume={music_volume},afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_start}:d={fade_out}[music];[orig][music]amerge=inputs=2,pan=stereo|c0=c0+c2|c1=c1+c3[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Add music failed: %s", result.stderr[-200:])
        return False
    return True
