"""Persistent settings for TTS providers (ElevenLabs / OmniVoice)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.config import (
    TTS_SETTINGS_PATH,
    TTS_PROVIDER,
    ELEVENLABS_API_KEY,
    ELEVENLABS_MODEL_ID,
    ELEVENLABS_DEFAULT_VOICE_ID,
    ELEVENLABS_TIMEOUT_SEC,
    ELEVENLABS_MAX_RETRIES,
    ELEVENLABS_API_BASE,
)

_ALLOWED_PROVIDERS = {"elevenlabs", "omnivoice"}


def _defaults() -> dict[str, Any]:
    provider = (TTS_PROVIDER or "elevenlabs").strip().lower()
    if provider not in _ALLOWED_PROVIDERS:
        provider = "elevenlabs"
    return {
        "provider": provider,
        "elevenlabs_api_base": ELEVENLABS_API_BASE,
        "elevenlabs_api_key": ELEVENLABS_API_KEY,
        "elevenlabs_model_id": ELEVENLABS_MODEL_ID or "eleven_multilingual_v2",
        "elevenlabs_default_voice_id": ELEVENLABS_DEFAULT_VOICE_ID,
        "elevenlabs_timeout_sec": max(5.0, float(ELEVENLABS_TIMEOUT_SEC or 60)),
        "elevenlabs_max_retries": max(0, int(ELEVENLABS_MAX_RETRIES or 2)),
    }


def _read_raw_file() -> dict[str, Any]:
    path = Path(TTS_SETTINGS_PATH)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
        if isinstance(raw, dict):
            return raw
    except Exception:
        return {}
    return {}


def _write_raw_file(data: dict[str, Any]) -> None:
    path = Path(TTS_SETTINGS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _normalize_provider(value: Any) -> str:
    provider = str(value or "").strip().lower()
    return provider if provider in _ALLOWED_PROVIDERS else "elevenlabs"


def _normalize_base_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ELEVENLABS_API_BASE
    return raw.rstrip("/")


def _normalize_float(value: Any, default: float, minimum: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(minimum, parsed)


def _normalize_int(value: Any, default: int, minimum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(minimum, parsed)


def _normalize(settings: dict[str, Any]) -> dict[str, Any]:
    defaults = _defaults()
    normalized = {
        "provider": _normalize_provider(settings.get("provider", defaults["provider"])),
        "elevenlabs_api_base": _normalize_base_url(settings.get("elevenlabs_api_base", defaults["elevenlabs_api_base"])),
        "elevenlabs_api_key": str(settings.get("elevenlabs_api_key", defaults["elevenlabs_api_key"]) or "").strip(),
        "elevenlabs_model_id": str(settings.get("elevenlabs_model_id", defaults["elevenlabs_model_id"]) or "").strip() or "eleven_multilingual_v2",
        "elevenlabs_default_voice_id": str(settings.get("elevenlabs_default_voice_id", defaults["elevenlabs_default_voice_id"]) or "").strip(),
        "elevenlabs_timeout_sec": _normalize_float(
            settings.get("elevenlabs_timeout_sec", defaults["elevenlabs_timeout_sec"]),
            float(defaults["elevenlabs_timeout_sec"]),
            5.0,
        ),
        "elevenlabs_max_retries": _normalize_int(
            settings.get("elevenlabs_max_retries", defaults["elevenlabs_max_retries"]),
            int(defaults["elevenlabs_max_retries"]),
            0,
        ),
    }
    return normalized


def get_tts_settings() -> dict[str, Any]:
    """Return effective settings (defaults + file overrides), including secret key."""
    defaults = _defaults()
    overrides = _read_raw_file()
    merged = {**defaults, **overrides}
    return _normalize(merged)


def update_tts_settings(
    *,
    provider: str | None = None,
    elevenlabs_api_base: str | None = None,
    elevenlabs_api_key: str | None = None,
    clear_elevenlabs_api_key: bool = False,
    elevenlabs_model_id: str | None = None,
    elevenlabs_default_voice_id: str | None = None,
    elevenlabs_timeout_sec: float | None = None,
    elevenlabs_max_retries: int | None = None,
) -> dict[str, Any]:
    """Update persisted settings and return normalized effective settings."""
    current = get_tts_settings()
    next_settings = dict(current)

    if provider is not None:
        next_settings["provider"] = provider
    if elevenlabs_api_base is not None:
        next_settings["elevenlabs_api_base"] = elevenlabs_api_base
    if clear_elevenlabs_api_key:
        next_settings["elevenlabs_api_key"] = ""
    elif elevenlabs_api_key is not None:
        next_settings["elevenlabs_api_key"] = elevenlabs_api_key
    if elevenlabs_model_id is not None:
        next_settings["elevenlabs_model_id"] = elevenlabs_model_id
    if elevenlabs_default_voice_id is not None:
        next_settings["elevenlabs_default_voice_id"] = elevenlabs_default_voice_id
    if elevenlabs_timeout_sec is not None:
        next_settings["elevenlabs_timeout_sec"] = elevenlabs_timeout_sec
    if elevenlabs_max_retries is not None:
        next_settings["elevenlabs_max_retries"] = elevenlabs_max_retries

    normalized = _normalize(next_settings)
    _write_raw_file(normalized)
    return normalized


def mask_secret(secret: str) -> str:
    token = (secret or "").strip()
    if not token:
        return ""
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"


def get_tts_settings_public() -> dict[str, Any]:
    settings = get_tts_settings()
    return {
        "provider": settings["provider"],
        "elevenlabs_api_base": settings["elevenlabs_api_base"],
        "elevenlabs_model_id": settings["elevenlabs_model_id"],
        "elevenlabs_default_voice_id": settings["elevenlabs_default_voice_id"],
        "elevenlabs_timeout_sec": settings["elevenlabs_timeout_sec"],
        "elevenlabs_max_retries": settings["elevenlabs_max_retries"],
        "elevenlabs_api_key_set": bool(settings["elevenlabs_api_key"]),
        "elevenlabs_api_key_masked": mask_secret(settings["elevenlabs_api_key"]),
    }

