"""Gemini Omni Flash video generation through the Google Flow bridge.

Supported Omni surfaces in this module:

* first frame -> video via ``batchAsyncGenerateVideoStartImage``
* first + last frame -> video via ``batchAsyncGenerateVideoStartAndEndImage``
* reference images -> video via ``batchAsyncGenerateVideoReferenceImages``

Omni duration-specific model keys live in ``agent/models.json``.  First-frame
Flow requests have been captured with ``abra_i2v_<duration>s``.  The current
First+Last rollout uses the same Omni I2V family but the StartAndEnd endpoint;
that mapping is deliberately configurable separately so it can be changed
without a code release if Google's rollout rotates the wire key.

Important: Omni submit responses may contain operation-looking handles, but
those handles are not compatible with the legacy
``batchCheckAsyncVideoGenerationStatus`` polling endpoint. Omni jobs are
workflow-backed and are polled through Flow's authenticated project data.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from agent.config import USE_BATCH_RPC
from agent.services import flow_batch as fb
from agent.services.flow_client import get_flow_client
from agent.services.flow_poll import annotate_polling, check_workflow_status, extract_workflows
from agent.services.headers import random_headers

_MODELS_FILE = Path(__file__).parent.parent / "models.json"

#: Every Omni surface here rides the pre-migration transports — the REST
#: endpoints on aisandbox-pa and the labs.google tRPC snapshot it polls
#: through. Flow moved to flow.google.com in September 2026 and stopped
#: minting the bearer both of those need, and no Omni payload has been
#: captured off the new frontend, so on the batch path these fail with a
#: name rather than dying on a 401 five retries deep.
_UNSUPPORTED_ON_BATCH = (
    "UNSUPPORTED_ON_BATCH_API: Omni Flash frame/reference generation is not yet "
    "ported to flow.google.com batchexecute. Omni text-to-video is supported on "
    "the batch path; frame-to-video, start+end and reference-to-video still need "
    "their migrated payload captures."
)


def _batch_path_blocks_omni() -> dict | None:
    """The error to return instead of reaching for auth that is gone."""
    return {"error": _UNSUPPORTED_ON_BATCH} if USE_BATCH_RPC else None

OMNI_FLASH_VALID_DURATIONS = (4, 6, 8, 10)
OMNI_FLASH_VALID_ASPECTS = {
    "VIDEO_ASPECT_RATIO_PORTRAIT",
    "VIDEO_ASPECT_RATIO_LANDSCAPE",
}
OMNI_FLASH_MAX_REFERENCE_IMAGES = 7
# Informational only. Flow pricing can be promotional/variable.
OMNI_FLASH_CREDIT_COST = {4: 15, 6: 20, 8: 25, 10: 30}


async def _fetch_project_initial_data(client, project_id: str) -> dict:
    """Compatibility wrapper around FlowClient's public project poll surface."""
    return await client.get_project_initial_data(project_id)


async def _fetch_media_url(client, media_id: str) -> dict:
    """Compatibility wrapper around FlowClient's public URL resolver."""
    return await client.resolve_media_url(media_id)


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


def _annotate_polling(result: dict, project_id: str) -> dict:
    """Annotate legacy Omni submits using the shared polling descriptor."""
    return annotate_polling(result, mode="project_media", project_id=project_id)


