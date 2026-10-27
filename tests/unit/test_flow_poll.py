from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent.services.flow_poll as polling
from agent.services.flow_client import FlowClient
from agent.services.flow_poll import annotate_polling, check_workflow_status

MEDIA = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_annotate_export_polling_uses_workflow_primary_media_id():
    result = {
        "status": 200,
        "data": {
            "workflows": [
                {"name": "wf-1", "metadata": {"primaryMediaId": MEDIA + "_upsampled"}}
            ]
        },
    }
    annotated = annotate_polling(result, mode="media_redirect")
    assert annotated["data"]["flowkitPolling"] == {
        "mode": "media_redirect",
        "workflows": [
            {"name": "wf-1", "primary_media_id": MEDIA + "_upsampled"}
        ],
    }


@pytest.mark.asyncio
async def test_batch_poll_resolves_completed_media_through_public_resolver():
    client = MagicMock()
    client.resolve_media_url = AsyncMock(return_value={
        "status": 200,
        "data": {
            "url": "https://flow-content.google/video/out?Signature=test",
            "contentType": "video/mp4",
        },
    })
    with patch("agent.services.flow_poll.get_flow_client", return_value=client):
        result = await check_workflow_status(
            [{"name": "wf-1", "primary_media_id": MEDIA + "_upsampled"}],
            mode="media_redirect",
        )

    assert result["done"] is True
    assert result["status"] == "COMPLETED"
    assert result["workflows"][0]["media"]["resolved_via"] == "as29s"
    client.resolve_media_url.assert_awaited_once_with(MEDIA + "_upsampled")


@pytest.mark.asyncio
async def test_batch_poll_stays_pending_until_video_url_exists():
    client = MagicMock()
    client.resolve_media_url = AsyncMock(return_value={
        "status": 404,
        "error": "not ready",
        "data": {},
    })
    with patch("agent.services.flow_poll.get_flow_client", return_value=client):
        result = await check_workflow_status(
            [{"name": "wf-1", "primary_media_id": MEDIA + "_upsampled"}],
            mode="media_redirect",
        )

    assert result["done"] is False
    assert result["status"] == "PENDING"
    assert result["workflows"][0]["status"] == "PENDING"


def test_unknown_poll_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown Flow polling mode"):
        annotate_polling({"data": {"workflows": []}}, mode="mystery")


@pytest.mark.asyncio
async def test_flow_client_media_resolver_uses_get_media_on_batch():
    client = FlowClient()
    client.get_media = AsyncMock(return_value={
        "status": 200,
        "data": {"video": {"fifeUrl": "https://flow-content.google/video/media-1?sig=x"}},
    })

    result = await client.resolve_media_url("media-1")

    assert result["data"]["url"].startswith("https://flow-content.google/video/")
    assert result["data"]["contentType"] == "video/mp4"
    client.get_media.assert_awaited_once_with("media-1")
