"""Gemini Omni Flash video generation through the Google Flow bridge.

Migrated ``flow.google.com`` batch surfaces live-verified on 2026-09-14:

* text -> video: ``YhhmEf`` + ``abra_t2v_<duration>s`` (workflow/media polling)
* first frame -> video: ``eb1hJf`` + ``abra_i2v_<duration>s``
* first + last frame -> video: ``nprQif`` + ``omni_flash_i2v_<duration>s_first_last``
* Ingredients/references -> video: ``MZZa6b`` + ``abra_r2v_<duration>s``

Reference-conditioned modes return normal batch operation receipts and use the
same operation/media poller as migrated Veo.

Duration-specific model keys live in ``agent/models.json`` so a rollout that
rotates a wire key does not need a code release.

Polling is workflow-backed: a submit hands back ``name`` + ``primaryMediaId``,
not an operation handle, so Omni jobs must not be fed to ``check_video_status``.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent.services import flow_batch as fb
from agent.services.flow_client import get_flow_client
from agent.services.flow_poll import check_workflow_status, extract_workflows

_MODELS_FILE = Path(__file__).parent.parent / "models.json"

OMNI_FLASH_VALID_DURATIONS = (4, 6, 8, 10)
OMNI_FLASH_VALID_ASPECTS = {
    "VIDEO_ASPECT_RATIO_PORTRAIT",
    "VIDEO_ASPECT_RATIO_LANDSCAPE",
}
OMNI_FLASH_MAX_REFERENCE_IMAGES = 7
# Informational only. Flow pricing can be promotional/variable.
OMNI_FLASH_CREDIT_COST = {4: 15, 6: 20, 8: 25, 10: 30}


def _validate_duration(duration_s: int) -> None:
    if duration_s not in OMNI_FLASH_VALID_DURATIONS:
        raise ValueError(
            f"Omni Flash duration {duration_s}s is unsupported; "
            f"choose one of {list(OMNI_FLASH_VALID_DURATIONS)}"
        )


def _validate_aspect(aspect_ratio: str) -> None:
    if aspect_ratio not in OMNI_FLASH_VALID_ASPECTS:
        raise ValueError(
            f"Omni Flash aspect ratio {aspect_ratio!r} is unsupported; "
            "use VIDEO_ASPECT_RATIO_PORTRAIT or VIDEO_ASPECT_RATIO_LANDSCAPE"
        )


def _validate_resolution(resolution: str) -> str:
    value = str(resolution or "720p").strip().lower()
    if value not in {"360p", "720p"}:
        raise ValueError("Omni Flash resolution must be 360p or 720p")
    return value


def _batch_operation_result(operation, project_id: str, model: str, duration_s: int, resolution: str) -> dict:
    pending = {
        "operation": {"name": operation.operation_id},
        "status": "MEDIA_GENERATION_STATUS_PENDING",
    }
    return {
        "status": 200,
        "data": {
            "operations": [pending],
            "model": model,
            "duration_s": duration_s,
            "resolution": resolution,
            "flowkitPolling": {
                "mode": "batch_operation",
                "project_id": project_id,
                "operations": [pending],
            },
        },
    }


def _load_model_key(duration_s: int, mode: str = "reference_to_video") -> str:
    """Resolve a configured Omni Flash model key for ``mode`` + duration."""
    _validate_duration(duration_s)

    with open(_MODELS_FILE, encoding="utf-8") as f:
        models = json.load(f)

    key = (
        models.get("omni_flash_models", {})
        .get(mode, {})
        .get(str(duration_s))
    )
    if not key:
        raise ValueError(
            f"No Omni Flash model key configured for mode {mode!r}, {duration_s}s"
        )
    return key


def _validate_reference_inputs(
    reference_media_ids: list[str],
    duration_s: int,
    aspect_ratio: str,
) -> list[str]:
    _validate_duration(duration_s)
    _validate_aspect(aspect_ratio)

    refs = [mid for mid in (reference_media_ids or []) if isinstance(mid, str) and mid]
    if not refs:
        raise ValueError("Omni Flash requires at least one reference image")
    if len(refs) > OMNI_FLASH_MAX_REFERENCE_IMAGES:
        raise ValueError(
            f"Omni Flash accepts at most {OMNI_FLASH_MAX_REFERENCE_IMAGES} reference images"
        )
    return refs


def _validate_frame_inputs(
    start_image_media_id: str,
    end_image_media_id: str | None,
    duration_s: int,
    aspect_ratio: str,
) -> None:
    _validate_duration(duration_s)
    _validate_aspect(aspect_ratio)
    if not isinstance(start_image_media_id, str) or not start_image_media_id:
        raise ValueError("Omni Flash first-frame generation requires start_image_media_id")
    if end_image_media_id is not None and (
        not isinstance(end_image_media_id, str) or not end_image_media_id
    ):
        raise ValueError("Omni Flash First+Last requires a non-empty end_image_media_id")


def extract_omni_workflows(result: dict) -> list[dict]:
    """Backward-compatible Omni name for the shared workflow extractor."""
    return extract_workflows(result)


async def generate_omni_flash_text_video(
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
    resolution: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit Omni 1.1 Flash text-to-video on the migrated Flow batch API."""
    _validate_duration(duration_s)
    resolution = _validate_resolution(resolution)
    _validate_aspect(aspect_ratio)
    client = get_flow_client()
    try:
        pid = client._batch_project_id(project_id)
        model_key = f"abra_t2v_{duration_s}s" + ("_360p" if resolution == "360p" else "")
        freq = fb.text_video_request(
            prompt,
            pid,
            aspect=aspect_ratio,
            model=model_key,
            resolution=resolution,
        )
        payload = await client._batch_payload(
            fb.RPC_GEN_VIDEO_TEXT, freq, fb.CAPTCHA_VIDEO, timeout=120)
        submitted = fb.read_text_video_submit(payload)
    except Exception as exc:
        return {"status": 502, "error": f"{type(exc).__name__}: {exc}"}

    media_id = submitted["media_id"]
    workflow = {
        "name": submitted.get("workflow_id") or media_id,
        "primary_media_id": media_id,
        "project_id": pid,
    }
    return {
        "status": 200,
        "data": {
            "media": [{"name": media_id}],
            "workflows": [workflow],
            "model": model_key,
            "duration_s": duration_s,
            "resolution": resolution,
            "flowkitPolling": {
                "mode": "batch_media",
                "project_id": pid,
                "workflows": [workflow],
            },
        },
    }


