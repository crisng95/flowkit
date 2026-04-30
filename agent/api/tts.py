"""FastAPI router for TTS (text-to-speech) endpoints."""
import asyncio
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

from agent.config import TTS_TEMPLATES_DIR, SHARED_OUTPUT_DIR, OUTPUT_DIR
from agent.utils.slugify import slugify
from agent.db.crud import get_video, list_scenes, get_project
from agent.models.tts import (
    TTSGenerateRequest,
    TTSGenerateResponse,
    TTSSettingsResponse,
    TTSSettingsUpdateRequest,
    TTSCatalogResponse,
    NarrateVideoRequest,
    NarrateVideoResponse,
    SceneNarrationResult,
    VoiceTemplateRequest,
    VoiceTemplateImportRequest,
    VoiceTemplateResponse,
    VoiceTemplateListItem,
)
from agent.services.tts import generate_speech, generate_video_narration
from agent.services.tts_catalog import load_tts_catalog
from agent.services.post_process import add_narration
from agent.services.tts_settings import get_tts_settings_public, update_tts_settings
from agent.utils.orientation import normalize_orientation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tts"])

TEMPLATES_DIR = TTS_TEMPLATES_DIR
TEMPLATES_META = TEMPLATES_DIR / "templates.json"

# Semaphore: max 2 concurrent TTS generations to prevent resource abuse
_TTS_SEMAPHORE = asyncio.Semaphore(2)

# Allowed base directories for ref_audio paths
_ALLOWED_REF_AUDIO_DIRS = [SHARED_OUTPUT_DIR, OUTPUT_DIR]

_TEMPLATE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

MAX_NARRATE_SCENES = 100


def _validate_template_name(name: str) -> None:
    """Raise 400 if template name contains invalid characters."""
    if not _TEMPLATE_NAME_RE.match(name):
        raise HTTPException(400, "Invalid template name: use alphanumeric, hyphens, underscores only (max 64 chars)")


def _validate_ref_audio(ref_audio: str) -> None:
    """Raise 400 if ref_audio path is outside allowed directories."""
    try:
        resolved = Path(ref_audio).resolve()
    except Exception:
        raise HTTPException(400, "Invalid ref_audio path")

    allowed = [d.resolve() for d in _ALLOWED_REF_AUDIO_DIRS]
    try:
        allowed.append(TEMPLATES_DIR.resolve())
    except Exception:
        pass

    if not any(resolved.is_relative_to(d) for d in allowed):
        raise HTTPException(400, "ref_audio must be within allowed directories")


@router.get("/tts/settings", response_model=TTSSettingsResponse)
async def get_tts_settings():
    """Get current TTS provider settings (public-safe fields)."""
    return TTSSettingsResponse(**get_tts_settings_public())


@router.patch("/tts/settings", response_model=TTSSettingsResponse)
async def patch_tts_settings(body: TTSSettingsUpdateRequest):
    """Update TTS provider settings."""
    update_tts_settings(
        provider=body.provider,
        elevenlabs_api_base=body.elevenlabs_api_base,
        elevenlabs_api_key=body.elevenlabs_api_key,
        clear_elevenlabs_api_key=body.clear_elevenlabs_api_key,
        elevenlabs_model_id=body.elevenlabs_model_id,
        elevenlabs_default_voice_id=body.elevenlabs_default_voice_id,
        elevenlabs_timeout_sec=body.elevenlabs_timeout_sec,
        elevenlabs_max_retries=body.elevenlabs_max_retries,
    )
    return TTSSettingsResponse(**get_tts_settings_public())


@router.get("/tts/catalog", response_model=TTSCatalogResponse)
async def get_tts_catalog(refresh: bool = False):
    """Get provider catalog for UI dropdowns (models + voices)."""
    data = await load_tts_catalog(force_refresh=bool(refresh))
    return TTSCatalogResponse(**data)


@router.post("/tts/generate", response_model=TTSGenerateResponse)
async def tts_generate(body: TTSGenerateRequest):
    """Generate speech for a single text string. Returns path to WAV file."""
    if body.ref_audio:
        _validate_ref_audio(body.ref_audio)

    SHARED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    import uuid as _uuid
    out_path = str(SHARED_OUTPUT_DIR / f"{_uuid.uuid4()}.wav")

    async with _TTS_SEMAPHORE:
        try:
            audio_path = await generate_speech(
                text=body.text,
                output_path=out_path,
                instruct=body.instruct,
                ref_audio=body.ref_audio,
                ref_text=body.ref_text,
                speed=body.speed,
                voice_id=body.voice_id,
                model_id=body.model_id,
            )
        except Exception as e:
            logger.exception("TTS generation failed")
            raise HTTPException(500, str(e) or "TTS generation failed")

    duration = _wav_duration(audio_path)
    return TTSGenerateResponse(audio_path=audio_path, duration=duration)


