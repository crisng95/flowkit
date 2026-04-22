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