async def _submit_omni_frame_video(
    *,
    start_image_media_id: str,
    end_image_media_id: str | None,
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
    resolution: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit Omni first-frame or First+Last generation.

    Batch payloads were live-captured from ``flow.google.com`` on 2026-09-14:
    first-frame uses ``eb1hJf``; First+Last uses ``nprQif``. Both return normal
    batch operations and are polled through ``/api/flow/check-status``.
    """
    _validate_frame_inputs(start_image_media_id, end_image_media_id, duration_s, aspect_ratio)
    resolution = _validate_resolution(resolution)
    mode = "start_end_frame_to_video" if end_image_media_id is not None else "frame_to_video"
    client = get_flow_client()

    try:
        pid = client._batch_project_id(project_id)
        if end_image_media_id is None:
            freq = fb.omni_first_frame_request(
                prompt, pid, start_image_media_id, duration_s=duration_s,
                resolution=resolution, aspect=aspect_ratio,
            )
            rpcid = fb.RPC_GEN_VIDEO
            batch_model = f"abra_i2v_{duration_s}s" + ("_360p" if resolution == "360p" else "")
        else:
            freq = fb.omni_first_last_request(
                prompt, pid, start_image_media_id, end_image_media_id,
                duration_s=duration_s, resolution=resolution, aspect=aspect_ratio,
            )
            rpcid = fb.RPC_GEN_VIDEO_FIRST_LAST
            batch_model = f"omni_flash_i2v_{duration_s}s_first_last" + (
                "_360p" if resolution == "360p" else ""
            )
        payload = await client._batch_payload(
            rpcid, freq, fb.CAPTCHA_VIDEO, timeout=120,
        )
        operation = fb.read_operation(payload)
        client._remember_operation(operation.operation_id, pid)
    except Exception as exc:
        return {"status": 502, "error": f"{type(exc).__name__}: {exc}"}
    return _batch_operation_result(operation, pid, batch_model, duration_s, resolution)

async def generate_omni_flash_first_frame_video(
    start_image_media_id: str,
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
    resolution: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit Omni Flash First frame -> video."""
    return await _submit_omni_frame_video(
        start_image_media_id=start_image_media_id,
        end_image_media_id=None,
        prompt=prompt,
        project_id=project_id,
        scene_id=scene_id,
        duration_s=duration_s,
        resolution=resolution,
        aspect_ratio=aspect_ratio,
        user_paygate_tier=user_paygate_tier,
        seed=seed,
    )


async def generate_omni_flash_first_last_video(
    start_image_media_id: str,
    end_image_media_id: str,
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
    resolution: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit Omni Flash First + Last frame -> video."""
    return await _submit_omni_frame_video(
        start_image_media_id=start_image_media_id,
        end_image_media_id=end_image_media_id,
        prompt=prompt,
        project_id=project_id,
        scene_id=scene_id,
        duration_s=duration_s,
        resolution=resolution,
        aspect_ratio=aspect_ratio,
        user_paygate_tier=user_paygate_tier,
        seed=seed,
    )


async def generate_omni_flash_video(
    reference_media_ids: list[str],
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
    resolution: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit Omni Flash Ingredients/reference-to-video generation.

    The migrated UI uses RPC ``MZZa6b`` with ``abra_r2v_<duration>s`` (720p)
    or ``abra_r2v_<duration>s_360p``. Batch jobs use normal operation polling.
    """
    refs = _validate_reference_inputs(reference_media_ids, duration_s, aspect_ratio)
    resolution = _validate_resolution(resolution)
    client = get_flow_client()

    try:
        pid = client._batch_project_id(project_id)
        freq = fb.omni_reference_video_request(
            prompt, pid, refs, duration_s=duration_s,
            resolution=resolution, aspect=aspect_ratio,
        )
        payload = await client._batch_payload(
            fb.RPC_GEN_VIDEO_REFERENCES, freq, fb.CAPTCHA_VIDEO, timeout=120,
        )
        operation = fb.read_operation(payload)
        client._remember_operation(operation.operation_id, pid)
    except Exception as exc:
        return {"status": 502, "error": f"{type(exc).__name__}: {exc}"}
    batch_model = f"abra_r2v_{duration_s}s" + ("_360p" if resolution == "360p" else "")
    return _batch_operation_result(operation, pid, batch_model, duration_s, resolution)

async def check_omni_flash_status(
    workflows: list[dict],
    include_encoded_video: bool = False,
    project_id: str = "",
) -> dict:
    """Poll Omni text-to-video results using the same batch media resolver as exports."""
    return await check_workflow_status(
        workflows,
        mode="batch_media",
        include_encoded_video=include_encoded_video,
        project_id=project_id,
        client=get_flow_client(),
    )
