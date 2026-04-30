"""Fetch runtime TTS catalog (models + voices) from ElevenLabs."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from agent.services.tts_settings import get_tts_settings

_CACHE_TTL_SEC = 60.0
_CACHE_LOCK = asyncio.Lock()
_CACHE_EXPIRES_AT = 0.0
_CACHE_KEY = ""
_CACHE_VALUE: dict[str, Any] | None = None

_FALLBACK_MODELS: list[dict[str, Any]] = [
    {
        "model_id": "eleven_multilingual_v2",
        "name": "Eleven Multilingual v2",
        "description": "High quality multilingual narration.",
        "language_count": 29,
    },
    {
        "model_id": "eleven_turbo_v2_5",
        "name": "Eleven Turbo v2.5",
        "description": "Fast generation with solid quality.",
        "language_count": 32,
    },
    {
        "model_id": "eleven_flash_v2_5",
        "name": "Eleven Flash v2.5",
        "description": "Ultra-low latency model.",
        "language_count": 32,
    },
    {
        "model_id": "eleven_english_v2",
        "name": "Eleven English v2",
        "description": "English-focused model.",
        "language_count": 1,
    },
]


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _parse_models(payload: Any) -> list[dict[str, Any]]:
    rows: list[Any] = []
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        raw = payload.get("models")
        if isinstance(raw, list):
            rows = raw

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = _safe_str(row.get("model_id") or row.get("id"))
        if not model_id:
            continue
        name = _safe_str(row.get("name")) or model_id
        desc = _safe_str(row.get("description"))
        languages_raw = row.get("languages")
        language_count = 0
        if isinstance(languages_raw, list):
            language_count = len(languages_raw)
        out.append(
            {
                "model_id": model_id,
                "name": name,
                "description": desc,
                "language_count": language_count,
            }
        )

    out.sort(key=lambda item: item["name"].lower())
    return out


def _parse_voices(payload: Any) -> list[dict[str, Any]]:
    rows: list[Any] = []
    if isinstance(payload, dict):
        raw = payload.get("voices")
        if isinstance(raw, list):
            rows = raw

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        voice_id = _safe_str(row.get("voice_id") or row.get("id"))
        if not voice_id:
            continue

        labels_raw = row.get("labels")
        labels: dict[str, str] = {}
        if isinstance(labels_raw, dict):
            for key, value in labels_raw.items():
                text = _safe_str(value)
                if text:
                    labels[str(key)] = text

        out.append(
            {
                "voice_id": voice_id,
                "name": _safe_str(row.get("name")) or voice_id,
                "category": _safe_str(row.get("category")),
                "preview_url": _safe_str(row.get("preview_url")) or None,
                "labels": labels,
            }
        )

    out.sort(key=lambda item: item["name"].lower())
    return out


def _source(models_api: bool, voices_api: bool) -> str:
    if models_api and voices_api:
        return "api"
    if models_api or voices_api:
        return "mixed"
    return "fallback"


async def _fetch_json(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> tuple[Any | None, str | None]:
    try:
        res = await client.get(url, headers=headers)
    except Exception as exc:  # pragma: no cover - network edge cases
        return None, str(exc)
    if res.status_code >= 400:
        body = (res.text or "").strip()
        msg = f"HTTP {res.status_code}"
        if body:
            msg = f"{msg}: {body[:220]}"
        return None, msg
    try:
        return res.json(), None
    except Exception:
        return None, "Invalid JSON response"


async def load_tts_catalog(*, force_refresh: bool = False) -> dict[str, Any]:
    settings = get_tts_settings()
    provider = _safe_str(settings.get("provider") or "elevenlabs").lower()

    if provider != "elevenlabs":
        return {
            "provider": provider if provider in {"elevenlabs", "omnivoice"} else "elevenlabs",
            "source": "fallback",
            "models": [],
            "voices": [],
            "warnings": ["Provider hiện tại không hỗ trợ catalog remote."],
        }

    api_base = _safe_str(settings.get("elevenlabs_api_base")) or "https://api.elevenlabs.io"
    api_key = _safe_str(settings.get("elevenlabs_api_key"))
    timeout_sec = max(5.0, float(settings.get("elevenlabs_timeout_sec") or 60.0))
    cache_key = f"{provider}|{api_base}|{api_key}"

    global _CACHE_EXPIRES_AT, _CACHE_KEY, _CACHE_VALUE
    now = time.time()
    if (
        not force_refresh
        and _CACHE_VALUE is not None
        and _CACHE_KEY == cache_key
        and now < _CACHE_EXPIRES_AT
    ):
        return dict(_CACHE_VALUE)

    warnings: list[str] = []
    headers = {"Accept": "application/json"}
    if api_key:
        headers["xi-api-key"] = api_key
    else:
        warnings.append("Chưa có ElevenLabs API key, không thể tải danh sách voice.")

    models = list(_FALLBACK_MODELS)
    voices: list[dict[str, Any]] = []
    models_from_api = False
    voices_from_api = False

    async with _CACHE_LOCK:
        # Double-check cache while waiting lock.
        now = time.time()
        if (
            not force_refresh
            and _CACHE_VALUE is not None
            and _CACHE_KEY == cache_key
            and now < _CACHE_EXPIRES_AT
        ):
            return dict(_CACHE_VALUE)

        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            if api_key:
                models_payload, models_err = await _fetch_json(client, f"{api_base.rstrip('/')}/v1/models", headers)
                if models_err:
                    warnings.append(f"Không tải được model list: {models_err}")
                else:
                    parsed_models = _parse_models(models_payload)
                    if parsed_models:
                        models = parsed_models
                        models_from_api = True
                    else:
                        warnings.append("Model list rỗng từ ElevenLabs, dùng fallback mặc định.")

                voices_payload, voices_err = await _fetch_json(client, f"{api_base.rstrip('/')}/v1/voices", headers)
                if voices_err:
                    warnings.append(f"Không tải được voice list: {voices_err}")
                else:
                    parsed_voices = _parse_voices(voices_payload)
                    if parsed_voices:
                        voices = parsed_voices
                        voices_from_api = True
                    else:
                        warnings.append("Voice list rỗng từ ElevenLabs.")

        payload = {
            "provider": "elevenlabs",
            "source": _source(models_from_api, voices_from_api),
            "models": models,
            "voices": voices,
            "warnings": warnings,
        }
        _CACHE_KEY = cache_key
        _CACHE_VALUE = dict(payload)
        _CACHE_EXPIRES_AT = time.time() + _CACHE_TTL_SEC
        return payload
