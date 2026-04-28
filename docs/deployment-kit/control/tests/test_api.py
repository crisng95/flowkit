from fastapi.testclient import TestClient

from fk_control import api as control_api


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(control_api, "ping_all", lambda: {"postgres": True, "redis": True})
    client = TestClient(control_api.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "postgres": True, "redis": True}


def test_create_project_enqueues_chapters(monkeypatch):
    created_project = {
        "id": "project-1",
        "project_slug": "project_1",
        "source_title": "Project 1",
        "source_brief": None,
        "target_duration_seconds": 900,
        "material_id": "realistic",
        "target_chapter_count": 3,
        "status": "draft",
        "created_at": "2026-04-21T12:00:00Z",
    }
    created_chapters = [
        {
            "id": "chapter-1",
            "project_id": "project-1",
            "chapter_index": 1,
            "chapter_slug": "project_x_chapter_01",
            "title": "Project X - Chapter 01",
            "target_duration_seconds": 300,
            "target_scene_count": 38,
            "status": "planned",
            "created_at": "2026-04-21T12:00:01Z",
        },
        {
            "id": "chapter-2",
            "project_id": "project-1",
            "chapter_index": 2,
            "chapter_slug": "project_x_chapter_02",
            "title": "Project X - Chapter 02",
            "target_duration_seconds": 300,
            "target_scene_count": 38,
            "status": "planned",
            "created_at": "2026-04-21T12:00:01Z",
        },
        {
            "id": "chapter-3",
            "project_id": "project-1",
            "chapter_index": 3,
            "chapter_slug": "project_x_chapter_03",
            "title": "Project X - Chapter 03",
            "target_duration_seconds": 300,
            "target_scene_count": 38,
            "status": "planned",
            "created_at": "2026-04-21T12:00:01Z",
        },
    ]
    stream_ids: list[str] = []

    monkeypatch.setattr(control_api, "create_project", lambda **kwargs: created_project)
    monkeypatch.setattr(control_api, "create_chapters", lambda project_id, rows: created_chapters)
    monkeypatch.setattr(
        control_api,
        "enqueue_pending_chapter",
        lambda chapter_id, project_id, chapter_index, target_duration_seconds, target_scene_count, material_id: stream_ids.append(chapter_id) or f"stream-{chapter_index}",
    )

    client = TestClient(control_api.app)
    response = client.post(
        "/projects",
        json={
            "source_title": "Project X",
            "target_duration_seconds": 900,
            "material_id": "realistic",
            "chapter_count": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == "project-1"
    assert len(payload["chapters"]) == 3
    assert payload["stream_ids"] == ["stream-1", "stream-2", "stream-3"]
    assert stream_ids == ["chapter-1", "chapter-2", "chapter-3"]


def test_overview_endpoint(monkeypatch):
    monkeypatch.setattr(control_api, "list_lanes", lambda: [{"lane_id": "lane-01", "status": "idle"}])
    monkeypatch.setattr(control_api, "list_projects", lambda: [{"id": "project-1", "status": "draft"}])
    monkeypatch.setattr(control_api, "list_chapters", lambda: [{"id": "chapter-1", "status": "planned"}])
    monkeypatch.setattr(control_api, "list_jobs", lambda: [{"id": "job-1", "status": "queued"}])
    monkeypatch.setattr(control_api, "queue_depths", lambda: {"chapters:pending": 1, "lane:01:jobs": 2})
    client = TestClient(control_api.app)

    response = client.get("/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["lane_count"] == 1
    assert payload["summary"]["project_count"] == 1
    assert payload["queues"]["chapters:pending"] == 1


def test_dashboard_endpoint_returns_html():
    client = TestClient(control_api.app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "FlowKit Control Dashboard" in response.text
    assert "Raw Queue Metrics" in response.text
