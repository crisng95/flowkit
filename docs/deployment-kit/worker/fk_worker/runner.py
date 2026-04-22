"""Redis stream consumer for one FlowKit lane."""

from __future__ import annotations

import json
import time

from redis.exceptions import ResponseError

from .client import FlowKitClient
from .config import settings
from .health import start_health_server
from .queue import ensure_lane_group, lane_dead_key, lane_group_name, lane_stream_key
from .state import RunnerStateStore
from .stages import (
    handle_concat_chapter,
    handle_create_entities,
    handle_create_project,
    handle_create_scenes,
    handle_create_video,
    handle_gen_images,
    handle_gen_refs,
    handle_gen_videos,
    handle_upload_artifacts,
    handle_upscale,
)
from .storage import get_chapter, mark_job_claimed, mark_job_completed, mark_job_failed, publish_heartbeat, redis_client, set_lane_state, update_chapter_state


def _dispatchable_reason(snapshot: dict) -> str:
    if not snapshot.get("api_reachable"):
        return "api_unreachable"
    if not snapshot.get("extension_connected"):
        return "extension_disconnected"
    if not snapshot.get("flow_key_present"):
        return "flow_key_missing"
    if not snapshot.get("flow_connected"):
        return "flow_disconnected"
    if not snapshot.get("flow_auth_valid"):
        return "flow_auth_invalid"
    return "ready"


def _extract_credits_probe(payload) -> tuple[bool, int | None]:
    if not isinstance(payload, dict):
        return False, None
    if payload.get("error"):
        return False, None
    if "credits" not in payload:
        return False, None
    return True, payload.get("credits")


def probe_lane_runtime(client: FlowKitClient) -> dict:
    snapshot = {
        "api_reachable": False,
        "extension_connected": False,
        "flow_connected": False,
        "flow_key_present": False,
        "flow_auth_valid": False,
        "credits_last_seen": None,
        "token_age_seconds": None,
    }

    try:
        health = client.get_health()
    except Exception:
        reason = _dispatchable_reason(snapshot)
        return {**snapshot, "runner_ready": False, "dispatchable_reason": reason, "lane_status": "paused"}

    snapshot["api_reachable"] = True
    snapshot["extension_connected"] = bool(health.get("extension_connected"))

    try:
        status = client.get_flow_status()
    except Exception:
        status = {}

    snapshot["flow_connected"] = bool(status.get("connected"))
    snapshot["flow_key_present"] = bool(status.get("flow_key_present"))

    try:
        auth_valid, credits = _extract_credits_probe(client.get_flow_credits())
        snapshot["credits_last_seen"] = credits
        snapshot["flow_auth_valid"] = auth_valid
    except Exception:
        snapshot["credits_last_seen"] = None
        snapshot["flow_auth_valid"] = False

    snapshot["token_age_seconds"] = 0 if snapshot["flow_key_present"] else None
    reason = _dispatchable_reason(snapshot)
    ready = reason == "ready"
    return {
        **snapshot,
        "runner_ready": ready,
        "dispatchable_reason": reason,
        "lane_status": "idle" if ready else "paused",
    }


def _lane_metadata_from_probe(probe: dict) -> dict:
    return {
        "api_reachable": probe["api_reachable"],
        "extension_connected": probe["extension_connected"],
        "flow_connected": probe["flow_connected"],
        "flow_key_present": probe["flow_key_present"],
        "flow_auth_valid": probe["flow_auth_valid"],
        "runner_ready": probe["runner_ready"],
        "dispatchable_reason": probe["dispatchable_reason"],
    }


