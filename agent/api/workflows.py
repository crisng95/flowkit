"""Workflow helper endpoints for CLI parity features."""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional
from urllib.parse import quote

import aiohttp
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agent.config import BASE_DIR, OUTPUT_DIR
from agent.db import crud
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.utils.orientation import normalize_orientation
from agent.utils.paths import resolve_4k_file, scene_tts_path
from agent.utils.slugify import slugify
from agent.services.video_reviewer import review_video
from agent.services.local_upscaler import local_upscale_health as get_local_upscale_health

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)
_repo = SQLiteRepository()

_DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b"),
    re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),
    re.compile(
        r"\b\d{1,2}\s+(?:th[áa]ng|tháng|month|apr|march|january|february|june|july|august|september|october|november|december)\s+\d{2,4}\b",
        re.IGNORECASE,
    ),
]
_COST_PATTERN = re.compile(
    r"(\$\s?\d[\d,\.]*|\d[\d,\.]*\s*(?:usd|vnd|triệu|tỷ|million|billion))",
    re.IGNORECASE,
)
_STAT_PATTERN = re.compile(
    r"(\d[\d,\.]*\s*(?:%|km|m|mi|người|people|casualties|lính|scene|fps|hours|minutes|s|sec))",
    re.IGNORECASE,
)
_NAME_PATTERN = re.compile(r"\b([A-ZÀ-Ý][\wÀ-ỹ-]*(?:\s+[A-ZÀ-Ý][\wÀ-ỹ-]*){1,3})\b")
_VI_MARKER = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]")
_ES_MARKER = re.compile(r"[ñáéíóúüÑÁÉÍÓÚÜ]")


class TextOverlayItem(BaseModel):
    text: str
    style: Literal["date", "name", "stat", "cost"]


class GenerateTextOverlaysRequest(BaseModel):
    language: Optional[str] = Field(None, max_length=8, description="vi, en, es... (auto-detect if omitted)")


class GenerateTextOverlaysResponse(BaseModel):
    project_id: str
    video_id: str
    language: str
    scenes_total: int
    scenes_with_overlays: int
    items_total: int
    output_path: str
    overlays: dict[str, list[TextOverlayItem]]


class BrandLogoRequest(BaseModel):
    channel_name: str = Field(..., min_length=1, max_length=120)
    project_id: Optional[str] = None
    video_id: Optional[str] = None
    video_path: Optional[str] = None
    output_path: Optional[str] = None
    size: Optional[int] = Field(None, ge=64, le=512)
    apply_thumbnails: bool = False
    include_intro: bool = True
    include_outro: bool = True


class BrandLogoResponse(BaseModel):
    output_path: str
    width: int
    height: int
    logo_size: int
    logo_padding: int
    intro_used: Optional[str] = None
    outro_used: Optional[str] = None
    badge_4k_applied: bool = False
    thumbnails: list[str] = Field(default_factory=list)


class DownloadUpscalesRequest(BaseModel):
    project_id: Optional[str] = None
    orientation: Optional[str] = None
    overwrite: bool = False


class DownloadUpscalesResponse(BaseModel):
    project_id: str
    video_id: str
    orientation: str
    output_dir: str
    downloaded: list[str]
    skipped: list[str]
    failed: list[str]


class SmartContinueRequest(BaseModel):
    project_id: Optional[str] = None
    orientation: Optional[str] = None
    include_upscale: bool = True
    include_tts: bool = False
    include_concat: bool = False
    auto_download_upscales: bool = False
    fit_narrator: bool = True
    narrator_buffer: float = Field(default=0.5, ge=0, le=6)
    tts_template: Optional[str] = None
    review_before_upscale: bool = True
    review_mode: Literal["light", "deep"] = "light"
    review_threshold: float = Field(default=7.5, ge=0, le=10)
    max_review_regens: int = Field(default=12, ge=1, le=200)
    low_score_regen_image_threshold: float = Field(default=4.0, ge=0, le=10)


class SmartContinueResponse(BaseModel):
    project_id: str
    video_id: str
    orientation: str
    action: str
    message: str
    queued_requests: int = 0
    requested_types: list[str] = Field(default_factory=list)
    review: Optional[dict[str, Any]] = None
    downloaded: Optional[dict[str, int]] = None
    concat_output: Optional[str] = None


class ResearchSource(BaseModel):
    title: str
    url: str
    snippet: str


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300)
    language: Optional[str] = Field(default="vi", max_length=8)
    limit: int = Field(default=3, ge=1, le=8)


class ResearchResponse(BaseModel):
    topic: str
    language: str
    summary: str
    key_facts: list[str]
    suggested_story_angle: str
    sources: list[ResearchSource]
    output_path: str


class YouTubeReferenceRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=1000)
    language: Optional[str] = Field(default="vi", max_length=16)
    max_chars: int = Field(default=12000, ge=1500, le=40000)


class YouTubeReferenceResponse(BaseModel):
    url: str
    video_id: str
    title: str
    channel: Optional[str] = None
    duration_sec: Optional[int] = None
    upload_date: Optional[str] = None
    transcript_language: str
    caption_type: Literal["subtitles", "automatic_captions"]
    transcript_chars: int
    transcript_truncated: bool
    transcript: str


@router.get("/local-upscale/health")
async def local_upscale_health():
    """Check local 4K upscaler dependencies (ffmpeg + Real-ESRGAN)."""
    return get_local_upscale_health()


