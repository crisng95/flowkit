from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fk_worker import media
from fk_worker import stages
from fk_worker import storage
from fk_worker.media import canonical_clip_name, prefer_scene_video_url


def test_canonical_clip_name():
    assert canonical_clip_name(2, "scene-abc") == "scene_002_scene-abc.mp4"


def test_prefer_scene_video_url_prefers_upscale_when_requested():
    scene = {
        "vertical_upscale_url": "https://example.com/upscale.mp4",
        "vertical_video_url": "https://example.com/video.mp4",
    }
    assert prefer_scene_video_url(scene, orientation="VERTICAL", prefer_4k=True) == "https://example.com/upscale.mp4"


def test_prefer_scene_video_url_falls_back_to_video():
    scene = {
        "vertical_upscale_url": None,
        "vertical_video_url": "https://example.com/video.mp4",
    }
    assert prefer_scene_video_url(scene, orientation="VERTICAL", prefer_4k=True) == "https://example.com/video.mp4"


def test_translate_media_path_uses_container_mount_when_enabled(monkeypatch):
    monkeypatch.setenv("MEDIA_DOCKER_WORK_ROOT", "C:/workroot")
    monkeypatch.setenv("MEDIA_DOCKER_MOUNT_POINT", "/work")

    translated = media._translate_media_path(Path("C:/workroot/output/final.mp4"))

    assert translated == "/work/output/final.mp4"


def test_media_tool_command_uses_docker_when_configured(monkeypatch):
    monkeypatch.setenv("MEDIA_DOCKER_IMAGE", "flowkit-image:latest")
    monkeypatch.setenv("MEDIA_DOCKER_WORK_ROOT", "C:/workroot")
    monkeypatch.setenv("MEDIA_DOCKER_MOUNT_POINT", "/work")
    monkeypatch.setenv("FLOWKIT_UID", "1000")
    monkeypatch.setenv("FLOWKIT_GID", "1000")

    command = media._media_tool_command("ffprobe")

    assert command[:7] == ["docker", "run", "--rm", "--user", "1000:1000", "-v", "C:\\workroot:/work"]
    assert command[-2:] == ["ffprobe", "flowkit-image:latest"]


def test_handle_upload_artifacts_uses_local_fallback_when_enabled(monkeypatch, tmp_path):
    final_path = tmp_path / "chapter_final.mp4"
    final_path.write_bytes(b"video")

    inserted = []
    updates = []
    monkeypatch.setattr(stages, "settings", SimpleNamespace(r2_prefix="projects", lane_id="lane-01", allow_local_artifact_fallback=True))
    monkeypatch.setattr(stages, "upload_file", lambda path, key: (_ for _ in ()).throw(RuntimeError("no r2 creds")))
    monkeypatch.setattr(stages, "sha256_file", lambda path: "sha256")
    monkeypatch.setattr(stages, "insert_artifact", lambda **kwargs: inserted.append(kwargs))
    monkeypatch.setattr(stages, "update_chapter_state", lambda chapter_id, **kwargs: updates.append((chapter_id, kwargs)))

    chapter = {
        "id": "chapter-1",
        "project_id": "project-1",
        "project_slug": "project_slug",
        "chapter_slug": "chapter_slug",
        "chapter_metadata": {"local_final_path": str(final_path)},
    }

    result = stages.handle_upload_artifacts(chapter, {})

    assert result["status"] == "completed"
    assert result["upload_mode"] == "local_fallback"
    assert result["uploaded"] == [final_path.resolve().as_uri()]
    assert inserted[0]["storage_uri"] == final_path.resolve().as_uri()
    assert inserted[0]["artifact_metadata"]["upload_mode"] == "local_fallback"
    assert updates[0][1]["status"] == "completed"


def test_handle_upload_artifacts_serializes_uuid_chapter_id(monkeypatch, tmp_path):
    final_path = tmp_path / "chapter_final.mp4"
    final_path.write_bytes(b"video")
    chapter_id = uuid4()

    monkeypatch.setattr(stages, "settings", SimpleNamespace(r2_prefix="projects", lane_id="lane-01", allow_local_artifact_fallback=True))
    monkeypatch.setattr(stages, "upload_file", lambda path, key: (_ for _ in ()).throw(RuntimeError("no r2 creds")))
    monkeypatch.setattr(stages, "sha256_file", lambda path: "sha256")
    monkeypatch.setattr(stages, "insert_artifact", lambda **kwargs: None)
    monkeypatch.setattr(stages, "update_chapter_state", lambda chapter_id, **kwargs: None)

    chapter = {
        "id": chapter_id,
        "project_id": "project-1",
        "project_slug": "project_slug",
        "chapter_slug": "chapter_slug",
        "chapter_metadata": {"local_final_path": str(final_path)},
    }

    result = stages.handle_upload_artifacts(chapter, {})

    assert result["chapter_id"] == str(chapter_id)


def test_update_chapter_state_supports_chapter_output_uri(monkeypatch):
    executed = {}

    class FakeCursor:
        def execute(self, sql, values):
            executed["sql"] = sql
            executed["values"] = values

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

        def close(self):
            return None

    class FakePgConn:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(storage, "pg_conn", lambda: FakePgConn())

    storage.update_chapter_state(
        "chapter-1",
        status="completed",
        chapter_output_uri="file:///tmp/final.mp4",
        metadata_patch={"local_final_path": "/tmp/final.mp4"},
    )

    assert "chapter_output_uri = %s" in executed["sql"]
    assert executed["values"][0] == "completed"
    assert executed["values"][1] == "file:///tmp/final.mp4"


def test_handle_concat_chapter_serializes_uuid_chapter_id(monkeypatch, tmp_path):
    chapter_id = uuid4()
    final_path = tmp_path / "output" / "demo_final.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")

    class _Client:
        def get_project_output_dir(self, project_id):
            return {"path": "output", "slug": "demo"}

        def list_video_scenes(self, video_id):
            return [
                {
                    "id": "scene-1",
                    "display_order": 0,
                    "vertical_video_url": "https://example.com/video.mp4",
                    "vertical_video_status": "COMPLETED",
                }
            ]

    class _Response:
        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield b"video"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _HttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def stream(self, method, url):
            return _Response()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(stages, "FlowKitClient", _Client)
    monkeypatch.setattr(stages.httpx, "Client", _HttpClient)
    monkeypatch.setattr(stages, "local_clip_path", lambda output_dir, display_order, scene_id: video_path)
    monkeypatch.setattr(stages, "prefer_scene_video_url", lambda scene, orientation, prefer_4k: scene["vertical_video_url"])
    monkeypatch.setattr(stages, "probe_dimensions", lambda path: (1080, 1920))
    monkeypatch.setattr(stages, "normalize_clip", lambda source, target, width, height: target.parent.mkdir(parents=True, exist_ok=True) or target.write_bytes(b"norm"))
    monkeypatch.setattr(stages, "concat_clips", lambda clips, target: target.write_bytes(b"final"))
    monkeypatch.setattr(stages, "probe_duration", lambda path: 8.0)
    monkeypatch.setattr(stages, "settings", SimpleNamespace(flow_agent_dir=str(tmp_path)))
    monkeypatch.setattr(stages, "update_chapter_state", lambda chapter_id, **kwargs: None)

    chapter = {
        "id": chapter_id,
        "project_id": "project-1",
        "local_flow_project_id": "flow-project-1",
        "chapter_metadata": {"local_video_id": "video-1"},
    }

    result = stages.handle_concat_chapter(chapter, {})

    assert result["chapter_id"] == str(chapter_id)