def _dispatch(job_type: str, client: FlowKitClient, chapter: dict, payload: dict):
    if job_type == "CREATE_PROJECT":
        return handle_create_project(client, chapter["id"], payload)
    if job_type == "CREATE_ENTITIES":
        return handle_create_entities(client, chapter, payload)
    if job_type == "CREATE_VIDEO":
        return handle_create_video(client, chapter, payload)
    if job_type == "CREATE_SCENES":
        return handle_create_scenes(client, chapter, payload)
    if job_type == "GEN_REFS":
        return handle_gen_refs(client, chapter, payload)
    if job_type == "GEN_IMAGES":
        return handle_gen_images(client, chapter, payload)
    if job_type == "GEN_VIDEOS":
        return handle_gen_videos(client, chapter, payload)
    if job_type == "UPSCALE":
        return handle_upscale(client, chapter, payload)
    if job_type == "CONCAT_CHAPTER":
        return handle_concat_chapter(chapter, payload)
    if job_type == "UPLOAD_ARTIFACTS":
        return handle_upload_artifacts(chapter, payload)
    raise NotImplementedError(f"Job type not implemented in scaffold: {job_type}")


def should_release_lane(job_type: str) -> bool:
    return job_type == "UPLOAD_ARTIFACTS"


def should_skip_job(chapter: dict, job_type: str) -> str | None:
    if chapter.get("status") == "failed":
        return f"Chapter already failed before {job_type}"
    return None


def prerequisite_wait_reason(chapter: dict, job_type: str) -> str | None:
    metadata = chapter.get("chapter_metadata") or {}
    has_project = bool(chapter.get("local_flow_project_id"))
    has_video = bool(metadata.get("local_video_id"))
    has_scenes = bool(metadata.get("local_scene_ids"))
    has_final = bool(metadata.get("local_final_path"))

    if job_type == "CREATE_PROJECT":
        return None
    if not has_project:
        return "waiting for CREATE_PROJECT"
    if job_type in {"CREATE_ENTITIES", "CREATE_VIDEO"}:
        return None
    if not has_video:
        return "waiting for CREATE_VIDEO"
    if job_type == "CREATE_SCENES":
        return None
    if job_type in {"GEN_REFS"}:
        return None
    if not has_scenes and job_type in {"GEN_IMAGES", "GEN_VIDEOS", "CONCAT_CHAPTER", "UPLOAD_ARTIFACTS"}:
        return "waiting for CREATE_SCENES"
    if job_type == "UPLOAD_ARTIFACTS" and not has_final:
        return "waiting for CONCAT_CHAPTER"
    return None


def read_lane_messages(r, stream: str, group: str):
    try:
        return r.xreadgroup(group, settings.worker_consumer_name, {stream: ">"}, count=1, block=5000)
    except ResponseError as exc:
        if "NOGROUP" not in str(exc):
            raise
        ensure_lane_group(r, settings.lane_id)
        return []