def _obj(item, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _clip_text(text: str, max_len: int = 40) -> str:
    compact = " ".join((text or "").strip().split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1].rstrip() + "…"


def _detect_language(text: str) -> str:
    if _VI_MARKER.search(text):
        return "vi"
    if _ES_MARKER.search(text):
        return "es"
    return "en"


def _extract_with_patterns(patterns: list[re.Pattern], text: str) -> str | None:
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(0)
    return None


def _extract_overlay_candidates(text: str) -> list[TextOverlayItem]:
    if not text or not text.strip():
        return []

    out: list[TextOverlayItem] = []
    seen: set[str] = set()

    date_text = _extract_with_patterns(_DATE_PATTERNS, text)
    if date_text:
        normalized = _clip_text(date_text)
        out.append(TextOverlayItem(text=normalized, style="date"))
        seen.add(normalized.lower())

    cost_match = _COST_PATTERN.search(text)
    if cost_match:
        val = _clip_text(cost_match.group(1))
        if val.lower() not in seen:
            out.append(TextOverlayItem(text=val, style="cost"))
            seen.add(val.lower())

    stat_match = _STAT_PATTERN.search(text)
    if stat_match:
        val = _clip_text(stat_match.group(1))
        if val.lower() not in seen:
            out.append(TextOverlayItem(text=val, style="stat"))
            seen.add(val.lower())

    name_match = _NAME_PATTERN.search(text)
    if name_match:
        val = _clip_text(name_match.group(1))
        if val.lower() not in seen:
            out.append(TextOverlayItem(text=val, style="name"))
            seen.add(val.lower())

    if not out:
        first_sentence = re.split(r"[.!?]\s+", text.strip())[0]
        if first_sentence:
            out.append(TextOverlayItem(text=_clip_text(first_sentence), style="name"))

    return out[:2]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").replace("&quot;", "\"").replace("&amp;", "&").strip()


def _extract_facts_from_text(text: str, limit: int = 5) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text or "")
    facts: list[str] = []
    for c in chunks:
        t = " ".join(c.split()).strip()
        if len(t) < 20:
            continue
        # Prefer concrete statements with numbers/dates.
        if re.search(r"\d", t):
            facts.append(t)
        if len(facts) >= limit:
            break
    if not facts:
        for c in chunks:
            t = " ".join(c.split()).strip()
            if len(t) >= 24:
                facts.append(t)
            if len(facts) >= limit:
                break
    return facts[:limit]


def _run_cmd(cmd: list[str], timeout: int = 300):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        stderr = (result.stderr or "")[-600:]
        raise HTTPException(500, f"Command failed: {' '.join(cmd[:3])}... {stderr}")
    return result


def _normalize_yt_lang(lang: str) -> str:
    return (lang or "en").strip().lower().replace("_", "-")


def _lang_candidates(lang: str) -> list[str]:
    normalized = _normalize_yt_lang(lang)
    out = [normalized]
    if "-" in normalized:
        out.append(normalized.split("-", 1)[0])
    if "en" not in out:
        out.append("en")
    if "en-orig" not in out:
        out.append("en-orig")
    return out


def _pick_caption_track(
    captions: dict[str, list[dict[str, Any]]] | None,
    preferred_lang: str,
) -> tuple[str, dict[str, Any]] | None:
    if not captions:
        return None
    keys = list(captions.keys())
    if not keys:
        return None

    def find_key(candidates: list[str]) -> str | None:
        for cand in candidates:
            for key in keys:
                if key.lower() == cand:
                    return key
        for cand in candidates:
            for key in keys:
                if key.lower().startswith(cand + "-"):
                    return key
        return None

    chosen_key = find_key(_lang_candidates(preferred_lang)) or keys[0]
    entries = captions.get(chosen_key) or []
    if not entries:
        return None

    rank = {"json3": 0, "srv3": 1, "vtt": 2, "ttml": 3, "srt": 4}
    chosen_entry = sorted(
        (e for e in entries if isinstance(e, dict) and e.get("url")),
        key=lambda e: rank.get(str(e.get("ext", "")).lower(), 9),
    )
    if not chosen_entry:
        return None
    return chosen_key, chosen_entry[0]


def _parse_json3_transcript(payload: dict[str, Any]) -> str:
    events = payload.get("events") or []
    lines: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        segs = event.get("segs") or []
        if not isinstance(segs, list):
            continue
        raw = "".join(str(seg.get("utf8", "")) for seg in segs if isinstance(seg, dict))
        line = " ".join(raw.replace("\n", " ").split()).strip()
        if not line:
            continue
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return " ".join(lines).strip()


def _parse_text_transcript(raw: str) -> str:
    lines: list[str] = []
    for ln in (raw or "").splitlines():
        line = ln.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        line = _strip_html(line)
        line = " ".join(line.split())
        if not line:
            continue
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return " ".join(lines).strip()


def _trim_transcript(text: str, max_chars: int) -> tuple[str, bool]:
    clean = " ".join((text or "").split()).strip()
    if len(clean) <= max_chars:
        return clean, False
    head = int(max_chars * 0.78)
    tail = max(200, max_chars - head - 26)
    trimmed = f"{clean[:head].rstrip()} ...[truncated]... {clean[-tail:].lstrip()}"
    return trimmed, True


def _format_upload_date(raw: str | None) -> str | None:
    if not raw:
        return None
    if re.fullmatch(r"\d{8}", raw):
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


async def _download_to_file(url: str, output_path: Path) -> bool:
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


def _probe_resolution(path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(path),
    ]
    out = _run_cmd(cmd, timeout=30).stdout.strip()
    if "x" not in out:
        raise HTTPException(500, f"Cannot read video resolution: {path}")
    w_str, h_str = out.split("x", 1)
    return int(w_str), int(h_str)


def _normalize_video(input_path: Path, output_path: Path, width: int, height: int):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-r",
        "24",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    _run_cmd(cmd, timeout=900)


def _concat_videos(parts: list[Path], output_path: Path):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in parts:
            safe = str(p).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
        concat_list = Path(f.name)
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        _run_cmd(cmd, timeout=900)
    finally:
        concat_list.unlink(missing_ok=True)


def _overlay_icon(input_video: Path, icon_path: Path, output_video: Path, size: int, pad: int, top_right: bool = False):
    icon_scaled = f"[1:v]scale={size}:{size},format=rgba[icon]"
    pos = f"W-w-{pad}:{pad}" if top_right else f"W-w-{pad}:H-h-{pad}"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-i",
        str(icon_path),
        "-filter_complex",
        f"{icon_scaled};[0:v][icon]overlay={pos}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-r",
        "24",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_video),
    ]
    _run_cmd(cmd, timeout=900)


