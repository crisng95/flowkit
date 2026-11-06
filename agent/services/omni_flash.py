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

_MODELS_FILE = Path(__file__).parent.parent / "models.json"

OMNI_FLASH_VALID_DURATIONS = (4, 6, 8, 10)
# Omni 1.2 Flash (Flow codename ``macaron_cookie``): any whole second 3-15.
# t2v / first+last keys live-captured from flow.google.com on 2026-11-06;
# first-frame (i2v) and Ingredients (r2v) follow the 1.1 naming by analogy.
OMNI_VERSIONS = ("1.1", "1.2")
OMNI_12_DURATIONS = tuple(range(3, 16))


def omni12_model_key(mode: str, duration_s: int, resolution: str) -> str:
    if duration_s not in OMNI_12_DURATIONS:
        raise ValueError(f"Omni 1.2 duration must be 3-15 seconds, got {duration_s}")
    stem = {"t2v": "t2v", "first_last": "i2v_fl", "first_frame": "i2v", "r2v": "r2v"}.get(mode)
    if stem is None:
        raise ValueError(
            f"Omni 1.2 mode {mode!r} is not captured yet; use omni_version='1.1'"
        )
    return f"macaron_cookie_{stem}_{duration_s}s" + ("_360p" if resolution == "360p" else "")
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


def _normalize_workflow(workflow: dict) -> dict | None:
    """Normalize a raw Flow workflow or FlowKit polling descriptor."""
    if not isinstance(workflow, dict):
        return None
    name = workflow.get("name")
    primary_media_id = workflow.get("primary_media_id")
    if not primary_media_id:
        metadata = workflow.get("metadata")
        if isinstance(metadata, dict):
            primary_media_id = metadata.get("primaryMediaId")
    if not isinstance(name, str) or not name:
        return None
    if not isinstance(primary_media_id, str) or not primary_media_id:
        return None
    item = {"name": name, "primary_media_id": primary_media_id}
    project_id = workflow.get("project_id") or workflow.get("projectId")
    if isinstance(project_id, str) and project_id:
        item["project_id"] = project_id
    return item


def extract_omni_workflows(result: dict) -> list[dict]:
    """Extract ``name`` + ``primaryMediaId`` pairs from an Omni submit."""
    if not isinstance(result, dict):
        return []
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    workflows = data.get("workflows", []) if isinstance(data, dict) else []
    normalized = []
    for workflow in workflows:
        item = _normalize_workflow(workflow)
        if item:
            normalized.append(item)
    return normalized


