"""Small Postgres/Redis helpers for the control scaffold."""

from contextlib import contextmanager
from uuid import uuid4
import json

import psycopg
from psycopg.rows import dict_row
import redis
from redis.exceptions import ResponseError

from .config import settings


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


def _stream_group_metrics(r, stream: str, group: str) -> dict[str, int]:
    stream_depth = int(r.xlen(stream))
    pending = 0
    lag = stream_depth
    try:
        groups = r.xinfo_groups(stream)
    except ResponseError:
        groups = []
    for entry in groups:
        if entry.get("name") == group:
            pending = int(entry.get("pending") or 0)
            lag_value = entry.get("lag")
            lag = int(lag_value) if lag_value is not None else max(stream_depth - pending, 0)
            break
    return {
        "backlog": pending + lag,
        "pending": pending,
        "lag": lag,
        "stream_depth": stream_depth,
    }


def ping_all() -> dict:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 as ok")
            db_ok = cur.fetchone()["ok"] == 1
    redis_ok = redis_client().ping()
    return {"postgres": db_ok, "redis": bool(redis_ok)}


def list_lanes() -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  lane_id,
                  vm_name,
                  status,
                  account_alias,
                  credits_last_seen,
                  token_age_seconds,
                  current_chapter_id,
                  last_heartbeat_at,
                  lane_metadata
                from lanes
                order by lane_id
                """
            )
            return cur.fetchall()


def list_projects() -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, project_slug, source_title, target_duration_seconds, status, material_id, created_at from projects order by created_at desc")
            return cur.fetchall()


def list_chapters(limit: int = 50) -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  c.id,
                  c.project_id,
                  c.chapter_index,
                  c.chapter_slug,
                  c.title,
                  c.target_duration_seconds,
                  c.target_scene_count,
                  c.status,
                  c.assigned_lane_id,
                  c.local_flow_project_id,
                  c.chapter_output_uri,
                  c.created_at,
                  p.project_slug,
                  l.lane_id
                from chapters c
                join projects p on p.id = c.project_id
                left join lanes l on l.id = c.assigned_lane_id
                order by c.created_at desc, c.chapter_index asc
                limit %s
                """,
                (limit,),
            )
            return cur.fetchall()


def list_jobs(limit: int = 100) -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  j.id,
                  j.chapter_id,
                  j.project_id,
                  j.job_type,
                  j.status,
                  j.attempt_count,
                  j.max_attempts,
                  j.priority,
                  j.trace_id,
                  j.error_text,
                  j.created_at,
                  j.started_at,
                  j.finished_at,
                  c.chapter_slug,
                  l.lane_id
                from jobs j
                join chapters c on c.id = j.chapter_id
                left join lanes l on l.id = j.lane_id
                order by j.created_at desc
                limit %s
                """,
                (limit,),
            )
            return cur.fetchall()


def queue_depths() -> dict[str, int]:
    r = redis_client()
    depths = {}
    pending_metrics = _stream_group_metrics(r, "chapters:pending", "scheduler")
    depths["chapters:pending"] = pending_metrics["backlog"]
    depths["chapters:pending:pending"] = pending_metrics["pending"]
    depths["chapters:pending:lag"] = pending_metrics["lag"]
    depths["chapters:pending:stream_depth"] = pending_metrics["stream_depth"]
    for lane_num in range(1, 11):
        lane_key = f"lane:{lane_num:02d}:jobs"
        dead_key = f"lane:{lane_num:02d}:dead"
        lane_group = f"lane:{lane_num:02d}"
        lane_metrics = _stream_group_metrics(r, lane_key, lane_group)
        depths[lane_key] = lane_metrics["backlog"]
        depths[f"{lane_key}:pending"] = lane_metrics["pending"]
        depths[f"{lane_key}:lag"] = lane_metrics["lag"]
        depths[f"{lane_key}:stream_depth"] = lane_metrics["stream_depth"]
        depths[dead_key] = int(r.xlen(dead_key))
    return depths


def get_project(project_id: str) -> dict | None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, project_slug, source_title, source_brief, target_duration_seconds, status, material_id, target_chapter_count, master_output_uri, project_metadata
                from projects
                where id = %s
                """,
                (project_id,),
            )
            return cur.fetchone()


def get_chapter_execution_context(chapter_id: str) -> dict | None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  c.id as chapter_id,
                  c.project_id,
                  c.chapter_index,
                  c.chapter_slug,
                  c.title as chapter_title,
                  c.synopsis,
                  c.target_duration_seconds,
                  c.target_scene_count,
                  p.source_title,
                  p.source_brief,
                  p.material_id
                from chapters c
                join projects p on p.id = c.project_id
                where c.id = %s
                """,
                (chapter_id,),
            )
            return cur.fetchone()


def create_project(source_title: str, source_brief: str | None, target_duration_seconds: int, material_id: str, chapter_count: int | None) -> dict:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            project_id = str(uuid4())
            cur.execute(
                """
                insert into projects (id, project_slug, source_title, source_brief, target_duration_seconds, status, material_id, target_chapter_count)
                values (%s, %s, %s, %s, %s, 'draft', %s, %s)
                returning id, project_slug, source_title, source_brief, target_duration_seconds, material_id, target_chapter_count, status, created_at
                """,
                (project_id, project_id.replace("-", "_"), source_title, source_brief, target_duration_seconds, material_id, chapter_count),
            )
            return cur.fetchone()


def create_chapters(project_id: str, chapter_rows: list[dict]) -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            created = []
            for row in chapter_rows:
                chapter_id = str(uuid4())
                cur.execute(
                    """
                    insert into chapters (id, project_id, chapter_index, chapter_slug, title, target_duration_seconds, target_scene_count, status)
                    values (%s, %s, %s, %s, %s, %s, %s, 'planned')
                    returning id, project_id, chapter_index, chapter_slug, title, target_duration_seconds, target_scene_count, status, created_at
                    """,
                    (chapter_id, project_id, row["chapter_index"], row["chapter_slug"], row["title"], row["target_duration_seconds"], row["target_scene_count"]),
                )
                created.append(cur.fetchone())
            return created


def enqueue_pending_chapter(chapter_id: str, project_id: str, chapter_index: int, target_duration_seconds: int, target_scene_count: int, material_id: str) -> str:
    r = redis_client()
    return r.xadd(
        "chapters:pending",
        {
            "project_id": str(project_id),
            "chapter_id": str(chapter_id),
            "chapter_index": str(chapter_index),
            "priority": "100",
            "target_duration_seconds": str(target_duration_seconds),
            "target_scene_count": str(target_scene_count),
            "material_id": str(material_id),
        },
    )


def list_completed_chapter_final_artifacts(project_id: str) -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  a.id,
                  a.chapter_id,
                  a.storage_uri,
                  a.local_path,
                  a.size_bytes,
                  c.chapter_index,
                  c.chapter_slug
                from artifacts a
                join chapters c on c.id = a.chapter_id
                where a.project_id = %s
                  and a.artifact_type = 'chapter_final'
                order by c.chapter_index asc
                """,
                (project_id,),
            )
            return cur.fetchall()


def set_project_master_output(project_id: str, master_output_uri: str) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update projects
                set master_output_uri = %s,
                    status = 'completed',
                    project_metadata = project_metadata || jsonb_build_object('master_output_uri', %s)
                where id = %s
                """,
                (master_output_uri, master_output_uri, project_id),
            )


def insert_artifact(
    *,
    project_id: str,
    chapter_id: str | None,
    lane_id: str | None,
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
