"""Omni 1.2 Flash (Flow codename ``macaron_cookie``) wire contract.

t2v and First+Last keys were live-captured from flow.google.com on
2026-11-06; first-frame (i2v) and Ingredients (r2v) follow the 1.1 naming and
were confirmed by real 3s/360p generations. 1.2 reuses the 1.1 envelopes, so
these tests lock the key per mode plus the 3-15s duration range, and that
omitting ``omni_version`` keeps the 1.1 keys.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent.services.omni_flash as omni_flash
from agent.services.omni_flash import (
    generate_omni_flash_first_frame_video,
    generate_omni_flash_first_last_video,
    generate_omni_flash_text_video,
    generate_omni_flash_video,
    omni12_model_key,
)

PID = "11111111-2222-3333-4444-555555555555"


def _request(freq: str) -> list:
    return json.loads(json.loads(freq)[0][0][1])[0][0]


def _operation_client():
    client = MagicMock()
    client._batch_project_id.return_value = PID
    client._batch_payload = AsyncMock(return_value=[None, 50, [["op-12", PID, "s", None]]])
    return client


@pytest.mark.parametrize(
    ("mode", "duration", "resolution", "expected"),
    [
        ("t2v", 3, "360p", "macaron_cookie_t2v_3s_360p"),
        ("t2v", 15, "720p", "macaron_cookie_t2v_15s"),
        ("first_frame", 5, "720p", "macaron_cookie_i2v_5s"),
        ("first_last", 3, "360p", "macaron_cookie_i2v_fl_3s_360p"),
        ("r2v", 12, "360p", "macaron_cookie_r2v_12s_360p"),
    ],
)
def test_omni12_model_keys(mode, duration, resolution, expected):
    assert omni12_model_key(mode, duration, resolution) == expected


@pytest.mark.parametrize("duration", [2, 16])
def test_omni12_rejects_durations_outside_3_to_15(duration):
    with pytest.raises(ValueError, match="3-15"):
        omni12_model_key("t2v", duration, "720p")


@pytest.mark.asyncio
async def test_omni12_first_last_uses_nprqif_with_macaron_key():
    client = _operation_client()
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await generate_omni_flash_first_last_video(
            start_image_media_id="media-start",
            end_image_media_id="media-end",
            prompt="run across the bridge",
            project_id=PID,
            duration_s=3,
            resolution="360p",
            aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
            omni_version="1.2",
        )
    assert result["status"] == 200
    assert result["data"]["model"] == "macaron_cookie_i2v_fl_3s_360p"
    rpcid, freq = client._batch_payload.await_args.args[:2]
    assert rpcid == omni_flash.fb.RPC_GEN_VIDEO_FIRST_LAST
    request = _request(freq)
    assert request[1] == "macaron_cookie_i2v_fl_3s_360p"
    assert request[4][1] == "media-start"
    assert request[5][1] == "media-end"


@pytest.mark.asyncio
async def test_omni12_first_frame_uses_eb1hjf_with_macaron_key():
    client = _operation_client()
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await generate_omni_flash_first_frame_video(
            start_image_media_id="media-start",
            prompt="p",
            project_id=PID,
            duration_s=7,
            aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
            omni_version="1.2",
        )
    assert result["data"]["model"] == "macaron_cookie_i2v_7s"
    rpcid, freq = client._batch_payload.await_args.args[:2]
    assert rpcid == omni_flash.fb.RPC_GEN_VIDEO
    assert _request(freq)[1] == "macaron_cookie_i2v_7s"


@pytest.mark.asyncio
async def test_omni12_reference_uses_mzza6b_with_macaron_key():
    client = _operation_client()
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await generate_omni_flash_video(
            reference_media_ids=["ref-a", "ref-b"],
            prompt="p",
            project_id=PID,
            duration_s=3,
            resolution="360p",
            aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
            omni_version="1.2",
        )
    assert result["data"]["model"] == "macaron_cookie_r2v_3s_360p"
    rpcid, freq = client._batch_payload.await_args.args[:2]
    assert rpcid == omni_flash.fb.RPC_GEN_VIDEO_REFERENCES
    request = _request(freq)
    assert request[1] == [[None, "ref-a"], [None, "ref-b"]]
    assert request[2] == "macaron_cookie_r2v_3s_360p"


@pytest.mark.asyncio
async def test_omni12_text_video_uses_macaron_key():
    client = MagicMock()
    client._batch_project_id.return_value = PID
    client._batch_payload = AsyncMock(return_value=[
        None, 10, [], [["22222222-3333-4444-5555-666666666666", PID, "x", "CAE"]],
    ])
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await generate_omni_flash_text_video(
            prompt="p", project_id=PID, duration_s=15,
            aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE", omni_version="1.2",
        )
    assert result["data"]["model"] == "macaron_cookie_t2v_15s"
    assert _request(client._batch_payload.await_args.args[1])[1] == "macaron_cookie_t2v_15s"


@pytest.mark.asyncio
async def test_default_version_keeps_omni_11_keys_and_durations():
    client = _operation_client()
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await generate_omni_flash_first_last_video(
            start_image_media_id="a", end_image_media_id="b", prompt="p",
            project_id=PID, duration_s=4, aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
        )
        with pytest.raises(ValueError, match="unsupported"):
            await generate_omni_flash_first_last_video(
                start_image_media_id="a", end_image_media_id="b", prompt="p",
                project_id=PID, duration_s=3, aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
            )
    assert result["data"]["model"] == "omni_flash_i2v_4s_first_last"