async def generate_omni_flash_text_video(
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
    resolution: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
    omni_version: str = "1.1",
) -> dict:
    """Submit Omni Flash text-to-video (1.1 ``abra`` or 1.2 ``macaron_cookie``)."""
    resolution = _validate_resolution(resolution)
    if omni_version == "1.2":
        model_key = omni12_model_key("t2v", duration_s, resolution)
    else:
        _validate_duration(duration_s)
        model_key = f"abra_t2v_{duration_s}s" + ("_360p" if resolution == "360p" else "")
    _validate_aspect(aspect_ratio)
    client = get_flow_client()
    try:
        pid = client._batch_project_id(project_id)
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
    omni_version: str = "1.1",
) -> dict:
    """Submit Omni first-frame or First+Last generation.

    Batch payloads were live-captured from ``flow.google.com`` on 2026-09-14:
    first-frame uses ``eb1hJf``; First+Last uses ``nprQif``. Both return normal
    batch operations and are polled through ``/api/flow/check-status``.
    """
    resolution = _validate_resolution(resolution)
    model_override = None
    if omni_version == "1.2":
        model_override = omni12_model_key(
            "first_last" if end_image_media_id is not None else "first_frame",
            duration_s, resolution,
        )
        _validate_frame_inputs(start_image_media_id, end_image_media_id, 4, aspect_ratio)
    else:
        _validate_frame_inputs(start_image_media_id, end_image_media_id, duration_s, aspect_ratio)
    mode = "start_end_frame_to_video" if end_image_media_id is not None else "frame_to_video"
    client = get_flow_client()

    try:
        pid = client._batch_project_id(project_id)
        if end_image_media_id is None:
            freq = fb.omni_first_frame_request(
                prompt, pid, start_image_media_id, duration_s=duration_s,
                resolution=resolution, aspect=aspect_ratio, model=model_override,
            )
            rpcid = fb.RPC_GEN_VIDEO
            batch_model = model_override or f"abra_i2v_{duration_s}s" + ("_360p" if resolution == "360p" else "")
        else:
            freq = fb.omni_first_last_request(
                prompt, pid, start_image_media_id, end_image_media_id,
                duration_s=duration_s, resolution=resolution, aspect=aspect_ratio,
                model=model_override,
            )
            rpcid = fb.RPC_GEN_VIDEO_FIRST_LAST
            batch_model = model_override or f"omni_flash_i2v_{duration_s}s_first_last" + (
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
    omni_version: str = "1.1",
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
        omni_version=omni_version,
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
    omni_version: str = "1.1",
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
        omni_version=omni_version,
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
    omni_version: str = "1.1",
) -> dict:
    """Submit Omni Flash Ingredients/reference-to-video generation.

    The migrated UI uses RPC ``MZZa6b`` with ``abra_r2v_<duration>s`` (720p)
    or ``abra_r2v_<duration>s_360p``. Batch jobs use normal operation polling.
    """
    resolution = _validate_resolution(resolution)
    model_override = None
    if omni_version == "1.2":
        model_override = omni12_model_key("r2v", duration_s, resolution)
        refs = _validate_reference_inputs(reference_media_ids, 4, aspect_ratio)
    else:
        refs = _validate_reference_inputs(reference_media_ids, duration_s, aspect_ratio)
    client = get_flow_client()

    try:
        pid = client._batch_project_id(project_id)
        freq = fb.omni_reference_video_request(
            prompt, pid, refs, duration_s=duration_s,
            resolution=resolution, aspect=aspect_ratio, model=model_override,
        )
        payload = await client._batch_payload(
            fb.RPC_GEN_VIDEO_REFERENCES, freq, fb.CAPTCHA_VIDEO, timeout=120,
        )
        operation = fb.read_operation(payload)
        client._remember_operation(operation.operation_id, pid)
    except Exception as exc:
        return {"status": 502, "error": f"{type(exc).__name__}: {exc}"}
    batch_model = model_override or f"abra_r2v_{duration_s}s" + ("_360p" if resolution == "360p" else "")
    return _batch_operation_result(operation, pid, batch_model, duration_s, resolution)

async def _check_omni_batch_media(
    workflows: list[dict],
    include_encoded_video: bool = False,
    project_id: str = "",
) -> dict:
    normalized = [item for workflow in (workflows or []) if (item := _normalize_workflow(workflow))]
    if not normalized:
        raise ValueError("Omni polling requires workflow descriptors with name and primary_media_id")
    resolved_project_id = project_id or next(
        (item.get("project_id", "") for item in normalized if item.get("project_id")), "")
    client = get_flow_client()
    items = []
    for workflow in normalized:
        media_id = workflow["primary_media_id"]
        response = await client.get_media(media_id)
        data = response.get("data") if isinstance(response, dict) else None
        video = data.get("video") if isinstance(data, dict) else None
        url = video.get("fifeUrl") if isinstance(video, dict) else None
        if isinstance(url, str) and url.startswith("https://flow-content.google/video/"):
            media = {
                "media_id": media_id,
                "url": url,
                "encoded_video_available": False,
                "resolved_via": "as29s",
            }
            if include_encoded_video:
                media["encoded_video"] = None
            items.append({
                "name": workflow["name"],
                "primary_media_id": media_id,
                "project_id": workflow.get("project_id") or resolved_project_id,
                "done": True,
                "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                "error": None,
                "media": media,
            })
        else:
            items.append({
                "name": workflow["name"],
                "primary_media_id": media_id,
                "project_id": workflow.get("project_id") or resolved_project_id,
                "done": False,
                "status": "PENDING",
                "error": None,
            })
    all_done = bool(items) and all(item["done"] for item in items)
    return {
        "project_id": resolved_project_id or None,
        "done": all_done,
        "status": "COMPLETED" if all_done else "PENDING",
        "workflows": items,
    }


async def check_omni_flash_status(
    workflows: list[dict],
    include_encoded_video: bool = False,
    project_id: str = "",
) -> dict:
    """Perform one non-blocking poll pass for Omni workflow-backed jobs."""
    return await _check_omni_batch_media(workflows, include_encoded_video, project_id)
