"""YouTube upload service and video scheduling for Flow Kit."""
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

from googleapiclient.http import MediaFileUpload

from youtube.auth import get_authenticated_service, get_channel_dir

logger = logging.getLogger(__name__)

DEFAULT_RULES = {
    "upload_rules": {
        "shorts": {
            "max_per_day": 3,
            "optimal_times": ["07:00", "12:00", "17:00"],
            "min_gap_hours": 4,
            "avoid_hours": [0, 1, 2, 3, 4, 5],
        },
        "long": {
            "max_per_day": 1,
            "optimal_times": ["19:00"],
            "min_gap_hours": 4,
            "avoid_hours": [0, 1, 2, 3, 4, 5],
        },
    },
    "seo": {
        "title_max_chars": 65,
        "always_include_hashtags": ["#Shorts"],
        "default_tags": [],
        "default_category": "25",
    },
    "timezone": "Asia/Ho_Chi_Minh",
}


def _probe_video(video_path: str | Path) -> Tuple[float, int, int]:
    """Return (duration_seconds, width, height) using ffprobe or ffmpeg."""
    path_str = str(video_path)
    # Try ffprobe first
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration:format=duration",
            "-of", "json",
            path_str,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            stream = (data.get("streams") or [{}])[0]
            width = int(stream.get("width", 1080))
            height = int(stream.get("height", 1920))
            duration_str = stream.get("duration") or data.get("format", {}).get("duration", "0")
            return float(duration_str), width, height
    except Exception as e:
        logger.warning("ffprobe probe failed: %s, attempting fallback", e)

    # Fallback to ffmpeg -i info parsing
    try:
        ffmpeg_bin = "ffmpeg"
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass

        res = subprocess.run([ffmpeg_bin, "-i", path_str], capture_output=True, text=True, timeout=30)
        stderr = res.stderr or ""
        duration = 0.0
        width, height = 1080, 1920
        for line in stderr.splitlines():
            if "Duration:" in line:
                parts = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = parts.split(":")
                duration = float(h) * 3600 + float(m) * 60 + float(s)
            if "Video:" in line and ("x" in line or "," in line):
                import re
                match = re.search(r"(\d{3,5})x(\d{3,5})", line)
                if match:
                    width, height = int(match.group(1)), int(match.group(2))
        return duration, width, height
    except Exception as e:
        logger.error("Failed to probe video %s: %s", video_path, e)
        return 0.0, 1080, 1920


def detect_video_type(video_path: str | Path) -> Tuple[str, str]:
    """Detect if video is Short or Long-form.

    Returns:
        tuple[str, str]: ("short", "vertical") or ("long", "horizontal")
    """
    duration, width, height = _probe_video(video_path)
    is_vertical = height > width
    is_short = duration < 61.0 and is_vertical
    video_type = "short" if is_short else "long"
    orientation = "vertical" if is_vertical else "horizontal"
    return video_type, orientation


