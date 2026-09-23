"""What each AI CLI accepts, and which one a given role runs on.

Three CLIs back the vision work: Claude Code (`claude`), Google Antigravity
(`agy`) and OpenAI Codex (`codex`). They disagree about almost everything —
flag names, effort ladders, whether an unknown model slug is an error — so the
differences live here rather than being re-derived at each call site.

Config lives in `agent/providers.json`, hot-reloaded into `config.CLI_PROVIDERS`:

    {"active": "claude",
     "roles": {"video_review": {"provider": "agy", "model": null, "effort": "low"}}}

`active` predates `roles` and is still the fallback for any role without an
entry, so an old providers.json keeps working untouched.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from pathlib import Path

from agent import config

logger = logging.getLogger(__name__)


PROVIDER_BINARIES = {
    "claude": "claude",
    "agy": "agy",
    "codex": "codex",
}

# Reasoning-effort ladders, as each CLI actually accepts them. agy's own help
# spells out "(low|medium|high)" and it rejects anything outside that; claude
# and codex both take the longer ladder. Codex's real ladder is per-model
# (`supported_reasoning_levels` in its cache) — this is the union, and codex
# itself rejects a level its chosen model does not support.
PROVIDER_EFFORTS = {
    "claude": ("low", "medium", "high", "xhigh", "max"),
    "agy": ("low", "medium", "high"),
    "codex": ("low", "medium", "high", "xhigh", "max"),
}

# agy's model slugs carry the effort in them — gemini-3.8-flash-low,
# gemini-3.1-pro-high — so --model and --effort are not independent there.
# Verified against agy 1.2.7: a mismatched pair is rejected ("--model
# gpt-oss-120b-medium conflicts with --effort=low") and a model with no effort
# in its name rejects --effort outright ("--effort is not supported for model
# claude-sonnet-4-6"). Even a *matching* pair only restates the slug. So for
# agy, effort is what you set when you have NOT picked a model.
PROVIDER_MODEL_ENCODES_EFFORT = {
    "claude": False,
    "agy": True,
    "codex": False,
}

# Whether the catalog we can list is the whole truth. agy validates --model
# against `agy models` and errors out on anything else, so its list is closed.
# claude takes aliases (sonnet, opus) as well as full names, and codex takes
# slugs newer than whatever its on-disk cache happens to hold — for those two,
# an unlisted value is a legitimate escape hatch, not a typo to reject.
PROVIDER_CATALOG_IS_AUTHORITATIVE = {
    "claude": False,
    "agy": True,
    "codex": False,
}

# Claude Code resolves these aliases itself; full model names also work, which
# is why claude's catalog is not authoritative.
_CLAUDE_ALIASES = [
    {"id": "fable", "label": "Fable"},
    {"id": "opus", "label": "Opus"},
    {"id": "sonnet", "label": "Sonnet"},
    {"id": "haiku", "label": "Haiku"},
]

_CODEX_MODELS_CACHE = Path.home() / ".codex" / "models_cache.json"

# Roles are the jobs an AI CLI does for Flow Kit. One today; the shape is a map
# so adding the next one is a dict entry rather than a schema change.
ROLES = {
    "video_review": {
        "label": "Video Review",
        "description": "Vision analysis of contact sheets during scene video review",
    },
}

DEFAULT_PROVIDER = "claude"

_CATALOG_TTL_S = 300.0
# Unlocked on purpose. Two concurrent misses for the same provider both run the
# listing and the second overwrites the first with the same answer — a wasted
# subprocess, never a wrong result. A lock would cost more than it buys.
_catalog_cache: dict[str, tuple[float, list[dict]]] = {}


# ── role resolution ───────────────────────────────────────────


def resolve_role(role: str) -> dict:
    """Return {provider, model, effort} for `role`.

    Never raises and never returns an unusable provider: a role naming a
    provider we do not know, or an effort outside that provider's ladder, is
    logged and dropped rather than passed to a subprocess that would reject it
    several seconds later with a worse error.
    """
    cfg = config.CLI_PROVIDERS
    roles = cfg.get("roles") or {}
    entry = roles.get(role) or {}

    provider = entry.get("provider") or cfg.get("active") or DEFAULT_PROVIDER
    if provider not in PROVIDER_BINARIES:
        logger.warning(
            "Role %r names unknown provider %r — falling back to %s",
            role, provider, DEFAULT_PROVIDER,
        )
        provider = DEFAULT_PROVIDER

    effort = entry.get("effort") or None
    if effort and effort not in PROVIDER_EFFORTS[provider]:
        logger.warning(
            "Dropping effort %r for role %r — %s accepts %s",
            effort, role, provider, list(PROVIDER_EFFORTS[provider]),
        )
        effort = None

    model = entry.get("model") or None
    if model is not None and (not isinstance(model, str) or model.startswith("-")):
        # The API refuses these, but providers.json is documented as safe to
        # hand-edit, so the two paths have to agree on what is acceptable.
        logger.warning("Dropping unusable model %r for role %r", model, role)
        model = None

    return {"provider": provider, "model": model, "effort": effort}


async def validate_role_entry(role: str, entry: dict) -> dict:
    """Normalise one role entry from an API body. Raises ValueError on bad input.

    The model is checked against the catalog only where the catalog is closed
    (agy) — see PROVIDER_CATALOG_IS_AUTHORITATIVE. For claude and codex an
    unlisted slug is a legitimate escape hatch, not a typo.
    """
    if role not in ROLES:
        raise ValueError(f"Unknown role '{role}'. Known: {sorted(ROLES)}")
    if not isinstance(entry, dict):
        raise ValueError(f"Role '{role}' must be an object, got {type(entry).__name__}")

    provider = entry.get("provider")
    if provider not in PROVIDER_BINARIES:
        raise ValueError(
            f"Unknown provider '{provider}' for role '{role}'. Known: {sorted(PROVIDER_BINARIES)}"
        )
    if not shutil.which(PROVIDER_BINARIES[provider]):
        raise ValueError(
            f"'{PROVIDER_BINARIES[provider]}' binary not found on PATH — install it first"
        )

    effort = entry.get("effort") or None
    if effort is not None and effort not in PROVIDER_EFFORTS[provider]:
        raise ValueError(
            f"Effort '{effort}' is not supported by {provider}. "
            f"Supported: {list(PROVIDER_EFFORTS[provider])}"
        )

    model = entry.get("model") or None
    if model is not None and effort is not None and PROVIDER_MODEL_ENCODES_EFFORT[provider]:
        raise ValueError(
            f"{provider} encodes the effort in the model name, so '{model}' and "
            f"effort '{effort}' cannot both be set — pick one"
        )
    if model is not None and not isinstance(model, str):
        raise ValueError(f"Model for role '{role}' must be a string or null")
    if model is not None and model.startswith("-"):
        # The model is otherwise unvalidated for the open-catalog providers (the
        # escape hatch for a slug newer than any catalog), and it lands in argv
        # next to --model. No real slug starts with a dash, and refusing them
        # removes any argument left to have about what a CLI's parser does.
        raise ValueError(f"Model for role '{role}' must not start with '-'")

    if model is not None and PROVIDER_CATALOG_IS_AUTHORITATIVE[provider]:
        # agy validates --model itself and errors out several seconds into the
        # run. Catching it here is the difference between a 400 that names the
        # options and a failed review. An empty catalog means the listing call
        # failed, not that no models exist, so it must not block the write.
        known = await list_models(provider)
        if known and not any(m["id"] == model for m in known):
            raise ValueError(
                f"Unknown {provider} model '{model}'. {provider} rejects anything "
                f"outside its own catalog; known: {[m['id'] for m in known]}"
            )

    return {"provider": provider, "model": model, "effort": effort}


def current_roles() -> dict:
    """Every known role resolved, including ones absent from providers.json."""
    return {role: resolve_role(role) for role in ROLES}


# ── model catalogs ────────────────────────────────────────────


async def _list_agy_models() -> list[dict]:
    """Parse `agy models`, whose output is a header line then `<id>\\tLabel`."""
    proc = await asyncio.create_subprocess_exec(
        "agy", "models",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError("`agy models` timed out after 30s")
    if proc.returncode != 0:
        raise RuntimeError(f"`agy models` failed (rc={proc.returncode}): {stderr.decode()[-300:]}")

    models = []
    for line in stdout.decode().splitlines():
        # The first line is "Fetching available models..." — no tab, so it and
        # any other chatter drop out without needing to be named here.
        if "\t" not in line:
            continue
        slug, _, label = line.partition("\t")
        slug, label = slug.strip(), label.strip()
        if slug:
            models.append({"id": slug, "label": label or slug})
    return models


def _list_codex_models() -> list[dict]:
    """Read codex's own on-disk catalog.

    `codex models` is interactive — run headlessly it dies with "stdin is not
    a terminal" — so the cache the CLI maintains is the only listing available
    to a server process.
    """
    if not _CODEX_MODELS_CACHE.exists():
        return []
    with open(_CODEX_MODELS_CACHE, encoding="utf-8") as f:
        data = json.load(f)
    models = []
    for entry in data.get("models") or []:
        if not isinstance(entry, dict) or entry.get("visibility") != "list":
            continue
        slug = entry.get("slug")
        if not slug:
            continue
        efforts = [
            lvl.get("effort")
            for lvl in entry.get("supported_reasoning_levels") or []
            if isinstance(lvl, dict) and lvl.get("effort")
        ]
        models.append({
            "id": slug,
            "label": entry.get("display_name") or slug,
            "efforts": efforts,
        })
    return models


async def list_models(provider: str, force: bool = False) -> list[dict]:
    """Model catalog for `provider`, TTL-cached.

    An empty catalog is never cached: it means the binary was missing or the
    listing call failed, and both are transient in a way a real empty list is
    not.
    """
    if provider not in PROVIDER_BINARIES:
        raise ValueError(f"Unknown provider '{provider}'")

    now = time.monotonic()
    if not force:
        hit = _catalog_cache.get(provider)
        if hit and now - hit[0] < _CATALOG_TTL_S:
            return list(hit[1])

    if not shutil.which(PROVIDER_BINARIES[provider]):
        return []

    try:
        if provider == "agy":
            models = await _list_agy_models()
        elif provider == "codex":
            models = await asyncio.to_thread(_list_codex_models)
        else:
            models = list(_CLAUDE_ALIASES)
    except Exception as e:
        logger.warning("Model catalog for %s unavailable: %s", provider, e)
        return []

    if models:
        _catalog_cache[provider] = (now, models)
    # A copy: the cache is shared for five minutes and a caller that mutated
    # the list it got back would corrupt it for every later reader.
    return list(models)


def clear_catalog_cache() -> None:
    _catalog_cache.clear()
