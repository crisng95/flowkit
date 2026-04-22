from redis.exceptions import ResponseError

from fk_control import storage


class _FakeRedis:
    def __init__(self, *, xlens=None, groups=None, errors=None):
        self.xlens = xlens or {}
        self.groups = groups or {}
        self.errors = errors or set()

    def xlen(self, stream):
        return self.xlens.get(stream, 0)

    def xinfo_groups(self, stream):
        if stream in self.errors:
            raise ResponseError("NOGROUP")
        return self.groups.get(stream, [])


def test_queue_depths_uses_group_backlog_not_stream_history(monkeypatch):
    fake = _FakeRedis(
        xlens={"chapters:pending": 10, "lane:01:jobs": 9, "lane:01:dead": 2},
        groups={
            "chapters:pending": [{"name": "scheduler", "pending": 1, "lag": 0}],
            "lane:01:jobs": [{"name": "lane:01", "pending": 2, "lag": 3}],
        },
    )
    monkeypatch.setattr(storage, "redis_client", lambda: fake)

    depths = storage.queue_depths()

    assert depths["chapters:pending"] == 1
    assert depths["chapters:pending:pending"] == 1
    assert depths["chapters:pending:lag"] == 0
    assert depths["chapters:pending:stream_depth"] == 10
    assert depths["lane:01:jobs"] == 5
    assert depths["lane:01:jobs:pending"] == 2
    assert depths["lane:01:jobs:lag"] == 3
    assert depths["lane:01:jobs:stream_depth"] == 9
    assert depths["lane:01:dead"] == 2


def test_queue_depths_falls_back_to_stream_length_when_group_missing(monkeypatch):
    fake = _FakeRedis(
        xlens={"chapters:pending": 4, "lane:01:jobs": 7},
        errors={"chapters:pending", "lane:01:jobs"},
    )
    monkeypatch.setattr(storage, "redis_client", lambda: fake)

    depths = storage.queue_depths()

    assert depths["chapters:pending"] == 4
    assert depths["chapters:pending:pending"] == 0
    assert depths["chapters:pending:lag"] == 4
    assert depths["lane:01:jobs"] == 7
    assert depths["lane:01:jobs:pending"] == 0
    assert depths["lane:01:jobs:lag"] == 7