def run_forever() -> None:
    r = redis_client()
    ensure_lane_group(r, settings.lane_id)
    client = FlowKitClient()
    state = RunnerStateStore(settings.lane_id)
    start_health_server(state)
    stream = lane_stream_key(settings.lane_id)
    group = lane_group_name(settings.lane_id)

    while True:
        probe = probe_lane_runtime(client)
        metadata_patch = _lane_metadata_from_probe(probe)
        state.mark_heartbeat(
            api_reachable=probe["api_reachable"],
            credits_last_seen=probe["credits_last_seen"],
            token_age_seconds=probe["token_age_seconds"],
            extension_connected=probe["extension_connected"],
            flow_connected=probe["flow_connected"],
            flow_key_present=probe["flow_key_present"],
            flow_auth_valid=probe["flow_auth_valid"],
            runner_ready=probe["runner_ready"],
            dispatchable_reason=probe["dispatchable_reason"],
        )
        publish_heartbeat(
            active_job_id=None,
            active_chapter_id=None,
            credits_last_seen=probe["credits_last_seen"],
            token_age_seconds=probe["token_age_seconds"],
        )
        messages = read_lane_messages(r, stream, group)
        if not messages:
            last_error_text = None if probe["runner_ready"] else probe["dispatchable_reason"]
            set_lane_state(
                status=probe["lane_status"],
                current_chapter_id=None,
                credits_last_seen=probe["credits_last_seen"],
                token_age_seconds=probe["token_age_seconds"],
                last_error_text=last_error_text,
                lane_metadata_patch=metadata_patch,
            )
            state.update(status=probe["lane_status"])
            continue

        _, entries = messages[0]
        message_id, envelope = entries[0]
        payload = json.loads(envelope["payload_json"])
        chapter = get_chapter(envelope["chapter_id"])
        if not chapter:
            mark_job_failed(envelope["job_id"], status="failed", error_text="Chapter not found")
            state.mark_job_failed("Chapter not found", degraded=False)
            r.xack(stream, group, message_id)
            continue

        skip_reason = should_skip_job(chapter, envelope["job_type"])
        if skip_reason:
            mark_job_failed(envelope["job_id"], status="dead", error_text=skip_reason)
            state.mark_job_failed(skip_reason, degraded=False)
            r.xack(stream, group, message_id)
            continue

        wait_reason = prerequisite_wait_reason(chapter, envelope["job_type"])
        if wait_reason:
            r.xadd(stream, envelope)
            set_lane_state(
                status=probe["lane_status"],
                current_chapter_id=None,
                credits_last_seen=probe["credits_last_seen"],
                token_age_seconds=probe["token_age_seconds"],
                last_error_text=None if probe["runner_ready"] else probe["dispatchable_reason"],
                lane_metadata_patch=metadata_patch,
            )
            state.update(status=probe["lane_status"])
            r.xack(stream, group, message_id)
            continue

        mark_job_claimed(envelope["job_id"], envelope["chapter_id"])
        state.mark_job_started(job_id=envelope["job_id"], chapter_id=envelope["chapter_id"])
        publish_heartbeat(
            active_job_id=envelope["job_id"],
            active_chapter_id=envelope["chapter_id"],
            credits_last_seen=probe["credits_last_seen"],
            token_age_seconds=probe["token_age_seconds"],
        )

        try:
            result = _dispatch(envelope["job_type"], client, chapter, payload)
            mark_job_completed(envelope["job_id"], result=result if isinstance(result, dict) else {"items": result})
            state.mark_job_completed()
            if should_release_lane(envelope["job_type"]):
                set_lane_state(
                    status=probe["lane_status"],
                    current_chapter_id=None,
                    credits_last_seen=probe["credits_last_seen"],
                    token_age_seconds=probe["token_age_seconds"],
                    last_error_text=None if probe["runner_ready"] else probe["dispatchable_reason"],
                    lane_metadata_patch=metadata_patch,
                )
                state.update(status=probe["lane_status"], active_chapter_id=None)
            else:
                set_lane_state(
                    status="busy",
                    current_chapter_id=envelope["chapter_id"],
                    credits_last_seen=probe["credits_last_seen"],
                    token_age_seconds=probe["token_age_seconds"],
                    last_error_text=None,
                    lane_metadata_patch=metadata_patch,
                )
                state.update(status="busy", active_chapter_id=envelope["chapter_id"])
            r.xack(stream, group, message_id)
        except Exception as exc:
            attempt = int(envelope["attempt"])
            max_attempts = int(envelope["max_attempts"])
            error_text = str(exc)
            if attempt + 1 < max_attempts:
                next_envelope = dict(envelope)
                next_envelope["attempt"] = str(attempt + 1)
                r.xadd(stream, next_envelope)
                mark_job_failed(envelope["job_id"], status="retryable", error_text=error_text)
                state.mark_job_failed(error_text, degraded=False)
            else:
                r.xadd(lane_dead_key(settings.lane_id), {**envelope, "dead_reason": "max_attempts_exhausted", "last_error": error_text})
                mark_job_failed(envelope["job_id"], status="dead", error_text=error_text)
                update_chapter_state(
                    envelope["chapter_id"],
                    status="failed",
                    metadata_patch={"failed_job_type": envelope["job_type"], "last_error_text": error_text},
                )
                state.mark_job_failed(error_text, degraded=True)
            set_lane_state(
                status="degraded",
                current_chapter_id=envelope["chapter_id"],
                credits_last_seen=probe["credits_last_seen"],
                token_age_seconds=probe["token_age_seconds"],
                last_error_text=error_text,
                lane_metadata_patch=metadata_patch,
            )
            r.xack(stream, group, message_id)


if __name__ == "__main__":
    run_forever()
