from contextlib import contextmanager

from redis.exceptions import ResponseError

from fk_control import scheduler
from fk_control.planning import build_chapter_job_plan


class _FakeCursor:
    def __init__(self, statements):
        self.statements = statements

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.statements.append((" ".join(sql.split()), params))


class _FakeConn:
    def __init__(self, statements):
        self.statements = statements

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _FakeCursor(self.statements)

    def commit(self):
        return None

    def close(self):
        return None


@contextmanager
def _fake_pg_conn(statements):
    yield _FakeConn(statements)


class _FakeRedis:
    def __init__(self):
        self.events = []

    def xadd(self, stream, payload):
        self.events.append(("xadd", stream, payload))
        return f"{stream}-1"

    def xack(self, stream, group, message_id):
        self.events.append(("xack", stream, group, message_id))


class _FakeSchedulerReader:
    def __init__(self):
        self.events = []
        self.calls = 0

    def xgroup_create(self, stream, group, id="0", mkstream=True):
        self.events.append(("xgroup_create", stream, group, id, mkstream))

    def xreadgroup(self, group, consumer, streams, count=1, block=5000):
        self.calls += 1
        if self.calls == 1:
            raise ResponseError("NOGROUP No such key 'chapters:pending' or consumer group 'scheduler'")
        return []


def test_persist_assignment_updates_chapter_and_lane(monkeypatch):
    statements = []
    monkeypatch.setattr(scheduler, "pg_conn", lambda: _fake_pg_conn(statements))

    scheduler.persist_assignment("chapter-1", "lane-02", "trace-1")

    sql = "\n".join(statement for statement, _ in statements).lower()
    assert "update chapters" in sql
    assert "update lanes" in sql
    assert any(params and "lane-02" in params for _, params in statements)


def test_persist_jobs_inserts_job_rows(monkeypatch):
    statements = []
    monkeypatch.setattr(scheduler, "pg_conn", lambda: _fake_pg_conn(statements))
    jobs = build_chapter_job_plan("project-1", "chapter-1", "lane-01", "trace-1")

    scheduler.persist_jobs(jobs)

    inserts = [(sql, params) for sql, params in statements if "insert into jobs" in sql.lower()]
    assert len(inserts) == len(jobs)
    assert inserts[0][1][0] == jobs[0]["job_id"]


def test_schedule_pending_chapter_persists_then_acks(monkeypatch):
    fake_redis = _FakeRedis()
    steps = []

    monkeypatch.setattr(scheduler, "idle_lane_scores", lambda: [scheduler.LaneScore("lane-02", 100, 15)])
    monkeypatch.setattr(
        scheduler,
        "persist_assignment",
        lambda chapter_id, lane_id, trace_id: steps.append(("assign", chapter_id, lane_id, trace_id)),
    )
    monkeypatch.setattr(
        scheduler,
        "get_chapter_execution_context",
        lambda chapter_id: {
            "chapter_title": "Chapter 01",
            "source_title": "Demo Project",
            "source_brief": "Short brief",
            "target_scene_count": 2,
            "material_id": "realistic",
        },
    )
    monkeypatch.setattr(scheduler, "persist_jobs", lambda jobs: steps.append(("persist_jobs", len(jobs))))
    monkeypatch.setattr(scheduler, "enqueue_lane_jobs", lambda jobs: steps.append(("enqueue", len(jobs))))

    result = scheduler.schedule_pending_chapter(
        fake_redis,
        "msg-1",
        {"project_id": "project-1", "chapter_id": "chapter-1"},
    )

    assert result is True
    assert [step[0] for step in steps] == ["assign", "persist_jobs", "enqueue"]
    assert fake_redis.events == [("xack", "chapters:pending", "scheduler", "msg-1")]


def test_schedule_pending_chapter_requeues_when_no_lane(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(scheduler, "idle_lane_scores", lambda: [])

    result = scheduler.schedule_pending_chapter(
        fake_redis,
        "msg-1",
        {"project_id": "project-1", "chapter_id": "chapter-1"},
    )

    assert result is False
    assert fake_redis.events[0] == (
        "xadd",
        "chapters:pending",
        {"project_id": "project-1", "chapter_id": "chapter-1"},
    )
    assert fake_redis.events[1] == ("xack", "chapters:pending", "scheduler", "msg-1")


def test_read_pending_messages_recreates_group_after_reset():
    fake_redis = _FakeSchedulerReader()

    messages = scheduler.read_pending_messages(fake_redis)

    assert messages == []
    assert fake_redis.events == [("xgroup_create", "chapters:pending", "scheduler", "0", True)]
