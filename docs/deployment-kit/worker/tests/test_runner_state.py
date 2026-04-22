from redis.exceptions import ResponseError

from fk_worker import runner
from fk_worker.state import RunnerStateStore


def test_runner_state_idle_to_busy_to_completed():
    store = RunnerStateStore("lane-01")
    store.mark_heartbeat(api_reachable=True, credits_last_seen=100, token_age_seconds=30)
    store.mark_job_started(job_id="job-1", chapter_id="chapter-1")
    busy = store.snapshot()
    assert busy["status"] == "busy"
    assert busy["active_job_id"] == "job-1"

    store.mark_job_completed()
    done = store.snapshot()
    assert done["status"] == "idle"
    assert done["active_job_id"] is None
    assert done["completed_jobs"] == 1


def test_runner_state_failed_degraded():
    store = RunnerStateStore("lane-01")
    store.mark_job_started(job_id="job-2", chapter_id="chapter-2")
    store.mark_job_failed("boom", degraded=True)
    state = store.snapshot()
    assert state["status"] == "degraded"
    assert state["failed_jobs"] == 1
    assert state["last_error_text"] == "boom"


class _FakeRedisReader:
    def __init__(self):
        self.calls = 0
        self.events = []

    def xreadgroup(self, group, consumer, streams, count=1, block=5000):
        self.calls += 1
        if self.calls == 1:
            raise ResponseError("NOGROUP No such key 'lane:01:jobs' or consumer group 'lane:01'")
        return []


def test_read_lane_messages_recreates_group_after_reset(monkeypatch):
    fake = _FakeRedisReader()
    monkeypatch.setattr(runner, "ensure_lane_group", lambda redis_client, lane_id: fake.events.append(("ensure", lane_id)))

    messages = runner.read_lane_messages(fake, "lane:01:jobs", "lane:01")

    assert messages == []
    assert fake.events == [("ensure", "lane-01")]


def test_probe_lane_runtime_reports_pause_reason_when_extension_missing():
    class _Client:
        def get_health(self):
            return {"extension_connected": False}

        def get_flow_status(self):
            return {"connected": False, "flow_key_present": True}

        def get_flow_credits(self):
            return {"credits": 321}

    snapshot = runner.probe_lane_runtime(_Client())

    assert snapshot["api_reachable"] is True
    assert snapshot["runner_ready"] is False
    assert snapshot["lane_status"] == "paused"
    assert snapshot["dispatchable_reason"] == "extension_disconnected"


def test_probe_lane_runtime_requires_valid_flow_credits_auth():
    class _Client:
        def get_health(self):
            return {"extension_connected": True}

        def get_flow_status(self):
            return {"connected": True, "flow_key_present": True}

        def get_flow_credits(self):
            return {"error": {"code": 401, "status": "UNAUTHENTICATED"}}

    snapshot = runner.probe_lane_runtime(_Client())

    assert snapshot["api_reachable"] is True
    assert snapshot["runner_ready"] is False
    assert snapshot["lane_status"] == "paused"
    assert snapshot["dispatchable_reason"] == "flow_auth_invalid"


def test_runner_state_tracks_runtime_readiness_details():
    store = RunnerStateStore("lane-02")

    store.mark_heartbeat(
        api_reachable=True,
        credits_last_seen=111,
        token_age_seconds=7,
        extension_connected=True,
        flow_connected=True,
        flow_key_present=True,
        flow_auth_valid=True,
        runner_ready=True,
        dispatchable_reason="ready",
    )

    state = store.snapshot()
    assert state["extension_connected"] is True
    assert state["flow_connected"] is True
    assert state["flow_key_present"] is True
    assert state["flow_auth_valid"] is True
    assert state["runner_ready"] is True
    assert state["dispatchable_reason"] == "ready"