def _resolve_video_path(video_path: Optional[str], project_slug: str, orientation: str, video_obj) -> Path:
    if video_path:
        p = Path(video_path).expanduser().resolve()
        if p.exists():
            return p
        raise HTTPException(400, f"video_path not found: {video_path}")

    candidates = [
        OUTPUT_DIR / project_slug / f"{project_slug}_final_{orientation.lower()}_music.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_{orientation.lower()}.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_vertical_music.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_vertical.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_horizontal_music.mp4",
        OUTPUT_DIR / project_slug / f"{project_slug}_final_horizontal.mp4",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    for key in ("vertical_url", "horizontal_url"):
        raw = _obj(video_obj, key)
        if not raw or str(raw).startswith("http"):
            continue
        p = Path(raw)
        if p.exists():
            return p.resolve()

    raise HTTPException(400, "Cannot infer final video path. Run concat first or provide video_path.")


def _pick_first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


async def _enqueue_request_if_needed(
    *,
    req_type: str,
    project_id: str,
    orientation: str,
    video_id: Optional[str] = None,
    scene_id: Optional[str] = None,
    character_id: Optional[str] = None,
    source_media_id: Optional[str] = None,
) -> bool:
    if scene_id:
        existing = await crud.list_requests(scene_id=scene_id)
        for r in existing:
            if r.get("type") == req_type and r.get("status") in ("PENDING", "PROCESSING"):
                return False
    if character_id:
        existing = await crud.list_requests(project_id=project_id)
        for r in existing:
            if (
                r.get("character_id") == character_id
                and r.get("type") == req_type
                and r.get("status") in ("PENDING", "PROCESSING")
            ):
                return False

    if video_id and orientation:
        await crud.update_video(video_id, orientation=orientation)

    await crud.create_request(
        req_type=req_type,
        project_id=project_id,
        video_id=video_id,
        scene_id=scene_id,
        character_id=character_id,
        orientation=orientation,
        source_media_id=source_media_id,
    )
    return True


@router.post("/research", response_model=ResearchResponse)
async def research_topic(body: ResearchRequest):
    """Fact-check topic from web sources and persist to .omc/research (fk:research parity)."""
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(400, "topic is required")
    lang = (body.language or "vi").strip().lower()
    if lang.startswith("vi"):
        wiki_lang = "vi"
    elif lang.startswith("es"):
        wiki_lang = "es"
    else:
        wiki_lang = "en"

    search_url = f"https://{wiki_lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": topic,
        "utf8": 1,
        "format": "json",
        "srlimit": body.limit,
    }

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(search_url, params=params) as resp:
                if resp.status != 200:
                    raise HTTPException(502, f"Research search failed (HTTP {resp.status})")
                raw_search = await resp.json()

            rows = raw_search.get("query", {}).get("search", []) or []
            if not rows:
                raise HTTPException(404, f"No research results for topic: {topic}")

            sources: list[ResearchSource] = []
            summaries: list[str] = []
            for row in rows[: body.limit]:
                title = (row.get("title") or "").strip()
                if not title:
                    continue
                snippet = _strip_html(row.get("snippet") or "")
                summary_url = f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
                async with session.get(summary_url) as s_resp:
                    if s_resp.status != 200:
                        continue
                    sd = await s_resp.json()
                extract = (sd.get("extract") or "").strip()
                page = (sd.get("content_urls", {}).get("desktop", {}).get("page") or "").strip()
                if not page:
                    page = f"https://{wiki_lang}.wikipedia.org/wiki/{quote(title)}"
                sources.append(ResearchSource(title=title, url=page, snippet=snippet or _clip_text(extract, 140)))
                if extract:
                    summaries.append(extract)

        if not sources:
            raise HTTPException(404, f"No valid research summaries for topic: {topic}")

        merged_summary = "\n\n".join(summaries[:3]).strip()
        key_facts = _extract_facts_from_text(merged_summary, limit=6)
        if not key_facts:
            key_facts = [s.snippet for s in sources[:5] if s.snippet]
        angle = (
            "Kể theo nhịp: bối cảnh ban đầu → bước ngoặt chính → hệ quả dài hạn, "
            "nhấn mạnh mốc thời gian và nhân vật then chốt."
        )

        out_dir = BASE_DIR / ".omc" / "research"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{ts}_{slugify(topic)[:96]}.md"
        lines = [
            f"# Research: {topic}",
            "",
            f"- Time (UTC): {datetime.now(timezone.utc).isoformat()}",
            f"- Language: {lang}",
            "",
            "## Summary",
            merged_summary or "(No summary)",
            "",
            "## Key Facts",
        ]
        for fact in key_facts:
            lines.append(f"- {fact}")
        lines.extend(["", "## Sources"])
        for s in sources:
            lines.append(f"- {s.title}: {s.url}")
        out_path.write_text("\n".join(lines), encoding="utf-8")

        return ResearchResponse(
            topic=topic,
            language=lang,
            summary=merged_summary,
            key_facts=key_facts,
            suggested_story_angle=angle,
            sources=sources,
            output_path=str(out_path),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Research workflow failed")
        raise HTTPException(500, f"Research failed: {e}")


@router.post("/youtube-reference", response_model=YouTubeReferenceResponse)
async def youtube_reference(body: YouTubeReferenceRequest):
    """Extract transcript + metadata from a YouTube URL for script cloning/adaptation flow."""
    url = body.url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise HTTPException(400, "url must be a valid http(s) URL")
    if ("youtube.com" not in url.lower()) and ("youtu.be" not in url.lower()):
        raise HTTPException(400, "Only YouTube URLs are supported")

    if shutil.which("yt-dlp") is None:
        raise HTTPException(500, "yt-dlp is not installed in this environment")

    try:
        cmd = ["yt-dlp", "--dump-single-json", "--skip-download", "--no-warnings", "--", url]
        result = _run_cmd(cmd, timeout=180)
        info = json.loads(result.stdout or "{}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch YouTube metadata: {e}") from e

    video_id = str(info.get("id") or "").strip()
    title = str(info.get("title") or "").strip()
    if not video_id or not title:
        raise HTTPException(502, "Could not parse video metadata from YouTube URL")

    preferred_lang = (body.language or "vi").strip().lower()
    subtitles = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}

    picked = _pick_caption_track(subtitles, preferred_lang)
    caption_type: Literal["subtitles", "automatic_captions"] = "subtitles"
    if not picked:
        picked = _pick_caption_track(automatic, preferred_lang)
        caption_type = "automatic_captions"
    if not picked:
        raise HTTPException(
            422,
            "No transcript/captions found for this video. Try another video with subtitles.",
        )

    track_lang, track = picked
    caption_url = str(track.get("url") or "").strip()
    track_ext = str(track.get("ext") or "json3").strip().lower()
    if not caption_url:
        raise HTTPException(502, "Caption track URL is missing")

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(caption_url) as resp:
                if resp.status != 200:
                    raise HTTPException(502, f"Failed downloading transcript (HTTP {resp.status})")
                payload_text = await resp.text()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Failed downloading transcript: {e}") from e

    transcript = ""
    if track_ext == "json3":
        try:
            payload = json.loads(payload_text or "{}")
            transcript = _parse_json3_transcript(payload)
        except Exception:
            transcript = _parse_text_transcript(payload_text)
    else:
        transcript = _parse_text_transcript(payload_text)

    if not transcript:
        raise HTTPException(422, "Transcript is empty or unavailable for this video")

    transcript, was_truncated = _trim_transcript(transcript, body.max_chars)

    duration_raw = info.get("duration")
    duration_sec = int(duration_raw) if isinstance(duration_raw, (int, float)) else None
    channel = str(info.get("channel") or info.get("uploader") or "").strip() or None
    upload_date = _format_upload_date(str(info.get("upload_date") or "").strip() or None)

    return YouTubeReferenceResponse(
        url=url,
        video_id=video_id,
        title=title,
        channel=channel,
        duration_sec=duration_sec,
        upload_date=upload_date,
        transcript_language=track_lang,
        caption_type=caption_type,
        transcript_chars=len(transcript),
        transcript_truncated=was_truncated,
        transcript=transcript,
    )


