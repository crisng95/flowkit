"""TTS service layer.

Supports two providers:
- elevenlabs (default)
- omnivoice (legacy local model)
"""
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

import httpx

from agent.config import TTS_MODEL, TTS_SAMPLE_RATE
from agent.services.tts_settings import get_tts_settings

logger = logging.getLogger(__name__)

# Default to python3.10 (has torch/torchaudio/omnivoice); override with TTS_PYTHON_BIN if needed
PYTHON_BIN = os.environ.get("TTS_PYTHON_BIN", "python3.10")

# Inline script template for TTS generation via subprocess
_TTS_SCRIPT = """
import sys, json, torch, torchaudio

args = json.loads(sys.argv[1])
from omnivoice import OmniVoice

model = OmniVoice.from_pretrained(args["model"], device_map="cpu", dtype=torch.float32)

kwargs = {"text": args["text"]}
if args.get("ref_audio") and args.get("ref_text"):
    kwargs["ref_audio"] = args["ref_audio"]
    kwargs["ref_text"] = args["ref_text"]
elif args.get("instruct"):
    kwargs["instruct"] = args["instruct"]
if args.get("speed") and args["speed"] != 1.0:
    kwargs["speed"] = args["speed"]

audio = model.generate(**kwargs)
torchaudio.save(args["output"], audio[0], args["sample_rate"])
print(json.dumps({"ok": True, "path": args["output"]}))
"""

# Batch script — loads model once, generates for multiple texts
_TTS_BATCH_SCRIPT = """
import sys, json, torch, torchaudio
from pathlib import Path

args = json.loads(sys.argv[1])
from omnivoice import OmniVoice

model = OmniVoice.from_pretrained(args["model"], device_map="cpu", dtype=torch.float32)

results = []
for item in args["items"]:
    try:
        kwargs = {"text": item["text"]}
        if args.get("ref_audio") and args.get("ref_text"):
            kwargs["ref_audio"] = args["ref_audio"]
            kwargs["ref_text"] = args["ref_text"]
        elif args.get("instruct"):
            kwargs["instruct"] = args["instruct"]
        if args.get("speed") and args["speed"] != 1.0:
            kwargs["speed"] = args["speed"]

        audio = model.generate(**kwargs)
        Path(item["output"]).parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(item["output"], audio[0], args["sample_rate"])

        info = torchaudio.info(item["output"])
        duration = info.num_frames / info.sample_rate
        results.append({"id": item["id"], "ok": True, "path": item["output"], "duration": duration})
    except Exception as e:
        results.append({"id": item["id"], "ok": False, "error": str(e)})

print(json.dumps(results))
"""


def _tts_provider() -> str:
    settings = get_tts_settings()
    provider = str(settings.get("provider") or "elevenlabs").strip().lower()
    return provider if provider in {"elevenlabs", "omnivoice"} else "elevenlabs"