async def generate_omni_flash_text_video(
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit Omni 1.1 Flash text-to-video on the migrated Flow batch API."""
    _validate_duration(duration_s)
    _validate_aspect(aspect_ratio)
    if not USE_BATCH_RPC:
        return {"error": "Omni text-to-video is implemented on the flow.google.com batch path only"}

    client = get_flow_client()
    try:
        pid = client._batch_project_id(project_id)
        model_key = f"abra_t2v_{duration_s}s"
        freq = fb.text_video_request(prompt, pid, aspect=aspect_ratio, model=model_key)
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
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit Omni first-frame or First+Last generation."""
    blocked = _batch_path_blocks_omni()
    if blocked:
        return blocked
    _validate_frame_inputs(
        start_image_media_id,
        end_image_media_id,
        duration_s,
        aspect_ratio,
    )

    mode = (
        "start_end_frame_to_video"
        if end_image_media_id is not None
        else "frame_to_video"
    )
    endpoint = (
        "generate_video_start_end"
        if end_image_media_id is not None
        else "generate_video"
    )
    model_key = _load_model_key(duration_s, mode=mode)
    client = get_flow_client()
    ts = int(time.time() * 1000)

    request_item = {
        "aspectRatio": aspect_ratio,
        "textInput": {"structuredPrompt": {"parts": [{"text": prompt}]}},
        "videoModelKey": model_key,
        "seed": seed if seed is not None else ts % 1_000_000,
        "metadata": {"sceneId": scene_id} if scene_id else {},
        "startImage": {"mediaId": start_image_media_id},
    }
    if end_image_media_id is not None:
        request_item["endImage"] = {"mediaId": end_image_media_id}

    context = client._client_context(project_id, user_paygate_tier)
    body = {
        "mediaGenerationContext": {"batchId": str(uuid.uuid4())},
        "clientContext": {**context, "sessionId": f";{ts}"},
        "requests": [request_item],
        "useV2ModelConfig": True,
    }

    result = await client._send(
        "api_request",
        {
            "url": client._build_url(endpoint),
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        },
        timeout=60,
    )
    return _annotate_polling(result, project_id)


async def generate_omni_flash_first_frame_video(
    start_image_media_id: str,
    prompt: str,
    project_id: str,
    scene_id: str = "",
    duration_s: int = 8,
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
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    user_paygate_tier: str = "PAYGATE_TIER_ONE",
    seed: int | None = None,
) -> dict:
    """Submit an Omni Flash reference-to-video generation.

    Successful responses are annotated with ``data.flowkitPolling`` containing
    the workflow names and primary media IDs required by the Omni polling path.
    Do not feed Omni operation handles to ``check_video_status``.
    """
    blocked = _batch_path_blocks_omni()
    if blocked:
        return blocked
    refs = _validate_reference_inputs(reference_media_ids, duration_s, aspect_ratio)
    model_key = _load_model_key(duration_s, mode="reference_to_video")
    client = get_flow_client()

    ts = int(time.time() * 1000)
    request_item = {
        "aspectRatio": aspect_ratio,
        "textInput": {"structuredPrompt": {"parts": [{"text": prompt}]}},
        "videoModelKey": model_key,
        "seed": seed if seed is not None else ts % 1_000_000,
        "metadata": {"sceneId": scene_id} if scene_id else {},
        "referenceImages": [
            {"mediaId": mid, "imageUsageType": "IMAGE_USAGE_TYPE_ASSET"}
            for mid in refs
        ],
    }

    context = client._client_context(project_id, user_paygate_tier)
    body = {
        "mediaGenerationContext": {
            "batchId": str(uuid.uuid4()),
            "audioFailurePreference": "BLOCK_SILENCED_VIDEOS",
        },
        "clientContext": {**context, "sessionId": f";{ts}"},
        "requests": [request_item],
        "useV2ModelConfig": True,
    }

    url = client._build_url("generate_video_references")
    result = await client._send(
        "api_request",
        {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        },
        timeout=60,
    )
    return _annotate_polling(result, project_id)


async def check_omni_flash_status(
    workflows: list[dict],
    include_encoded_video: bool = False,
    project_id: str = "",
) -> dict:
    """Perform one non-blocking poll pass using the shared Flow poller."""
    return await check_workflow_status(
        workflows,
        mode="batch_media" if USE_BATCH_RPC else "project_media",
        include_encoded_video=include_encoded_video,
        project_id=project_id,
        client=get_flow_client(),
    )
