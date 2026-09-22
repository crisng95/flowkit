"""CLI provider config API — which AI CLI, model and effort each role runs on.

`active` is the legacy single-provider switch; `roles` is the per-role
configuration the dashboard edits. Every write here keeps the two consistent,
so neither reader sees a stale answer.

The only real consumer of `active` is `skills/fk-change-provider.md`
(`scripts/statusline.sh` does not read it — its `active` matches are the
unrelated `/api/active-project`). One reader is reason enough to keep the
field in step; it is not reason to grow more of them.
"""
import asyncio
import json
import logging
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from agent import config
from agent.services.cli_providers import (
    PROVIDER_BINARIES,
    PROVIDER_CATALOG_IS_AUTHORITATIVE,
    PROVIDER_EFFORTS,
    PROVIDER_MODEL_ENCODES_EFFORT,
    ROLES,
    current_roles,
    list_models,
    validate_role_entry,
)

router = APIRouter(prefix="/api/providers", tags=["providers"])
logger = logging.getLogger(__name__)
_PROVIDERS_FILE = Path(__file__).parent.parent / "providers.json"


def _read() -> dict:
    """Read providers.json from disk and refresh config.CLI_PROVIDERS in place.

    The file is the source of truth, and it is editable by hand (the skills
    do), so re-reading it here is what makes a hand edit take effect without a
    restart — and what stops a GET describing a state the worker is not in.
    """
    with open(_PROVIDERS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("active", "claude")
    data.setdefault("roles", {})
    # Same no-await-in-the-gap rule as _apply.
    config.CLI_PROVIDERS.clear()
    config.CLI_PROVIDERS.update(data)
    return data


def _write(data: dict):
    """Write atomically.

    `open(..., "w")` truncates in place, so a crash or a full disk mid-write
    leaves a truncated providers.json — which then 500s every request here and
    hard-fails `agent/config.py`'s import, so the server will not boot at all.
    That was survivable when this file changed on a rare provider switch; it is
    written on every dashboard settings change now.
    """
    tmp = _PROVIDERS_FILE.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _PROVIDERS_FILE)  # atomic within the same directory
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _apply(data: dict):
    """Persist and hot-reload. config.CLI_PROVIDERS is mutated, never rebound,
    because callers hold a reference to that same dict.

    The clear/update pair leaves a momentarily empty dict. That is safe only
    because no `await` separates the two lines: this runs on the event loop, so
    a concurrent `resolve_role` cannot be scheduled into the gap. Do not put an
    await between them — a review landing in that window would silently fall
    back to the default provider.
    """
    _write(data)
    config.CLI_PROVIDERS.clear()
    config.CLI_PROVIDERS.update(data)


async def _probe_version(binary: str) -> tuple:
    try:
        proc = await asyncio.create_subprocess_exec(
            binary, "--version",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        return proc.returncode == 0, None if proc.returncode == 0 else stderr.decode()[-200:]
    except Exception as e:
        return False, str(e)


@router.get("")
async def get_providers(live: bool = False):
    """Provider status plus the per-role configuration.

    `live=true` runs a real `<binary> --version` per provider, which costs a
    few seconds — it is opt-in for that reason, not the default.
    """
    data = _read()
    statuses = {}
    for name, binary in PROVIDER_BINARIES.items():
        installed = shutil.which(binary) is not None
        tested, error = (await _probe_version(binary)) if (live and installed) else (None, None)
        statuses[name] = {
            "binary": binary,
            "installed": installed,
            "tested": tested,
            "error": error,
            "efforts": list(PROVIDER_EFFORTS[name]),
            "default_model": None,
            "catalog_is_authoritative": PROVIDER_CATALOG_IS_AUTHORITATIVE[name],
            "model_encodes_effort": PROVIDER_MODEL_ENCODES_EFFORT[name],
        }
    return {
        "active": data["active"],
        "roles": current_roles(),
        "role_meta": ROLES,
        "providers": statuses,
    }


@router.get("/models")
async def get_provider_models(
    provider: str = Query(..., description="claude | agy | codex"),
    refresh: bool = Query(False, description="Bypass the 5-minute catalog cache"),
):
    """List a provider's models.

    An empty list is a normal answer, not an error: it means the binary is
    absent or the catalog call failed, and the caller should fall back to the
    provider's own default.
    """
    if provider not in PROVIDER_BINARIES:
        raise HTTPException(400, f"Unknown provider '{provider}'. Known: {sorted(PROVIDER_BINARIES)}")
    models = await list_models(provider, force=refresh)
    return {
        "provider": provider,
        "models": models,
        "authoritative": PROVIDER_CATALOG_IS_AUTHORITATIVE[provider],
    }


@router.patch("")
async def patch_providers(body: dict):
    """Update the active provider, the per-role config, or both.

    Body is either the legacy `{"active": "claude"}` or
    `{"roles": {"video_review": {"provider": ..., "model": ..., "effort": ...}}}`.
    """
    if not isinstance(body, dict) or ("active" not in body and "roles" not in body):
        raise HTTPException(400, "Body must contain 'active', 'roles', or both")

    data = _read()
    roles = dict(data.get("roles") or {})

    explicit = set()
    if "roles" in body:
        incoming = body["roles"]
        if not isinstance(incoming, dict):
            raise HTTPException(400, "'roles' must be an object keyed by role name")
        for role, entry in incoming.items():
            try:
                roles[role] = await validate_role_entry(role, entry)
            except ValueError as e:
                raise HTTPException(400, str(e))
        explicit = set(incoming)

    if "active" in body:
        provider = body["active"]
        if provider not in PROVIDER_BINARIES:
            raise HTTPException(400, f"Unknown provider '{provider}'. Known: {list(PROVIDER_BINARIES)}")
        if not shutil.which(PROVIDER_BINARIES[provider]):
            raise HTTPException(400, f"'{PROVIDER_BINARIES[provider]}' binary not found on PATH — install it first")
        data["active"] = provider
        # Switching the whole agent over has to carry the roles with it.
        # Only roles this build knows about. A name left behind by another
        # version (or a typo in a hand-edited file) is neither rewritten here
        # nor accepted by the `roles` path, which 400s on it — one policy for
        # both, rather than silently adopting it on one and rejecting it on the
        # other.
        for role in ROLES:
            if role in explicit:
                # The same request configured this role by name. That is the
                # more specific instruction and it already passed validation —
                # the sweep must not undo it.
                continue
            prev = roles.get(role) or {}
            # A model slug only survives if the CLI did not change: agy would
            # reject "sonnet" outright. Re-asserting the provider a role is
            # already on must not cost the user their model.
            model = prev.get("model") if prev.get("provider") == provider else None
            effort = prev.get("effort")
            if effort not in PROVIDER_EFFORTS[provider]:
                effort = None  # agy has no xhigh or max
            if model and effort and PROVIDER_MODEL_ENCODES_EFFORT[provider]:
                # Only reachable from a hand-edited file — the API refuses to
                # store the pair — but persisting it would fail the next review.
                effort = None
            roles[role] = {"provider": provider, "model": model, "effort": effort}

    data["roles"] = roles

    if "active" not in body and roles:
        # Keep the legacy field meaningful for /fk-change-provider: it reports
        # whatever the primary role runs on.
        primary = next(iter(ROLES))
        if primary in roles:
            data["active"] = roles[primary]["provider"]

    _apply(data)
    logger.info("Providers updated: active=%s roles=%s", data["active"], data["roles"])
    return {"status": "updated", "active": data["active"], "roles": data["roles"]}
