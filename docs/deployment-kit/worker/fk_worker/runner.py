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


def _credits_and_token_age(client: FlowKitClient) -> tuple[int | None, int | None]:
    try:
        status = client.get_flow_status()
        credits = client.get_flow_credits().get("credits")
        token_age = 0 if status.get("flow_key_present") else None
        return credits, token_age
    except Exception:
        return None, None


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
        credits, token_age = _credits_and_token_age(client)
        state.mark_heartbeat(api_reachable=credits is not None or token_age is not None, credits_last_seen=credits, token_age_seconds=token_age)
        publish_heartbeat(active_job_id=None, active_chapter_id=None, credits_last_seen=credits, token_age_seconds=token_age)
        messages = read_lane_messages(r, stream, group)
        if not messages:
            set_lane_state(status="idle", current_chapter_id=None, credits_last_seen=credits, token_age_seconds=token_age, last_error_text=None)
            state.update(status="idle")
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
            set_lane_state(status="idle", current_chapter_id=None, credits_last_seen=credits, token_age_seconds=token_age, last_error_text=None)
            state.update(status="idle")
            r.xack(stream, group, message_id)
            continue

        mark_job_claimed(envelope["job_id"], envelope["chapter_id"])
        state.mark_job_started(job_id=envelope["job_id"], chapter_id=envelope["chapter_id"])
        publish_heartbeat(active_job_id=envelope["job_id"], active_chapter_id=envelope["chapter_id"], credits_last_seen=credits, token_age_seconds=token_age)

        try:
            result = _dispatch(envelope["job_type"], client, chapter, payload)
            mark_job_completed(envelope["job_id"], result=result if isinstance(result, dict) else {"items": result})
            state.mark_job_completed()
            if should_release_lane(envelope["job_type"]):
                set_lane_state(status="idle", current_chapter_id=None, credits_last_seen=credits, token_age_seconds=token_age, last_error_text=None)
            else:
                set_lane_state(
                    status="busy",
                    current_chapter_id=envelope["chapter_id"],
                    credits_last_seen=credits,
                    token_age_seconds=token_age,
                    last_error_text=None,
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
            set_lane_state(status="degraded", current_chapter_id=envelope["chapter_id"], credits_last_seen=credits, token_age_seconds=token_age, last_error_text=error_text)
            r.xack(stream, group, message_id)


if __name__ == "__main__":
    run_forever()
