from fk_control.contracts import build_job_envelope, lane_dead_key, lane_stream_key, utcnow


def test_utcnow_uses_z_suffix():
    assert utcnow().endswith("Z")


def test_lane_stream_key():
    assert lane_stream_key("lane-01") == "lane:01:jobs"
    assert lane_stream_key("lane:01") == "lane:01:jobs"


def test_lane_dead_key():
    assert lane_dead_key("lane-01") == "lane:01:dead"
    assert lane_dead_key("lane:01") == "lane:01:dead"


def test_build_job_envelope_has_required_fields():
    job = build_job_envelope(
        job_type="GEN_IMAGES",
        project_id="project-1",
        chapter_id="chapter-1",
        lane_id="lane-01",
        payload={"scene_ids": ["scene-1"]},
        priority=75,
        max_attempts=3,
        trace_id="trace-1",
        idempotency_key="chapter:chapter-1:gen-images:v1",
    )
    assert job["job_type"] == "GEN_IMAGES"
    assert job["project_id"] == "project-1"
    assert job["chapter_id"] == "chapter-1"
    assert job["lane_id"] == "lane-01"
    assert job["priority"] == "75"
    assert job["max_attempts"] == "3"
    assert job["payload_json"] == "{\"scene_ids\":[\"scene-1\"]}"