def _run_tts_subprocess(args: dict) -> dict:
    """Run OmniVoice TTS subprocess."""
    proc = subprocess.run(
        [PYTHON_BIN, "-c", _TTS_SCRIPT, json.dumps(args)],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr[-500:] if proc.stderr else "unknown error"}
    try:
        return json.loads(proc.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        return {"ok": False, "error": proc.stdout[-200:] + proc.stderr[-200:]}


def _run_batch_subprocess(args: dict) -> list[dict]:
    """Run OmniVoice batch subprocess. Model loads once."""
    timeout = 180 + len(args.get("items", [])) * 45  # ~180s model load + ~45s per scene
    proc = subprocess.run(
        [PYTHON_BIN, "-c", _TTS_BATCH_SCRIPT, json.dumps(args)],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        error = proc.stderr[-500:] if proc.stderr else "unknown"
        return [{"id": item["id"], "ok": False, "error": error} for item in args["items"]]
    try:
        return json.loads(proc.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        error = proc.stdout[-200:] + proc.stderr[-200:]
        return [{"id": item["id"], "ok": False, "error": error} for item in args["items"]]


def _ffprobe_duration(path: str) -> float | None:
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return None
        return float(proc.stdout.strip())
    except Exception:
        return None


def _atempo_filter(speed: float) -> str | None:
    if abs(speed - 1.0) < 1e-3:
        return None

    # ffmpeg atempo supports 0.5..2.0 per stage, so chain when needed.
    stages: list[float] = []
    remaining = float(speed)
    while remaining > 2.0:
        stages.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        stages.append(0.5)
        remaining /= 0.5
    stages.append(remaining)

    return ",".join(f"atempo={x:.4f}" for x in stages)


def _convert_audio_to_wav(src_path: Path, dst_path: Path, speed: float) -> bool:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src_path),
        "-ac",
        "1",
        "-ar",
        str(TTS_SAMPLE_RATE),
    ]
    speed_filter = _atempo_filter(speed)
    if speed_filter:
        cmd += ["-filter:a", speed_filter]
    cmd += ["-c:a", "pcm_s16le", str(dst_path)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            logger.error("ffmpeg convert failed: %s", (proc.stderr or "")[-400:])
            return False
    except Exception:
        logger.exception("ffmpeg convert raised exception")
        return False

    return dst_path.exists() and dst_path.stat().st_size > 1024


async def _generate_speech_omnivoice(
    text: str,
    output_path: str,
    instruct: Optional[str] = None,
    ref_audio: Optional[str] = None,
    ref_text: Optional[str] = None,
    speed: float = 1.0,
) -> str:
    args = {
        "model": TTS_MODEL,
        "text": text,
        "output": output_path,
        "sample_rate": TTS_SAMPLE_RATE,
        "speed": speed,
    }
    if instruct:
        args["instruct"] = instruct
    if ref_audio:
        args["ref_audio"] = ref_audio
    if ref_text:
        args["ref_text"] = ref_text

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_tts_subprocess, args)
    if not result.get("ok"):
        raise RuntimeError(f"OmniVoice TTS failed: {result.get('error', 'unknown')}")

    return output_path


async def _generate_speech_elevenlabs(
    text: str,
    output_path: str,
    speed: float = 1.0,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> str:
    settings = get_tts_settings()
    api_key = str(settings.get("elevenlabs_api_key") or "").strip()
    if not api_key:
        raise RuntimeError("ElevenLabs API key is not configured")

    resolved_voice = str(voice_id or settings.get("elevenlabs_default_voice_id") or "").strip()
    if not resolved_voice:
        raise RuntimeError("ElevenLabs voice_id is required (set default voice in TTS settings)")

    resolved_model = str(model_id or settings.get("elevenlabs_model_id") or "eleven_multilingual_v2").strip()
    base_url = str(settings.get("elevenlabs_api_base") or "https://api.elevenlabs.io").rstrip("/")
    timeout_sec = float(settings.get("elevenlabs_timeout_sec") or 60)
    max_retries = int(settings.get("elevenlabs_max_retries") or 2)

    url = f"{base_url}/v1/text-to-speech/{resolved_voice}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload: dict = {
        "text": text,
        "model_id": resolved_model,
    }

    response_bytes: bytes | None = None
    last_error: str = ""

    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        for attempt in range(max_retries + 1):
            try:
                res = await client.post(url, headers=headers, json=payload)
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    await asyncio.sleep(min(4.0, 1.0 + attempt))
                    continue
                raise RuntimeError(f"ElevenLabs request failed: {last_error}")

            if res.status_code == 429 and attempt < max_retries:
                await asyncio.sleep(min(5.0, 1.5 + attempt * 1.5))
                continue

            if res.status_code >= 400:
                err_text = (res.text or "").strip()
                if res.status_code in (401, 403):
                    raise RuntimeError(f"ElevenLabs auth failed ({res.status_code}). Check API key")
                if res.status_code == 429:
                    raise RuntimeError("ElevenLabs rate limit reached (429)")
                raise RuntimeError(f"ElevenLabs API error {res.status_code}: {err_text[:300]}")

            response_bytes = res.content
            break

    if not response_bytes:
        raise RuntimeError(f"ElevenLabs returned no audio bytes. Last error: {last_error or 'unknown'}")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_mp3 = out_path.with_suffix(f".tmp_{out_path.stem}.mp3")
    try:
        tmp_mp3.write_bytes(response_bytes)
        ok = _convert_audio_to_wav(tmp_mp3, out_path, speed)
        if not ok:
            raise RuntimeError("Failed to convert ElevenLabs audio to WAV")
    finally:
        try:
            if tmp_mp3.exists():
                tmp_mp3.unlink()
        except Exception:
            pass

    return output_path


async def generate_speech(
    text: str,
    output_path: str,
    instruct: Optional[str] = None,
    ref_audio: Optional[str] = None,
    ref_text: Optional[str] = None,
    speed: float = 1.0,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> str:
    """Generate speech for text. Returns path to WAV file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    provider = _tts_provider()
    if provider == "omnivoice":
        result = await _generate_speech_omnivoice(
            text=text,
            output_path=output_path,
            instruct=instruct,
            ref_audio=ref_audio,
            ref_text=ref_text,
            speed=speed,
        )
        logger.info("TTS saved to %s (provider=omnivoice)", output_path)
        return result

    result = await _generate_speech_elevenlabs(
        text=text,
        output_path=output_path,
        speed=speed,
        voice_id=voice_id,
        model_id=model_id,
    )
    logger.info("TTS saved to %s (provider=elevenlabs)", output_path)
    return result


async def generate_video_narration(
    scenes: list[dict],
    output_dir: str,
    instruct: Optional[str] = None,
    ref_audio: Optional[str] = None,
    ref_text: Optional[str] = None,
    speed: float = 1.0,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> list[dict]:
    """Generate narration WAVs for scenes with narrator_text.

    OmniVoice mode uses a batch subprocess for performance.
    ElevenLabs mode generates per scene (network API).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    items = []
    scene_map = {}
    for scene in scenes:
        scene_id = scene.get("id")
        display_order = scene.get("display_order", 0)
        narrator_text = scene.get("narrator_text")

        if not narrator_text:
            continue

        wav_path = str(out_dir / f"scene_{display_order:03d}_{scene_id}.wav")
        if Path(wav_path).exists() and Path(wav_path).stat().st_size > 1024:
            logger.info("Skipping scene %03d (WAV exists: %s)", display_order, wav_path)
            scene_map[scene_id] = {
                "display_order": display_order,
                "narrator_text": narrator_text,
                "skipped": True,
                "wav_path": wav_path,
            }
            continue
        items.append({"id": scene_id, "text": narrator_text, "output": wav_path})
        scene_map[scene_id] = {"display_order": display_order, "narrator_text": narrator_text}

    batch_results: dict[str, dict] = {}
    provider = _tts_provider()

    if items:
        if provider == "omnivoice":
            args = {
                "model": TTS_MODEL,
                "sample_rate": TTS_SAMPLE_RATE,
                "speed": speed,
                "items": items,
            }
            if instruct:
                args["instruct"] = instruct
            if ref_audio:
                args["ref_audio"] = ref_audio
            if ref_text:
                args["ref_text"] = ref_text

            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, _run_batch_subprocess, args)
            for r in raw:
                batch_results[r["id"]] = r
        else:
            for item in items:
                try:
                    await generate_speech(
                        text=item["text"],
                        output_path=item["output"],
                        instruct=instruct,
                        ref_audio=ref_audio,
                        ref_text=ref_text,
                        speed=speed,
                        voice_id=voice_id,
                        model_id=model_id,
                    )
                    batch_results[item["id"]] = {
                        "id": item["id"],
                        "ok": True,
                        "path": item["output"],
                        "duration": _ffprobe_duration(item["output"]),
                    }
                except Exception as e:
                    batch_results[item["id"]] = {
                        "id": item["id"],
                        "ok": False,
                        "error": str(e),
                    }

    results = []
    for scene in scenes:
        scene_id = scene.get("id")
        display_order = scene.get("display_order", 0)
        narrator_text = scene.get("narrator_text")

        if not narrator_text:
            results.append({
                "scene_id": scene_id,
                "display_order": display_order,
                "narrator_text": None,
                "audio_path": None,
                "duration": None,
                "status": "SKIPPED",
                "error": None,
            })
            continue

        sm = scene_map.get(scene_id, {})
        if sm.get("skipped"):
            results.append({
                "scene_id": scene_id,
                "display_order": display_order,
                "narrator_text": narrator_text,
                "audio_path": sm["wav_path"],
                "duration": _ffprobe_duration(sm["wav_path"]),
                "status": "COMPLETED",
                "error": None,
            })
            continue

        br = batch_results.get(scene_id, {})
        if br.get("ok"):
            results.append({
                "scene_id": scene_id,
                "display_order": display_order,
                "narrator_text": narrator_text,
                "audio_path": br.get("path"),
                "duration": br.get("duration"),
                "status": "COMPLETED",
                "error": None,
            })
        else:
            results.append({
                "scene_id": scene_id,
                "display_order": display_order,
                "narrator_text": narrator_text,
                "audio_path": None,
                "duration": None,
                "status": "FAILED",
                "error": br.get("error", "not processed"),
            })

    return results
