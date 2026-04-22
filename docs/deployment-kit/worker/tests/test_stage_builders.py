from fk_worker import runner
from fk_worker import stages
from fk_worker.queue import lane_dead_key, lane_group_name, lane_stream_key
from fk_worker.stages import build_ref_requests, build_scene_requests


def test_lane_key_helpers():
    assert lane_group_name("lane-01") == "lane:01"
    assert lane_stream_key("lane-01") == "lane:01:jobs"
    assert lane_dead_key("lane-01") == "lane:01:dead"


def test_build_ref_requests():
    payload = build_ref_requests("project-1", ["char-1", "char-2"])
    assert payload["requests"][0]["type"] == "GENERATE_CHARACTER_IMAGE"
    assert payload["requests"][1]["character_id"] == "char-2"


def test_build_scene_requests():
    payload = build_scene_requests(
        "GENERATE_VIDEO",
        project_id="project-1",
        video_id="video-1",
        scene_ids=["scene-1", "scene-2"],
        orientation="VERTICAL",
    )
    assert payload["requests"][0]["type"] == "GENERATE_VIDEO"
    assert payload["requests"][0]["video_id"] == "video-1"
    assert payload["requests"][1]["scene_id"] == "scene-2"


def test_dispatch_supports_create_entities(monkeypatch):
    captured = {}

    def fake_handle(client, chapter, payload):
        captured["chapter"] = chapter
        captured["payload"] = payload
        return ["ok"]

    monkeypatch.setattr(runner, "handle_create_entities", fake_handle)

    result = runner._dispatch("CREATE_ENTITIES", client=object(), chapter={"id": "chapter-1"}, payload={"entities": [{"name": "Anchor"}]})

    assert result == ["ok"]
    assert captured["payload"]["entities"][0]["name"] == "Anchor"


def test_handle_gen_videos_raises_when_any_request_failed():
    class FakeClient:
        def submit_requests_batch(self, payload):
            return [{"id": "req-1"}]

        def wait_for_requests(self, request_ids, timeout_seconds=900, poll_interval=6):
            return [{"id": "req-1", "status": "FAILED", "error": "boom"}]

        def list_video_scenes(self, video_id):
            return [{"id": "scene-1", "vertical_video_url": "https://example.com/video.mp4", "vertical_video_status": "COMPLETED"}]

    chapter = {
        "id": "chapter-1",
        "local_flow_project_id": "project-1",
        "chapter_metadata": {"local_video_id": "video-1", "local_scene_ids": ["scene-1"]},
    }

    try:
        stages.handle_gen_videos(FakeClient(), chapter, {"scene_ids": ["scene-1"], "orientation": "VERTICAL"})
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "GENERATE_VIDEO" in str(exc)
        assert "req-1" in str(exc)


def test_handle_gen_videos_raises_when_scene_has_no_downloadable_video():
    class FakeClient:
        def submit_requests_batch(self, payload):
            return [{"id": "req-1"}]

        def wait_for_requests(self, request_ids, timeout_seconds=900, poll_interval=6):
            return [{"id": "req-1", "status": "COMPLETED"}]

        def list_video_scenes(self, video_id):
            return [{"id": "scene-1", "vertical_video_url": None, "vertical_video_status": "FAILED"}]

    chapter = {
        "id": "chapter-1",
        "local_flow_project_id": "project-1",
        "chapter_metadata": {"local_video_id": "video-1", "local_scene_ids": ["scene-1"]},
    }

    try:
        stages.handle_gen_videos(FakeClient(), chapter, {"scene_ids": ["scene-1"], "orientation": "VERTICAL"})
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "scene-1" in str(exc)
        assert "FAILED" in str(exc)
