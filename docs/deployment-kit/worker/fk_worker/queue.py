"""Redis queue helpers for worker lanes."""

from redis.exceptions import ResponseError

from .config import settings


def lane_group_name(lane_id: str) -> str:
    return lane_id.replace("lane-", "lane:")


def lane_stream_key(lane_id: str) -> str:
    return f"{lane_group_name(lane_id)}:jobs"


def lane_dead_key(lane_id: str) -> str:
    return f"{lane_group_name(lane_id)}:dead"


def lane_heartbeat_key(lane_id: str) -> str:
    return f"{lane_group_name(lane_id)}:heartbeat"


def ensure_lane_group(redis_client, lane_id: str) -> None:
    stream = lane_stream_key(lane_id)
    group = lane_group_name(lane_id)
    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
