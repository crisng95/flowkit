"""Minimal scheduler stub that routes chapter requests into lane streams."""

import time
from uuid import uuid4

from redis.exceptions import ResponseError

from .config import settings
from .contracts import lane_stream_key
from .planning import LaneScore, build_chapter_job_plan, choose_best_lane
from .storage import get_chapter_execution_context, list_lanes, pg_conn, redis_client


def ensure_group(stream: str, group: str, r=None) -> None:
    r = r or redis_client()
    try:
        r.xgroup_create(stream, group, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def idle_lane_scores() -> list[LaneScore]:
    rows = [row for row in list_lanes() if row["status"] == "idle"]
    return [
        LaneScore(
            lane_id=row["lane_id"],
            credits_last_seen=row.get("credits_last_seen") or 0,
            token_age_seconds=row.get("token_age_seconds"),
        )
        for row in rows
    ]


def persist_assignment(chapter_id: str, lane_id: str, trace_id: str) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update chapters
                set assigned_lane_id = (select id from lanes where lane_id = %s),
                    status = 'assigned',
                    chapter_metadata = chapter_metadata || jsonb_build_object('trace_id', %s::text)
                where id = %s
                """,
                (lane_id, trace_id, chapter_id),
            )
            cur.execute(
                """
                update lanes
                set status = 'busy',
                    current_chapter_id = %s,
                    last_error_text = null
                where lane_id = %s
                """,
                (chapter_id, lane_id),
            )

def persist_jobs(jobs: list[dict[str, str]]) -> None:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            for job in jobs:
                cur.execute(
                    """
                    insert into jobs (
                      id,
                      chapter_id,
                      project_id,
                      lane_id,
                      job_type,
                      status,
                      max_attempts,
                      priority,
                      idempotency_key,
                      trace_id,
                      payload_json
                    )
                    values (
                      %s,
                      %s,
                      %s,
                      (select id from lanes where lane_id = %s),
                      %s,
                      'queued',
                      %s,
                      %s,
                      %s,
                      %s,
                      %s::jsonb
                    )
                    on conflict (idempotency_key) do update
                    set lane_id = excluded.lane_id,
                        trace_id = excluded.trace_id,
                        max_attempts = excluded.max_attempts,
                        priority = excluded.priority,
                        payload_json = excluded.payload_json
                    """,
                    (
                        job["job_id"],
                        job["chapter_id"],
                        job["project_id"],
                        job["lane_id"],
                        job["job_type"],
                        int(job["max_attempts"]),
                        int(job["priority"]),
                        job["idempotency_key"],
                        job["trace_id"],
                        job["payload_json"],
                    ),
                )


def enqueue_lane_jobs(jobs: list[dict[str, str]]) -> None:
    r = redis_client()
    for job in jobs:
        r.xadd(lane_stream_key(job["lane_id"]), job)


def schedule_pending_chapter(r, message_id: str, payload: dict[str, str]) -> bool:
    lane_id = choose_best_lane(idle_lane_scores())
    if not lane_id:
        r.xadd("chapters:pending", payload)
        r.xack("chapters:pending", "scheduler", message_id)
        time.sleep(2)
        return False

    trace_id = f"trace-{uuid4()}"
    chapter_context = get_chapter_execution_context(payload["chapter_id"]) or {}
    jobs = build_chapter_job_plan(payload["project_id"], payload["chapter_id"], lane_id, trace_id, chapter_context)
    persist_assignment(payload["chapter_id"], lane_id, trace_id)
    persist_jobs(jobs)
    enqueue_lane_jobs(jobs)
    r.xack("chapters:pending", "scheduler", message_id)
    return True


def read_pending_messages(r):
    try:
        return r.xreadgroup(
            "scheduler",
            settings.scheduler_consumer,
            {"chapters:pending": ">"},
            count=1,
            block=5000,
        )
    except ResponseError as exc:
        if "NOGROUP" not in str(exc):
            raise
        ensure_group("chapters:pending", "scheduler", r)
        return []


def run_forever() -> None:
    ensure_group("chapters:pending", "scheduler")
    r = redis_client()
    while True:
        messages = read_pending_messages(r)
        if not messages:
            continue
        _, entries = messages[0]
        message_id, payload = entries[0]
        schedule_pending_chapter(r, message_id, payload)


if __name__ == "__main__":
    run_forever()