@router.get("/channels")
async def list_channels():
    channels_dir = BASE_DIR / "youtube" / "channels"
    if not channels_dir.exists():
        return []
    rows = []
    for d in sorted(channels_dir.iterdir(), key=lambda p: p.name.lower()):
        if not d.is_dir():
            continue
        icon = d / f"{d.name}_icon.png"
        rows.append(
            {
                "name": d.name,
                "icon_exists": icon.exists(),
                "intro_exists": any((d / f).exists() for f in ("intro_4k_2x.mp4", "intro_4k.mp4", "intro_1080.mp4")),
                "outro_exists": any((d / f).exists() for f in ("outro_4k.mp4", "outro_1080.mp4")),
                "badge_4k_exists": (d / "4k_icon.png").exists(),
            }
        )
    return rows


@router.get("/status")
async def workflow_status(
    project_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
):
    """Aggregated status dashboard (fk:status + fk:monitor parity)."""
    if not project_id:
        projects = await crud.list_projects()
        out = []
        for p in projects:
            pid = _obj(p, "id")
            videos = await _repo.list_videos(pid)
            out.append(
                {
                    "id": pid,
                    "name": _obj(p, "name"),
                    "status": _obj(p, "status"),
                    "tier": _obj(p, "user_paygate_tier"),
                    "orientation": normalize_orientation(_obj(p, "orientation")),
                    "material": _obj(p, "material"),
                    "video_count": len(videos),
                    "created_at": _obj(p, "created_at"),
                }
            )
        return {"projects": out, "count": len(out)}

    project = await _repo.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    characters = await _repo.get_project_characters(project_id)
    videos = await _repo.list_videos(project_id)
    if not videos:
        return {
            "project": {
                "id": _obj(project, "id"),
                "name": _obj(project, "name"),
                "status": _obj(project, "status"),
                "material": _obj(project, "material"),
            },
            "videos": [],
            "message": "No videos in project",
        }

    active_video = None
    if video_id:
        active_video = next((v for v in videos if _obj(v, "id") == video_id), None)
    if not active_video:
        active_video = videos[0]

    vid = _obj(active_video, "id")
    scenes = sorted(await _repo.list_scenes(vid), key=lambda s: _obj(s, "display_order", 0))
    orientation = normalize_orientation(
        _obj(active_video, "orientation") or _obj(project, "orientation") or "VERTICAL"
    )
    prefix = orientation.lower()
    project_slug = slugify(_obj(project, "name") or "project")

    refs_total = len(characters)
    refs_done = sum(1 for c in characters if _obj(c, "media_id"))
    scenes_total = len(scenes)
    images_done = sum(1 for s in scenes if _obj(s, f"{prefix}_image_status") == "COMPLETED")
    videos_done = sum(1 for s in scenes if _obj(s, f"{prefix}_video_status") == "COMPLETED")
    upscales_done = sum(1 for s in scenes if _obj(s, f"{prefix}_upscale_status") == "COMPLETED")
    tts_total = sum(1 for s in scenes if (_obj(s, "narrator_text") or "").strip())
    tts_done = sum(
        1
        for s in scenes
        if (_obj(s, "narrator_text") or "").strip()
        and scene_tts_path(project_slug, int(_obj(s, "display_order", 0)), _obj(s, "id")).exists()
    )
    downloads_done = sum(
        1
        for s in scenes
        if resolve_4k_file(project_slug, int(_obj(s, "display_order", 0)), _obj(s, "id")) is not None
    )

    if refs_total > refs_done:
        next_action = "gen_refs"
    elif scenes_total > images_done:
        next_action = "gen_images"
    elif scenes_total > videos_done:
        next_action = "gen_videos"
    elif scenes_total > upscales_done:
        next_action = "review_or_upscale"
    elif scenes_total > downloads_done:
        next_action = "download_upscales"
    elif tts_total > tts_done:
        next_action = "gen_tts"
    else:
        next_action = "concat"

    pending = await crud.list_requests(project_id=project_id, status="PENDING")
    processing = await crud.list_requests(project_id=project_id, status="PROCESSING")
    failed = await crud.list_requests(project_id=project_id, status="FAILED")

    def scene_status_row(s):
        order = int(_obj(s, "display_order", 0))
        narrator_text = _obj(s, "narrator_text") or ""
        tts_path = scene_tts_path(project_slug, order, _obj(s, "id"))
        tts_ready = bool(narrator_text.strip()) and tts_path.exists()
        local_4k = resolve_4k_file(project_slug, order, _obj(s, "id"))
        return {
            "id": _obj(s, "id"),
            "display_order": _obj(s, "display_order"),
            "prompt": _obj(s, "prompt"),
            "character_names": _obj(s, "character_names"),
            "narrator_text": narrator_text,
            "image_status": _obj(s, f"{prefix}_image_status"),
            "video_status": _obj(s, f"{prefix}_video_status"),
            "upscale_status": _obj(s, f"{prefix}_upscale_status"),
            "tts_status": "COMPLETED" if tts_ready else ("PENDING" if narrator_text.strip() else "SKIPPED"),
            "image_url": _obj(s, f"{prefix}_image_url"),
            "video_url": _obj(s, f"{prefix}_video_url"),
            "tts_audio_path": str(tts_path) if tts_ready else None,
            "download_ready": local_4k is not None,
            "download_path": str(local_4k) if local_4k is not None else None,
        }

    return {
        "project": {
            "id": _obj(project, "id"),
            "name": _obj(project, "name"),
            "status": _obj(project, "status"),
            "material": _obj(project, "material"),
        },
        "video": {
            "id": vid,
            "title": _obj(active_video, "title"),
            "orientation": orientation,
        },
        "counts": {
            "refs_done": refs_done,
            "refs_total": refs_total,
            "images_done": images_done,
            "images_total": scenes_total,
            "videos_done": videos_done,
            "videos_total": scenes_total,
            "upscales_done": upscales_done,
            "upscales_total": scenes_total,
            "tts_done": tts_done,
            "tts_total": tts_total,
            "downloads_done": downloads_done,
            "downloads_total": scenes_total,
        },
        "queue": {
            "pending": len(pending),
            "processing": len(processing),
            "failed": len(failed),
        },
        "characters": [
            {
                "id": _obj(c, "id"),
                "name": _obj(c, "name"),
                "entity_type": _obj(c, "entity_type"),
                "media_id": _obj(c, "media_id"),
                "reference_image_url": _obj(c, "reference_image_url"),
                "ready": bool(_obj(c, "media_id")),
            }
            for c in characters
        ],
        "scenes": [scene_status_row(s) for s in scenes],
        "suggested_next_action": next_action,
    }