@router.post("/videos/{vid}/narrate", response_model=NarrateVideoResponse)
async def narrate_video(vid: str, body: NarrateVideoRequest):
    """Generate narration WAVs for all scenes in a video and optionally mix into video files."""
    if body.ref_audio:
        _validate_ref_audio(body.ref_audio)

    video = await get_video(vid)
    if not video:
        raise HTTPException(404, "Video not found")

    project = await get_project(body.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    scenes = await list_scenes(vid)
    if not scenes:
        raise HTTPException(404, "No scenes found for video")

    # Filter by scene range if specified
    if body.from_scene is not None or body.to_scene is not None:
        lo = body.from_scene if body.from_scene is not None else 0
        hi = body.to_scene if body.to_scene is not None else float("inf")
        scenes = [s for s in scenes if lo <= s.get("display_order", 0) <= hi]
        if not scenes:
            raise HTTPException(404, f"No scenes in range {lo}-{hi}")
        logger.info("Filtered to scenes %d-%d (%d scenes)", lo, int(hi), len(scenes))

    # Check batch size cap
    scenes_with_text = [s for s in scenes if s.get("narrator_text")]
    if len(scenes_with_text) > MAX_NARRATE_SCENES:
        raise HTTPException(400, f"Too many scenes with narrator_text: max {MAX_NARRATE_SCENES}, got {len(scenes_with_text)}")

    # Resolve voice template by name if provided
    instruct = body.instruct or project.get("narrator_voice")
    ref_audio = body.ref_audio or project.get("narrator_ref_audio")
    ref_text = body.ref_text
    voice_id = body.voice_id
    model_id = body.model_id

    if body.template:
        meta = _load_templates_meta()
        if body.template not in meta:
            raise HTTPException(404, f"Voice template '{body.template}' not found")
        tmpl = meta[body.template]
        ref_audio = tmpl["audio_path"]
        ref_text = tmpl.get("text")
        if not voice_id:
            voice_id = tmpl.get("voice_id")
        if not model_id:
            model_id = tmpl.get("model_id")
        logger.info("Using voice template '%s' as reference", body.template)
    elif ref_audio and not ref_text:
        # Try to auto-resolve ref_text from template metadata
        meta = _load_templates_meta()
        for tmpl in meta.values():
            if tmpl["audio_path"] == ref_audio:
                ref_text = tmpl.get("text")
                if not voice_id:
                    voice_id = tmpl.get("voice_id")
                if not model_id:
                    model_id = tmpl.get("model_id")
                logger.info("Auto-resolved ref_text from template '%s'", tmpl["name"])
                break

    project_name = project.get("name") or "unnamed_project"
    project_slug = slugify(project_name)
    out_dir = OUTPUT_DIR / project_slug / "tts"
    out_dir.mkdir(parents=True, exist_ok=True)
    narrated_dir = OUTPUT_DIR / project_slug / "narrated"
    narrated_dir.mkdir(parents=True, exist_ok=True)

    async with _TTS_SEMAPHORE:
        raw_results = await generate_video_narration(
            scenes=scenes,
            output_dir=str(out_dir),
            instruct=instruct,
            ref_audio=ref_audio,
            ref_text=ref_text,
            speed=body.speed,
            voice_id=voice_id,
            model_id=model_id,
        )

    orientation = normalize_orientation(body.orientation)

    scene_results = []
    for r in raw_results:
        result = SceneNarrationResult(
            scene_id=r["scene_id"],
            display_order=r["display_order"],
            narrator_text=r.get("narrator_text"),
            audio_path=r.get("audio_path"),
            duration=r.get("duration"),
            status=r["status"],
            error=r.get("error"),
        )

        # Mix narration into video if requested and both files exist
        if body.mix and r["status"] == "COMPLETED" and r.get("audio_path"):
            scene_data = next((s for s in scenes if s["id"] == r["scene_id"]), None)
            if scene_data:
                video_url_key = f"{orientation.lower()}_video_url"
                video_path = scene_data.get(video_url_key)
                if video_path and Path(video_path).exists():
                    mixed_path = str(narrated_dir / f"scene_{r['display_order']:03d}_{r['scene_id']}_mixed.mp4")
                    ok = add_narration(
                        video_path=video_path,
                        narration_path=r["audio_path"],
                        output_path=mixed_path,
                        sfx_volume=body.sfx_volume,
                    )
                    if ok:
                        logger.info("Mixed narration for scene %s -> %s", r["scene_id"], mixed_path)
                    else:
                        logger.warning("Narration mix failed for scene %s", r["scene_id"])

        scene_results.append(result)

    scenes_narrated = sum(1 for r in scene_results if r.status == "COMPLETED")
    scenes_skipped = sum(1 for r in scene_results if r.status == "SKIPPED")
    scenes_failed = sum(1 for r in scene_results if r.status == "FAILED")
    total_duration = sum(r.duration for r in scene_results if r.duration is not None) or None

    return NarrateVideoResponse(
        video_id=vid,
        project_id=body.project_id,
        scenes=scene_results,
        scenes_narrated=scenes_narrated,
        scenes_skipped=scenes_skipped,
        scenes_failed=scenes_failed,
        total_narration_duration=total_duration,
    )


@router.post("/tts/templates", response_model=VoiceTemplateResponse)
async def create_voice_template(body: VoiceTemplateRequest):
    """Generate and save a voice template for consistent narration."""
    # name already validated by Pydantic pattern — double-check here for defense-in-depth
    _validate_template_name(body.name)

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = str(TEMPLATES_DIR / f"{body.name}.wav")

    async with _TTS_SEMAPHORE:
        try:
            await generate_speech(
                text=body.text,
                output_path=wav_path,
                instruct=body.instruct,
                speed=body.speed,
                voice_id=body.voice_id,
                model_id=body.model_id,
            )
        except Exception as e:
            logger.exception("Voice template generation failed")
            raise HTTPException(500, str(e) or "Voice template generation failed")

    duration = _wav_duration(wav_path)

    # Save metadata
    meta = _load_templates_meta()
    meta[body.name] = {
        "name": body.name,
        "audio_path": wav_path,
        "text": body.text,
        "instruct": body.instruct,
        "voice_id": body.voice_id or "",
        "model_id": body.model_id or "",
        "duration": duration,
    }
    _save_templates_meta(meta)

    return VoiceTemplateResponse(
        name=body.name, audio_path=wav_path, text=body.text,
        instruct=body.instruct, voice_id=body.voice_id, model_id=body.model_id, duration=duration,
    )


@router.post("/tts/templates/import", response_model=VoiceTemplateResponse)
async def import_voice_template(body: VoiceTemplateImportRequest):
    """Import an existing local audio file as a template (fk:import-voice parity)."""
    _validate_template_name(body.name)

    src = Path(body.audio_path).expanduser().resolve()
    if not src.exists():
        raise HTTPException(404, f"Audio file not found: {body.audio_path}")
    if not src.is_file():
        raise HTTPException(400, "audio_path must be a file")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    target = (TEMPLATES_DIR / f"{body.name}.wav").resolve()

    # Import strategy:
    # - copy WAV directly when allowed
    # - otherwise transcode to 24k WAV for OmniVoice compatibility
    if src.suffix.lower() == ".wav" and body.copy_audio:
        try:
            shutil.copyfile(src, target)
        except Exception as e:
            logger.exception("Failed to copy template audio")
            raise HTTPException(500, f"Failed to import template audio: {e}")
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(target),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except Exception as e:
            raise HTTPException(500, f"ffmpeg failed while importing voice template: {e}")
        if result.returncode != 0:
            logger.error("ffmpeg import failed: %s", (result.stderr or "")[-400:])
            raise HTTPException(500, "Failed to convert audio to WAV for template import")

    duration = _wav_duration(str(target))
    meta = _load_templates_meta()
    meta[body.name] = {
        "name": body.name,
        "audio_path": str(target),
        "text": body.text,
        "instruct": body.instruct,
        "voice_id": body.voice_id or "",
        "model_id": body.model_id or "",
        "duration": duration,
    }
    _save_templates_meta(meta)

    return VoiceTemplateResponse(
        name=body.name,
        audio_path=str(target),
        text=body.text,
        instruct=body.instruct,
        voice_id=body.voice_id,
        model_id=body.model_id,
        duration=duration,
    )


@router.get("/tts/templates", response_model=list[VoiceTemplateListItem])
async def list_voice_templates():
    """List all saved voice templates."""
    meta = _load_templates_meta()
    return [
        VoiceTemplateListItem(
            name=v["name"],
            audio_path=v["audio_path"],
            voice_id=v.get("voice_id"),
            model_id=v.get("model_id"),
            duration=v.get("duration"),
        )
        for v in meta.values()
    ]


@router.get("/tts/templates/{name}", response_model=VoiceTemplateResponse)
async def get_voice_template(name: str):
    """Get a voice template by name."""
    _validate_template_name(name)
    meta = _load_templates_meta()
    if name not in meta:
        raise HTTPException(404, f"Voice template '{name}' not found")
    v = meta[name]
    return VoiceTemplateResponse(**v)


@router.delete("/tts/templates/{name}")
async def delete_voice_template(name: str):
    """Delete a voice template."""
    _validate_template_name(name)
    meta = _load_templates_meta()
    if name not in meta:
        raise HTTPException(404, f"Voice template '{name}' not found")
    wav = Path(meta[name]["audio_path"]).resolve()
    # Verify resolved path is within TEMPLATES_DIR before deletion
    if not wav.is_relative_to(TEMPLATES_DIR.resolve()):
        logger.warning("Attempted deletion outside TEMPLATES_DIR: %s", wav)
        raise HTTPException(400, "Invalid template path")
    if wav.exists():
        wav.unlink()
    del meta[name]
    _save_templates_meta(meta)
    return {"ok": True}


def _load_templates_meta() -> dict:
    if TEMPLATES_META.exists():
        return json.loads(TEMPLATES_META.read_text())
    return {}


def _save_templates_meta(meta: dict):
    TEMPLATES_META.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_META.write_text(json.dumps(meta, indent=2, ensure_ascii=False))


def _wav_duration(path: str) -> float | None:
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return None