def load_channel_rules(channel_name: str) -> dict:
    """Load channel rules from youtube/channels/<channel_name>/channel_rules.json."""
    rules_file = get_channel_dir(channel_name) / "channel_rules.json"
    if rules_file.exists():
        try:
            return json.loads(rules_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Error reading %s: %s, using defaults", rules_file, e)
    return DEFAULT_RULES.copy()


def load_upload_history(channel_name: str) -> list[dict]:
    """Load history of uploads for a channel."""
    hist_file = get_channel_dir(channel_name) / "upload_history.json"
    if hist_file.exists():
        try:
            return json.loads(hist_file.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_upload_history_entry(channel_name: str, entry: dict):
    """Save an entry to upload_history.json."""
    cdir = get_channel_dir(channel_name)
    cdir.mkdir(parents=True, exist_ok=True)
    hist_file = cdir / "upload_history.json"
    history = load_upload_history(channel_name)
    history.append(entry)
    hist_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_dt(val: Any) -> datetime:
    """Normalize datetime to timezone-aware UTC datetime."""
    if not val:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        val_clean = str(val).replace("Z", "+00:00")
        dt = datetime.fromisoformat(val_clean)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.fromtimestamp(0, tz=timezone.utc)


def validate_upload(
    channel_name: str,
    schedule_at: str | datetime,
    is_short: bool = True,
) -> Tuple[bool, str]:
    """Validate scheduled upload against channel rules.

    Checks:
    1. Max uploads per day
    2. Min gap between uploads
    3. Avoid hours
    """
    rules = load_channel_rules(channel_name)
    upload_rules = rules.get("upload_rules") or DEFAULT_RULES["upload_rules"]
    type_key = "shorts" if is_short else "long"
    type_rules = upload_rules.get(type_key) or DEFAULT_RULES["upload_rules"][type_key]

    sched_dt = _parse_dt(schedule_at)
    target_date = sched_dt.date()

    history = load_upload_history(channel_name)

    # 1. Max per day
    max_per_day = type_rules.get("max_per_day", 3 if is_short else 1)
    day_count = sum(
        1 for h in history
        if h.get("is_short", True) == is_short
        and _parse_dt(h.get("schedule_at") or h.get("timestamp", "")).date() == target_date
    )
    if day_count >= max_per_day:
        return False, f"Max {max_per_day} {type_key}/day reached for {target_date}"

    # 2. Min gap hours
    min_gap = timedelta(hours=type_rules.get("min_gap_hours", 4))
    for h in history:
        prev_dt = _parse_dt(h.get("schedule_at") or h.get("timestamp", ""))
        if abs(sched_dt - prev_dt) < min_gap:
            return False, f"Min gap of {min_gap} not met relative to {prev_dt.isoformat()}"

    # 3. Avoid hours
    avoid = type_rules.get("avoid_hours", [0, 1, 2, 3, 4, 5])
    if sched_dt.hour in avoid:
        return False, f"Schedule hour {sched_dt.hour}:00 is in avoid_hours {avoid}"

    return True, "OK"


def auto_schedule(
    channel_name: str,
    count: int,
    is_short: bool = True,
    start_from: Optional[datetime] = None,
) -> list[str]:
    """Auto-generate N valid schedule slots adhering to channel rules."""
    rules = load_channel_rules(channel_name)
    upload_rules = rules.get("upload_rules", DEFAULT_RULES["upload_rules"])
    type_key = "shorts" if is_short else "long"
    type_rules = upload_rules.get(type_key, DEFAULT_RULES["upload_rules"][type_key])
    optimal_times = type_rules.get("optimal_times", ["07:00", "12:00", "17:00"] if is_short else ["19:00"])

    current = start_from or datetime.now(timezone.utc)
    current_date = current.date()

    slots: list[str] = []
    day_offset = 0

    while len(slots) < count and day_offset < 60:
        day = current_date + timedelta(days=day_offset)
        for t_str in optimal_times:
            hh, mm = map(int, t_str.split(":"))
            candidate = datetime(day.year, day.month, day.day, hh, mm, tzinfo=timezone.utc)
            if candidate <= current:
                continue
            ok, _ = validate_upload(channel_name, candidate, is_short=is_short)
            if ok:
                slots.append(candidate.isoformat())
                if len(slots) == count:
                    break
        day_offset += 1

    return slots


def upload_video(
    channel_name: str,
    video_path: str | Path,
    title: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    category_id: str = "25",
    schedule_at: Optional[str] = None,
    is_short: bool = True,
    privacy_status: str = "private",
) -> str:
    """Upload a video to YouTube with resume support, auto-hashtags, and schedule."""
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_file}")

    rules = load_channel_rules(channel_name)
    seo_rules = rules.get("seo", DEFAULT_RULES["seo"])

    # Ensure #Shorts in title if short
    if is_short and "#Shorts" not in title and "#shorts" not in title.lower():
        title = f"{title} #Shorts"

    title_max = seo_rules.get("title_max_chars", 65)
    if len(title) > title_max:
        title = title[:title_max]

    all_tags = list(tags or [])
    for d_tag in seo_rules.get("default_tags", []):
        if d_tag not in all_tags:
            all_tags.append(d_tag)

    body: dict[str, Any] = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": all_tags,
            "categoryId": category_id or seo_rules.get("default_category", "25"),
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    if schedule_at:
        sched_dt = _parse_dt(schedule_at)
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = sched_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    service = get_authenticated_service(channel_name)

    chunksize = 10 * 1024 * 1024  # 10MB chunk
    media = MediaFileUpload(
        str(video_file),
        mimetype="video/mp4",
        chunksize=chunksize,
        resumable=True,
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    logger.info("Uploading %s to channel %s...", video_file.name, channel_name)
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("Upload progress: %d%%", int(status.progress() * 100))

    video_id = response.get("id", "")
    logger.info("Uploaded video %s successfully with ID %s", video_file.name, video_id)

    # Save to history
    save_upload_history_entry(
        channel_name,
        {
            "video_id": video_id,
            "title": title,
            "video_path": str(video_file),
            "is_short": is_short,
            "schedule_at": schedule_at,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return video_id