@router.post("/videos/{video_id}/text-overlays", response_model=GenerateTextOverlaysResponse)
async def generate_text_overlays(video_id: str, body: GenerateTextOverlaysRequest):
    """Generate text_overlays.json from narrator text (fk:gen-text-overlays parity)."""
    video = await _repo.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    project_id = _obj(video, "project_id")
    project = await _repo.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    scenes = sorted(await _repo.list_scenes(video_id), key=lambda s: _obj(s, "display_order", 0))
    if not scenes:
        raise HTTPException(400, "No scenes found for this video")

    joined_text = " ".join((_obj(s, "narrator_text") or "") for s in scenes)
    language = (body.language or "").strip().lower() or _detect_language(joined_text)
    if not language:
        language = "en"

    candidates: list[tuple[int, list[TextOverlayItem]]] = []
    for scene in scenes:
        text = (_obj(scene, "narrator_text") or "").strip()
        if not text:
            continue
        extracted = _extract_overlay_candidates(text)
        if extracted:
            candidates.append((_obj(scene, "display_order", 0), extracted[:2]))

    target = max(1, round(len(scenes) * 0.45))
    selected = sorted(candidates, key=lambda x: (len(x[1]), -x[0]), reverse=True)[:target]
    selected_orders = {order for order, _items in selected}

    overlays: dict[str, list[TextOverlayItem]] = {}
    for order, items in candidates:
        if order in selected_orders:
            overlays[str(order)] = items[:2]

    project_slug = slugify(_obj(project, "name") or "project")
    out_dir = OUTPUT_DIR / project_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "text_overlays.json"

    raw_payload = {
        key: [item.model_dump() for item in values]
        for key, values in overlays.items()
    }
    out_path.write_text(json.dumps(raw_payload, indent=2, ensure_ascii=False))

    items_total = sum(len(v) for v in overlays.values())
    return GenerateTextOverlaysResponse(
        project_id=project_id,
        video_id=video_id,
        language=language,
        scenes_total=len(scenes),
        scenes_with_overlays=len(overlays),
        items_total=items_total,
        output_path=str(out_path),
        overlays=overlays,
    )


