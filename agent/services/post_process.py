"""Post-processing: trim, merge, add music via ffmpeg."""
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FLOAT_MIN = 0.0
_FLOAT_MAX = 2.0


def _clamp_float(value: float, name: str, lo: float = _FLOAT_MIN, hi: float = _FLOAT_MAX) -> float:
    """Clamp float to [lo, hi] and warn if out of bounds."""
    if value < lo or value > hi:
        logger.warning("Parameter %s=%s out of bounds [%s, %s], clamping", name, value, lo, hi)
        return max(lo, min(hi, value))
    return value


def trim_video(input_path: str, output_path: str, start: float, end: float) -> bool:
    """Trim video to [start, end] seconds."""
    if not Path(input_path).exists():
        logger.error("trim_video: input file not found: %s", input_path)
        return False
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
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error("Trim failed: %s", result.stderr[-200:])
        return False
    return True


def merge_videos(video_paths: list[str], output_path: str) -> bool:
    """Concatenate videos using ffmpeg concat demuxer."""
    concat_file = output_path + ".concat.txt"
    try:
        with open(concat_file, "w") as f:
            for p in video_paths:
                # Escape single quotes to prevent path injection in concat file
                escaped = str(p).replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "copy", "-c:a", "copy",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    finally:
        Path(concat_file).unlink(missing_ok=True)
    if result.returncode != 0:
        logger.error("Merge failed: %s", result.stderr[-200:])
        return False
    return True


def add_narration(video_path: str, narration_path: str, output_path: str,
                  narration_volume: float = 1.0, sfx_volume: float = 0.4,
                  fade_in: float = 0.5, fade_out: float = 0.5,
                  replace_original: bool = False) -> bool:
    """Add narration audio on video.

    replace_original=False: mix narration with original SFX track.
    replace_original=True: replace original audio track with narration.
    """
    if not Path(video_path).exists():
        logger.error("add_narration: video file not found: %s", video_path)
        return False
    if not Path(narration_path).exists():
        logger.error("add_narration: narration file not found: %s", narration_path)
        return False

    # Clamp float params to prevent filter injection
    narration_volume = _clamp_float(narration_volume, "narration_volume")
    sfx_volume = _clamp_float(sfx_volume, "sfx_volume")
    fade_in = _clamp_float(fade_in, "fade_in")
    fade_out = _clamp_float(fade_out, "fade_out")

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path],
        capture_output=True, text=True, timeout=30,
    )
    try:
        duration = float(probe.stdout.strip())
    except (ValueError, AttributeError):
        logger.error("ffprobe failed for %s: %s", video_path, probe.stderr[-200:] if probe.stderr else "no output")
        return False
    fade_start = max(0, duration - fade_out)

    if replace_original:
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", narration_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-filter_complex",
            f"[1:a]volume={narration_volume},afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_start}:d={fade_out},apad[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", narration_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-filter_complex",
            f"[0:a]volume={sfx_volume}[sfx];[1:a]volume={narration_volume},afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_start}:d={fade_out}[narr];[sfx][narr]amerge=inputs=2,pan=stereo|c0=c0+c2|c1=c1+c3[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error("Add narration failed: %s", result.stderr[-200:])
        return False
    return True


def add_music(video_path: str, music_path: str, output_path: str,
              music_volume: float = 0.3, fade_in: float = 2.0, fade_out: float = 3.0) -> bool:
    """Overlay background music on video."""
    if not Path(video_path).exists():
        logger.error("add_music: video file not found: %s", video_path)
        return False
    if not Path(music_path).exists():
        logger.error("add_music: music file not found: %s", music_path)
        return False

    # Clamp float params to prevent filter injection
    music_volume = _clamp_float(music_volume, "music_volume")
    fade_in = _clamp_float(fade_in, "fade_in")
    fade_out = _clamp_float(fade_out, "fade_out")

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path],
        capture_output=True, text=True, timeout=30,
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
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error("Add music failed: %s", result.stderr[-200:])
        return False
    return True
