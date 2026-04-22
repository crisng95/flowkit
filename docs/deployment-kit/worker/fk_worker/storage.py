"""Postgres and Redis helpers for the lane worker."""

from contextlib import contextmanager
import json

import psycopg
from psycopg.rows import dict_row
import redis

from .config import settings
from .queue import lane_heartbeat_key


@contextmanager
def pg_conn():
    conn = psycopg.connect(settings.postgres_dsn, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def redis_client():
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_chapter(chapter_id: str) -> dict | None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select c.*, l.lane_id, p.project_slug, p.source_title
                from chapters c
                left join lanes l on l.id = c.assigned_lane_id
                join projects p on p.id = c.project_id
                where c.id = %s
                """,
                (chapter_id,),
            )
            return cur.fetchone()


def update_chapter_state(
    chapter_id: str,
    *,
    status: str | None = None,
    local_flow_project_id: str | None = None,
    chapter_output_uri: str | None = None,
    metadata_patch: dict | None = None,
) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            sets = []
            values = []
            if status is not None:
                sets.append("status = %s")
                values.append(status)
            if local_flow_project_id is not None:
                sets.append("local_flow_project_id = %s")
                values.append(local_flow_project_id)
            if chapter_output_uri is not None:
                sets.append("chapter_output_uri = %s")
                values.append(chapter_output_uri)
            if metadata_patch:
                sets.append("chapter_metadata = chapter_metadata || %s::jsonb")
                values.append(json.dumps(metadata_patch))
            if not sets:
                return
            values.append(chapter_id)
            cur.execute(f"update chapters set {', '.join(sets)} where id = %s", values)


def set_lane_state(
    *,
    status: str,
    current_chapter_id: str | None = None,
    credits_last_seen: int | None = None,
    token_age_seconds: int | None = None,
    last_error_text: str | None = None,
    lane_metadata_patch: dict | None = None,
) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            metadata_json = json.dumps(lane_metadata_patch or {})
            cur.execute(
                """
                update lanes
                set status = %s,
                    current_chapter_id = %s,
                    credits_last_seen = coalesce(%s, credits_last_seen),
                    token_age_seconds = coalesce(%s, token_age_seconds),
                    last_error_text = %s,
                    lane_metadata = lane_metadata || %s::jsonb,
                    last_heartbeat_at = now()
                where lane_id = %s
                """,
                (status, current_chapter_id, credits_last_seen, token_age_seconds, last_error_text, metadata_json, settings.lane_id),
            )


def mark_job_claimed(job_id: str, chapter_id: str) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update jobs
                set status = 'claimed',
                    lane_id = (select id from lanes where lane_id = %s),
                    claimed_at = now(),
                    started_at = coalesce(started_at, now()),
                    attempt_count = attempt_count + 1
                where id = %s
                """,
                (settings.lane_id, job_id),
            )
    set_lane_state(status="busy", current_chapter_id=chapter_id)


def mark_job_completed(job_id: str, result: dict | None = None) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update jobs
                set status = 'completed',
                    result_json = %s::jsonb,
                    finished_at = now()
                where id = %s
                """,
                (json.dumps(result or {}), job_id),
            )


def mark_job_failed(job_id: str, *, status: str, error_text: str, result: dict | None = None) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update jobs
                set status = %s,
                    error_text = %s,
                    result_json = %s::jsonb,
                    finished_at = now()
                where id = %s
                """,
                (status, error_text, json.dumps(result or {}), job_id),
            )


def publish_heartbeat(*, active_job_id: str | None, active_chapter_id: str | None, credits_last_seen: int | None, token_age_seconds: int | None) -> None:
    payload = {
        "lane_id": settings.lane_id,
        "worker_hostname": settings.worker_consumer_name,
        "active_job_id": active_job_id,
        "active_chapter_id": active_chapter_id,
        "credits_last_seen": credits_last_seen,
        "token_age_seconds": token_age_seconds,
    }
    redis_client().set(
        lane_heartbeat_key(settings.lane_id),
        json.dumps(payload),
        ex=settings.heartbeat_ttl_seconds,
    )


def insert_artifact(
    *,
    project_id: str,
    chapter_id: str | None,
    lane_id: str,
    artifact_type: str,
    local_path: str | None,
    storage_uri: str,
    checksum_sha256: str | None,
    size_bytes: int | None,
    duration_seconds: float | None = None,
    width: int | None = None,
    height: int | None = None,
    artifact_metadata: dict | None = None,
) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into artifacts (
                  project_id, chapter_id, lane_id, artifact_type, local_path, storage_uri,
                  checksum_sha256, size_bytes, duration_seconds, width, height, artifact_metadata
                )
                values (
                  %s, %s, (select id from lanes where lane_id = %s), %s, %s, %s,
                  %s, %s, %s, %s, %s, %s::jsonb
                )
                """,
                (
                    project_id,
                    chapter_id,
                    lane_id,
                    artifact_type,
                    local_path,
                    storage_uri,
                    checksum_sha256,
                    size_bytes,
                    duration_seconds,
                    width,
                    height,
                    json.dumps(artifact_metadata or {}),
                ),
            )
