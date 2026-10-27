"""Regression tests for the public Flow native video export API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from agent.api import flow as api


@pytest.mark.asyncio
async def test_export_uses_session_project_and_returns_polling_descriptor():
    client = MagicMock(connected=True)
    client.upscale_video = AsyncMock(return_value={
        "status": 200,
        "data": {"workflows": [{"name": "upscale-job", "primary_media_id": "video_upscaled"}]},
    })
    with (
        patch.object(api, "get_flow_client", return_value=client),
        patch.object(api, "ensure_session_project", new_callable=AsyncMock) as session,
    ):
        session.return_value = {"project_id": "project-123"}
        result = await api.export_video(api.ExportVideoRequest(media_id="video"))

    client.upscale_video.assert_awaited_once_with(
        media_id="video", scene_id="export",
        aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
        resolution="VIDEO_RESOLUTION_1080P",
        project_id="project-123",
    )
    assert result["flowkitPolling"]["mode"] == "media_redirect"
    assert result["flowkitPolling"]["workflows"][0]["primary_media_id"] == "video_upscaled"
    assert result["export"]["check_status_mode"] == "export"


@pytest.mark.asyncio
async def test_export_with_explicit_project_does_not_allocate_session():
    client = MagicMock(connected=True)
    client.upscale_video = AsyncMock(return_value={"status": 200, "data": {"workflows": []}})
    with (
        patch.object(api, "get_flow_client", return_value=client),
        patch.object(api, "ensure_session_project", new_callable=AsyncMock) as session,
    ):
        await api.export_video(api.ExportVideoRequest(media_id="video", project_id="existing-project"))
    session.assert_not_awaited()
    assert client.upscale_video.await_args.kwargs["project_id"] == "existing-project"


@pytest.mark.asyncio
async def test_export_polls_through_shared_batch_media_resolver():
    client = MagicMock(connected=True)
    with (
        patch.object(api, "get_flow_client", return_value=client),
        patch.object(api, "check_workflow_status", new_callable=AsyncMock) as polling,
    ):
        polling.return_value = {"status": "COMPLETED", "done": True, "workflows": []}
        response = await api.check_status(api.CheckStatusRequest(
            mode="export",
            project_id="existing-project",
            workflows=[{"name": "job", "primary_media_id": "video_upscaled"}],
        ))
    assert response["download_ready"] is True
    assert polling.await_args.kwargs["mode"] == "media_redirect"
    assert polling.await_args.kwargs["project_id"] == "existing-project"


@pytest.mark.asyncio
async def test_export_surfaces_provider_error():
    client = MagicMock(connected=True)
    client.upscale_video = AsyncMock(return_value={"status": 403, "error": "plan required"})
    with patch.object(api, "get_flow_client", return_value=client):
        with pytest.raises(HTTPException) as exc:
            await api.export_video(api.ExportVideoRequest(media_id="video", project_id="project-123"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_export_fails_cleanly_without_browser_connection():
    with patch.object(api, "get_flow_client", return_value=MagicMock(connected=False)):
        with pytest.raises(HTTPException) as exc:
            await api.export_video(api.ExportVideoRequest(media_id="video"))
    assert exc.value.status_code == 503
