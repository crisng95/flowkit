"""Redis stream/job envelope contract helpers."""

from datetime import datetime, timezone
from uuid import uuid4
import json

JOB_TYPES = (
    "CREATE_PROJECT",
    "CREATE_ENTITIES",
    "CREATE_VIDEO",
    "CREATE_SCENES",
    "GEN_REFS",
    "GEN_IMAGES",
    "GEN_VIDEOS",
    "UPSCALE",
    "CONCAT_CHAPTER",
    "UPLOAD_ARTIFACTS",
    "ASSEMBLE_MASTER",
)


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def lane_stream_key(lane_id: str) -> str:
    return f"{lane_id}:jobs" if lane_id.startswith("lane:") else f"{lane_id.replace('lane-', 'lane:')}:jobs"


def lane_dead_key(lane_id: str) -> str:
    return f"{lane_id}:dead" if lane_id.startswith("lane:") else f"{lane_id.replace('lane-', 'lane:')}:dead"


def build_job_envelope(
    *,
    job_type: str,
    project_id: str,
    chapter_id: str,
    lane_id: str,
    payload: dict,
    priority: int,
    max_attempts: int,
    trace_id: str,
    idempotency_key: str,
) -> dict[str, str]:
    if job_type not in JOB_TYPES:
        raise ValueError(f"Unknown job type: {job_type}")
    return {
        "job_id": str(uuid4()),
        "job_type": job_type,
        "project_id": project_id,
        "chapter_id": chapter_id,
        "lane_id": lane_id,
        "trace_id": trace_id,
        "attempt": "0",
        "max_attempts": str(max_attempts),
        "priority": str(priority),
        "idempotency_key": idempotency_key,
        "created_at": utcnow(),
        "payload_json": json.dumps(payload, separators=(",", ":")),
    }