@router.post("/brand-logo", response_model=BrandLogoResponse)
async def apply_brand_logo(body: BrandLogoRequest):
    """Apply intro/outro + logo watermark + 4K badge (fk:brand-logo parity)."""
    project = None
    video = None
    resolved_project_id = body.project_id

    if body.video_id:
        video = await _repo.get_video(body.video_id)
        if not video:
            raise HTTPException(404, "Video not found")
        resolved_project_id = _obj(video, "project_id")

    if resolved_project_id:
        project = await _repo.get_project(resolved_project_id)
        if not project:
            raise HTTPException(404, "Project not found")

    if not project and not body.video_path:
        raise HTTPException(400, "Provide project_id/video_id or explicit video_path")

    project_slug = slugify(_obj(project, "name") or "project") if project else "project"
    orientation = normalize_orientation(
        _obj(video, "orientation") if video else (_obj(project, "orientation") if project else "VERTICAL")
    )
    source_video = _resolve_video_path(body.video_path, project_slug, orientation, video)
    if not source_video.exists():
        raise HTTPException(404, f"Source video not found: {source_video}")

    channel_dir = BASE_DIR / "youtube" / "channels" / body.channel_name
    if not channel_dir.exists():
        raise HTTPException(404, f"Channel not found: {channel_dir}")
    logo = channel_dir / f"{body.channel_name}_icon.png"
    if not logo.exists():
        raise HTTPException(400, f"Missing channel logo: {logo}")

    width, height = _probe_resolution(source_video)
    if body.size is not None:
        logo_size = body.size
    elif width >= 3840:
        logo_size = 220
    elif width >= 1920:
        logo_size = 130
    else:
        logo_size = 110
    logo_padding = 40 if width >= 3840 else 24 if width >= 1920 else 16

    intro_used = None
    outro_used = None
    if width >= 3840:
        intro_candidates = [channel_dir / "intro_4k_2x.mp4", channel_dir / "intro_4k.mp4", channel_dir / "intro_1080.mp4"]
        outro_candidates = [channel_dir / "outro_4k.mp4", channel_dir / "outro_1080.mp4"]
    else:
        intro_candidates = [channel_dir / "intro_1080.mp4", channel_dir / "intro_4k.mp4"]
        outro_candidates = [channel_dir / "outro_1080.mp4", channel_dir / "outro_4k.mp4"]
    intro_file = _pick_first_existing(intro_candidates) if body.include_intro else None
    outro_file = _pick_first_existing(outro_candidates) if body.include_outro else None

    if intro_file:
        intro_used = str(intro_file)
    if outro_file:
        outro_used = str(outro_file)

    out_path = Path(body.output_path).expanduser().resolve() if body.output_path else source_video.with_name(f"{source_video.stem}_branded.mp4")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    thumbnails: list[str] = []
    badge_applied = False

    with tempfile.TemporaryDirectory(prefix="flowkit_brand_") as tmp:
        tmpdir = Path(tmp)
        main_norm = tmpdir / "main_norm.mp4"
        _normalize_video(source_video, main_norm, width, height)

        parts = [main_norm]
        if intro_file:
            intro_norm = tmpdir / "intro_norm.mp4"
            _normalize_video(intro_file, intro_norm, width, height)
            parts.insert(0, intro_norm)
        if outro_file:
            outro_norm = tmpdir / "outro_norm.mp4"
            _normalize_video(outro_file, outro_norm, width, height)
            parts.append(outro_norm)

        merged = tmpdir / "merged.mp4"
        _concat_videos(parts, merged)

        branded = tmpdir / "branded.mp4"
        _overlay_icon(merged, logo, branded, logo_size, logo_padding, top_right=False)

        badge_4k = channel_dir / "4k_icon.png"
        final_source = branded
        if width >= 3840 and badge_4k.exists():
            with_badge = tmpdir / "branded_badge.mp4"
            _overlay_icon(branded, badge_4k, with_badge, 180, 40, top_right=True)
            final_source = with_badge
            badge_applied = True

        out_path.write_bytes(final_source.read_bytes())

    if body.apply_thumbnails and project:
        thumbs_dir = OUTPUT_DIR / project_slug / "thumbnails"
        if thumbs_dir.exists():
            for thumb in sorted(thumbs_dir.glob("*.png")):
                if thumb.stem.endswith("_branded"):
                    continue
                thumb_out = thumb.with_name(f"{thumb.stem}_branded.png")
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(thumb),
                    "-i",
                    str(logo),
                    "-filter_complex",
                    "[1:v]scale=72:72[icon];[0:v][icon]overlay=W-w-16:H-h-16",
                    str(thumb_out),
                ]
                _run_cmd(cmd, timeout=120)
                thumbnails.append(str(thumb_out))

    return BrandLogoResponse(
        output_path=str(out_path),
        width=width,
        height=height,
        logo_size=logo_size,
        logo_padding=logo_padding,
        intro_used=intro_used,
        outro_used=outro_used,
        badge_4k_applied=badge_applied,
        thumbnails=thumbnails,
    )


@router.post("/videos/{video_id}/download-upscales", response_model=DownloadUpscalesResponse)
async def download_upscales(video_id: str, body: DownloadUpscalesRequest):
    """Download completed upscale clips to local output/<project>/4k (fk:monitor parity)."""
    video = await _repo.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found")

    project_id = body.project_id or _obj(video, "project_id")
    if not project_id:
        raise HTTPException(400, "project_id is required")
    project = await _repo.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    orientation = normalize_orientation(
        body.orientation or _obj(video, "orientation") or _obj(project, "orientation") or "VERTICAL"
    )
    prefix = orientation.lower()
    scenes = sorted(await _repo.list_scenes(video_id), key=lambda s: _obj(s, "display_order", 0))
    if not scenes:
        raise HTTPException(400, "No scenes found for this video")

    project_slug = slugify(_obj(project, "name") or "project")
    output_dir = OUTPUT_DIR / project_slug / "4k"
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for scene in scenes:
        order = int(_obj(scene, "display_order", 0))
        scene_id = _obj(scene, "id")
        status = _obj(scene, f"{prefix}_upscale_status")
        if status != "COMPLETED":
            skipped.append(f"scene_{order + 1}: status={status or 'UNKNOWN'}")
            continue

        url = _obj(scene, f"{prefix}_upscale_url") or _obj(scene, f"{prefix}_video_url")
        if not url:
            failed.append(f"scene_{order + 1}: missing url")
            continue

        out_path = output_dir / f"scene_{order:03d}_{scene_id}.mp4"
        if out_path.exists() and not body.overwrite:
            skipped.append(f"scene_{order + 1}: exists")
            continue

        if str(url).startswith("http"):
            ok = await _download_to_file(str(url), out_path)
            if not ok:
                failed.append(f"scene_{order + 1}: download failed")
                continue
            downloaded.append(str(out_path))
            continue

        local_src = Path(str(url))
        if local_src.exists():
            out_path.write_bytes(local_src.read_bytes())
            downloaded.append(str(out_path))
        else:
            failed.append(f"scene_{order + 1}: source missing")

    return DownloadUpscalesResponse(
        project_id=project_id,
        video_id=video_id,
        orientation=orientation,
        output_dir=str(output_dir),
        downloaded=downloaded,
        skipped=skipped,
        failed=failed,
    )


