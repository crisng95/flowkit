"""In-memory runtime state for lane-runner health reporting."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from threading import Lock


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class RunnerState:
    lane_id: str
    status: str = "starting"
    api_reachable: bool = False
    extension_connected: bool = False
    flow_connected: bool = False
    flow_key_present: bool = False
    flow_auth_valid: bool = False
    runner_ready: bool = False
    dispatchable_reason: str = "starting"
    active_job_id: str | None = None
    active_chapter_id: str | None = None
    credits_last_seen: int | None = None
    token_age_seconds: int | None = None
    processed_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    last_error_text: str | None = None
    started_at: str = utcnow()
    last_heartbeat_at: str | None = None
    last_job_finished_at: str | None = None

    def snapshot(self) -> dict:
        return asdict(self)


class RunnerStateStore:
    def __init__(self, lane_id: str):
        self._lock = Lock()
        self._state = RunnerState(lane_id=lane_id)

    def update(self, **fields) -> None:
        with self._lock:
            for key, value in fields.items():
                setattr(self._state, key, value)

    def mark_heartbeat(
        self,
        *,
        api_reachable: bool,
        credits_last_seen: int | None,
        token_age_seconds: int | None,
        extension_connected: bool = False,
        flow_connected: bool = False,
        flow_key_present: bool = False,
        flow_auth_valid: bool = False,
        runner_ready: bool = False,
        dispatchable_reason: str = "starting",
    ) -> None:
        self.update(
            api_reachable=api_reachable,
            extension_connected=extension_connected,
            flow_connected=flow_connected,
            flow_key_present=flow_key_present,
            flow_auth_valid=flow_auth_valid,
            runner_ready=runner_ready,
            dispatchable_reason=dispatchable_reason,
            credits_last_seen=credits_last_seen,
            token_age_seconds=token_age_seconds,
            last_heartbeat_at=utcnow(),
        )

    def mark_job_started(self, *, job_id: str, chapter_id: str) -> None:
        self.update(status="busy", active_job_id=job_id, active_chapter_id=chapter_id, last_error_text=None)

    def mark_job_completed(self) -> None:
        with self._lock:
            self._state.status = "idle"
            self._state.active_job_id = None
            self._state.active_chapter_id = None
            self._state.processed_jobs += 1
            self._state.completed_jobs += 1
            self._state.last_job_finished_at = utcnow()

    def mark_job_failed(self, error_text: str, *, degraded: bool) -> None:
        with self._lock:
            self._state.status = "degraded" if degraded else "idle"
            self._state.processed_jobs += 1
            self._state.failed_jobs += 1
            self._state.last_error_text = error_text
            self._state.last_job_finished_at = utcnow()

    def snapshot(self) -> dict:
        with self._lock:
            return self._state.snapshot()