@router.post("/videos/{video_id}/smart-continue", response_model=SmartContinueResponse)
async def smart_continue(video_id: str, body: SmartContinueRequest):
    """Advance pipeline by one smart step (fk:pipeline parity with review-before-upscale)."""
    video = await _repo.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found")

    project_id = body.project_id or _obj(video, "project_id")
    if not project_id:
        raise HTTPException(400, "project_id is required")
    project = await _repo.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    orientation = normalize_orientation(
        body.orientation or _obj(video, "orientation") or _obj(project, "orientation") or "VERTICAL"
    )
    prefix = orientation.lower()
    await crud.update_video(video_id, orientation=orientation)

    scenes = sorted(await _repo.list_scenes(video_id), key=lambda s: _obj(s, "display_order", 0))
    characters = await _repo.get_project_characters(project_id)
    project_slug = slugify(_obj(project, "name") or "project")

    if not scenes:
        return SmartContinueResponse(
            project_id=project_id,
            video_id=video_id,
            orientation=orientation,
            action="noop",
            message="No scenes found for this video.",
        )

    scenes_total = len(scenes)
    tts_total = sum(1 for s in scenes if (_obj(s, "narrator_text") or "").strip())
    tts_done = sum(
        1
        for s in scenes
        if (_obj(s, "narrator_text") or "").strip()
        and scene_tts_path(project_slug, int(_obj(s, "display_order", 0)), _obj(s, "id")).exists()
    )
    downloads_done = sum(
        1
        for s in scenes
        if resolve_4k_file(project_slug, int(_obj(s, "display_order", 0)), _obj(s, "id")) is not None
    )

    async def _maybe_tts() -> bool:
        nonlocal tts_done
        if not body.include_tts or tts_total == 0 or tts_done >= tts_total:
            return False
        from agent.api.tts import NarrateVideoRequest, narrate_video

        await narrate_video(
            video_id,
            NarrateVideoRequest(
                project_id=project_id,
                template=body.tts_template,
                orientation=orientation,
                mix=True,
            ),
        )
        # Refresh tts_done after generation
        tts_done = sum(
            1
            for s in scenes
            if (_obj(s, "narrator_text") or "").strip()
            and scene_tts_path(project_slug, int(_obj(s, "display_order", 0)), _obj(s, "id")).exists()
        )
        return True

    # Stage 0: refs
    missing_chars = [c for c in characters if not _obj(c, "media_id")]
    if missing_chars:
        queued = 0
        for c in missing_chars:
            if await _enqueue_request_if_needed(
                req_type="GENERATE_CHARACTER_IMAGE",
                project_id=project_id,
                character_id=_obj(c, "id"),
                orientation=orientation,
            ):
                queued += 1

        return SmartContinueResponse(
            project_id=project_id,
            video_id=video_id,
            orientation=orientation,
            action="queue_refs",
            message=f"Queued {queued}/{len(missing_chars)} missing reference image requests.",
            queued_requests=queued,
            requested_types=["GENERATE_CHARACTER_IMAGE"] if queued > 0 else [],
        )

    # Stage 1: images (queue missing images but do not block video stage)
    pending_images = [s for s in scenes if not _obj(s, f"{prefix}_image_media_id")]
    queued_images = 0
    if pending_images:
        for s in pending_images:
            if await _enqueue_request_if_needed(
                req_type="GENERATE_IMAGE",
                project_id=project_id,
                video_id=video_id,
                scene_id=_obj(s, "id"),
                orientation=orientation,
            ):
                queued_images += 1

    # Stage 2: videos (only for scenes that already have image)
    pending_videos = [
        s
        for s in scenes
        if _obj(s, f"{prefix}_video_status") != "COMPLETED" and _obj(s, f"{prefix}_image_media_id")
    ]
    waiting_images = [
        s
        for s in scenes
        if _obj(s, f"{prefix}_video_status") != "COMPLETED" and not _obj(s, f"{prefix}_image_media_id")
    ]
    if pending_videos:
        tts_started = await _maybe_tts()
        queued_videos = 0
        for s in pending_videos:
            if await _enqueue_request_if_needed(
                req_type="GENERATE_VIDEO",
                project_id=project_id,
                video_id=video_id,
                scene_id=_obj(s, "id"),
                orientation=orientation,
            ):
                queued_videos += 1

        queued_upscales = 0
        if body.include_upscale:
            ready_for_upscale = [
                s
                for s in scenes
                if _obj(s, f"{prefix}_upscale_status") != "COMPLETED"
                and _obj(s, f"{prefix}_video_media_id")
            ]
            for s in ready_for_upscale:
                if await _enqueue_request_if_needed(
                    req_type="UPSCALE_VIDEO_LOCAL",
                    project_id=project_id,
                    video_id=video_id,
                    scene_id=_obj(s, "id"),
                    orientation=orientation,
                ):
                    queued_upscales += 1

        msg = f"Queued {queued_videos}/{len(pending_videos)} scene video requests."
        if queued_images > 0:
            msg += f" Also queued {queued_images}/{len(pending_images)} image requests for remaining scenes."
        if waiting_images:
            msg += f" {len(waiting_images)} scene(s) still waiting for image before video."
        if body.include_upscale:
            msg += f" Queued {queued_upscales} upscale request(s) for scenes that already have video."
        if tts_started:
            msg += " Triggered TTS in parallel."
        requested: list[str] = []
        if queued_videos > 0:
            requested.append("GENERATE_VIDEO")
        if queued_images > 0:
            requested.append("GENERATE_IMAGE")
        if queued_upscales > 0:
            requested.append("UPSCALE_VIDEO_LOCAL")
        if tts_started:
            requested.append("TTS_NARRATE")
        return SmartContinueResponse(
            project_id=project_id,
            video_id=video_id,
            orientation=orientation,
            action=(
                "queue_images_videos_upscale"
                if queued_images > 0 and queued_upscales > 0
                else "queue_videos_upscale"
                if queued_upscales > 0
                else "queue_images_and_videos"
                if queued_images > 0
                else "queue_videos"
            ),
            message=msg,
            queued_requests=queued_videos + queued_images + queued_upscales,
            requested_types=requested,
        )

    if queued_images > 0:
        return SmartContinueResponse(
            project_id=project_id,
            video_id=video_id,
            orientation=orientation,
            action="queue_images",
            message=f"Queued {queued_images}/{len(pending_images)} scene image requests. No scenes are image-ready for video yet.",
            queued_requests=queued_images,
            requested_types=["GENERATE_IMAGE"],
        )

    # Stage 2.5: review before upscale
    if body.include_upscale and body.review_before_upscale:
        try:
            review = await review_video(
                video_id,
                project_id,
                mode=body.review_mode,
                orientation=orientation,
            )
        except Exception as e:
            raise HTTPException(500, f"Review failed: {e}")

        failed_reviews = sorted(
            [sr for sr in review.scene_reviews if sr.overall_score < body.review_threshold],
            key=lambda sr: sr.overall_score,
        )
        if failed_reviews:
            queued = 0
            req_types: list[str] = []
            reviewed_scene_by_id = {str(_obj(s, "id")): s for s in scenes}
            for sr in failed_reviews[: body.max_review_regens]:
                scene_id = str(sr.scene_id)
                scene = reviewed_scene_by_id.get(scene_id)
                if not scene:
                    continue

                fix = (sr.fix_guide or "").strip()
                current_video_prompt = (_obj(scene, "video_prompt") or "").strip()
                if fix:
                    marker = f"[REVIEW FIX] {fix}"
                    if marker.lower() not in current_video_prompt.lower():
                        next_video_prompt = f"{current_video_prompt}\n{marker}".strip() if current_video_prompt else marker
                        await _repo.update("scene", scene_id, video_prompt=next_video_prompt)

                req_type = (
                    "REGENERATE_IMAGE"
                    if sr.overall_score < body.low_score_regen_image_threshold or bool(getattr(sr, "has_critical_errors", False))
                    else "REGENERATE_VIDEO"
                )
                if await _enqueue_request_if_needed(
                    req_type=req_type,
                    project_id=project_id,
                    video_id=video_id,
                    scene_id=scene_id,
                    orientation=orientation,
                ):
                    queued += 1
                    req_types.append(req_type)

            return SmartContinueResponse(
                project_id=project_id,
                video_id=video_id,
                orientation=orientation,
                action="review_regen",
                message=(
                    f"Review found {len(failed_reviews)} scene(s) below {body.review_threshold:.1f}. "
                    f"Queued {queued} regen request(s)."
                ),
                queued_requests=queued,
                requested_types=sorted(set(req_types)),
                review={
                    "mode": body.review_mode,
                    "threshold": body.review_threshold,
                    "overall_score": review.overall_score,
                    "failed_count": len(failed_reviews),
                    "failed_scene_ids": [str(r.scene_id) for r in failed_reviews],
                },
            )

    # Stage 3: upscale
    upscales_pending = [
        s
        for s in scenes
        if _obj(s, f"{prefix}_upscale_status") != "COMPLETED"
        and _obj(s, f"{prefix}_video_media_id")
    ]
    if body.include_upscale and upscales_pending:
        tts_started = await _maybe_tts()
        queued = 0
        for s in upscales_pending:
            if await _enqueue_request_if_needed(
                req_type="UPSCALE_VIDEO_LOCAL",
                project_id=project_id,
                video_id=video_id,
                scene_id=_obj(s, "id"),
                orientation=orientation,
            ):
                queued += 1
        msg = f"Queued {queued}/{len(upscales_pending)} upscale request(s)."
        if tts_started:
            msg += " Triggered TTS in parallel."
        requested = ["UPSCALE_VIDEO_LOCAL"] if queued > 0 else []
        if tts_started:
            requested.append("TTS_NARRATE")
        return SmartContinueResponse(
            project_id=project_id,
            video_id=video_id,
            orientation=orientation,
            action="queue_upscale",
            message=msg,
            queued_requests=queued,
            requested_types=requested,
        )

    # Optional rolling downloads
    downloaded_meta: Optional[dict[str, int]] = None
    if body.auto_download_upscales and body.include_upscale:
        dl = await download_upscales(
            video_id,
            DownloadUpscalesRequest(
                project_id=project_id,
                orientation=orientation,
                overwrite=False,
            ),
        )
        downloaded_meta = {
            "downloaded": len(dl.downloaded),
            "skipped": len(dl.skipped),
            "failed": len(dl.failed),
        }
        # refresh local download count after potential new downloads
        downloads_done = sum(
            1
            for s in scenes
            if resolve_4k_file(project_slug, int(_obj(s, "display_order", 0)), _obj(s, "id")) is not None
        )

    # Optional concat when fully ready
    if body.include_concat:
        upscale_ready = (not body.include_upscale) or all(
            _obj(s, f"{prefix}_upscale_status") == "COMPLETED" for s in scenes
        )
        tts_ready = (not body.include_tts) or (tts_total == 0) or (tts_done >= tts_total)
        downloads_ready = (not body.include_upscale) or (not body.auto_download_upscales) or (downloads_done >= scenes_total)
        if upscale_ready and tts_ready and downloads_ready:
            from agent.api.videos import ConcatRequest, concat_video

            concat_res = await concat_video(
                video_id,
                ConcatRequest(
                    project_id=project_id,
                    orientation=orientation,
                    with_narrator=True,
                    with_music=False,
                    fit_narrator=body.fit_narrator,
                    narrator_buffer=body.narrator_buffer,
                ),
            )
            return SmartContinueResponse(
                project_id=project_id,
                video_id=video_id,
                orientation=orientation,
                action="concat_done",
                message="Pipeline completed and concat finished.",
                concat_output=str(concat_res.output_path),
                downloaded=downloaded_meta,
            )
        return SmartContinueResponse(
            project_id=project_id,
            video_id=video_id,
            orientation=orientation,
            action="wait_concat",
            message=(
                f"Waiting before concat (upscale_ready={upscale_ready}, "
                f"tts_ready={tts_ready}, downloads_ready={downloads_ready})."
            ),
            downloaded=downloaded_meta,
        )

    # No further stages
    tts_started = await _maybe_tts()
    return SmartContinueResponse(
        project_id=project_id,
        video_id=video_id,
        orientation=orientation,
        action="completed",
        message="No pending stages detected for current settings." + (" TTS triggered." if tts_started else ""),
        requested_types=["TTS_NARRATE"] if tts_started else [],
        downloaded=downloaded_meta,
    )
