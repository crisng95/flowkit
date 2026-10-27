"""Unit tests for Gemini Omni Flash Flow submissions and workflow polling.

Every mode here runs on the flow.google.com batch path; the REST implementations
they used to shadow went with the transport. The wire-contract tests lock the
captured envelopes — rpc id, model key and slot order — because a payload that
submits but is shaped wrong buys a render and returns the wrong clip.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent.services.omni_flash as omni_flash
from agent.services.omni_flash import (
    OMNI_FLASH_MAX_REFERENCE_IMAGES,
    _load_model_key,
    check_omni_flash_status,
    extract_omni_workflows,
    generate_omni_flash_first_frame_video,
    generate_omni_flash_first_last_video,
    generate_omni_flash_text_video,
    generate_omni_flash_video,
)


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (4, "abra_r2v_4s"),
        (6, "abra_r2v_6s"),
        (8, "abra_r2v_8s"),
        (10, "abra_r2v_10s"),
    ],
)
def test_omni_reference_duration_model_keys(duration, expected):
    assert _load_model_key(duration) == expected


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (4, "abra_i2v_4s"),
        (6, "abra_i2v_6s"),
        (8, "abra_i2v_8s"),
        (10, "abra_i2v_10s"),
    ],
)
def test_omni_first_frame_model_keys(duration, expected):
    assert _load_model_key(duration, mode="frame_to_video") == expected


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (4, "abra_i2v_4s"),
        (6, "abra_i2v_6s"),
        (8, "abra_i2v_8s"),
        (10, "abra_i2v_10s"),
    ],
)
def test_omni_first_last_model_keys_are_independently_configured(duration, expected):
    assert _load_model_key(duration, mode="start_end_frame_to_video") == expected


def test_invalid_duration_fails_before_submit():
    with pytest.raises(ValueError, match="duration 5s is unsupported"):
        _load_model_key(5)


def test_extract_omni_workflows_uses_primary_media_id():
    result = {
        "status": 200,
        "data": {
            "operations": [
                {
                    "operation": {"name": "operation-looking-handle"},
                    "status": "MEDIA_GENERATION_STATUS_PENDING",
                }
            ],
            "workflows": [
                {
                    "name": "workflow-1",
                    "metadata": {"primaryMediaId": "media-1"},
                }
            ],
        },
    }
    assert extract_omni_workflows(result) == [
        {"name": "workflow-1", "primary_media_id": "media-1"}
    ]


@pytest.mark.asyncio
async def test_batch_text_video_builds_4s_yhhmef_submit(monkeypatch):
    client = MagicMock()
    client._batch_project_id.return_value = "11111111-2222-3333-4444-555555555555"
    client._batch_payload = AsyncMock(return_value=[
        None,
        10,
        [],
        [[
            "22222222-3333-4444-5555-666666666666",
            "11111111-2222-3333-4444-555555555555",
            "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
            "CAE",
        ]],
    ])

    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await generate_omni_flash_text_video(
            prompt="A red paper boat drifts across a pond",
            project_id="11111111-2222-3333-4444-555555555555",
            duration_s=4,
            aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
        )

    assert result["status"] == 200
    assert result["data"]["model"] == "abra_t2v_4s"
    assert result["data"]["duration_s"] == 4
    assert result["data"]["flowkitPolling"]["mode"] == "batch_media"
    assert result["data"]["flowkitPolling"]["workflows"][0]["primary_media_id"] == (
        "22222222-3333-4444-5555-666666666666"
    )
    rpcid, freq, captcha = client._batch_payload.await_args.args[:3]
    assert rpcid == omni_flash.fb.RPC_GEN_VIDEO_TEXT
    assert captcha == omni_flash.fb.CAPTCHA_VIDEO
    payload = __import__("json").loads(__import__("json").loads(freq)[0][0][1])
    assert payload[0][0][1] == "abra_t2v_4s"
    assert payload[0][0][2] == omni_flash.fb.VIDEO_ASPECT_LANDSCAPE


@pytest.mark.asyncio
async def test_batch_first_frame_video_uses_eb1hjf_abra_i2v(monkeypatch):
    client = MagicMock()
    pid = "11111111-2222-3333-4444-555555555555"
    client._batch_project_id.return_value = pid
    client._batch_payload = AsyncMock(return_value=[
        None,
        50,
        [["op-omni-1", pid, "scene-1", None]],
    ])

    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await generate_omni_flash_first_frame_video(
            start_image_media_id="media-start",
            prompt="Three children clap gently",
            project_id=pid,
            duration_s=6,
            aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE",
        )

    assert result["status"] == 200
    assert result["data"]["model"] == "abra_i2v_6s"
    assert result["data"]["duration_s"] == 6
    assert result["data"]["flowkitPolling"]["mode"] == "batch_operation"
    assert result["data"]["flowkitPolling"]["project_id"] == pid
    assert result["data"]["operations"][0]["operation"]["name"] == "op-omni-1"
    client._remember_operation.assert_called_once_with("op-omni-1", pid)

    rpcid, freq, captcha = client._batch_payload.await_args.args[:3]
    assert rpcid == omni_flash.fb.RPC_GEN_VIDEO
    assert captcha == omni_flash.fb.CAPTCHA_VIDEO
    payload = __import__("json").loads(__import__("json").loads(freq)[0][0][1])
    request = payload[0][0]
    assert request[0][2][0][0][0] == "Three children clap gently"
    assert request[1] == "abra_i2v_6s"
    assert request[2] == omni_flash.fb.VIDEO_ASPECT_LANDSCAPE
    assert request[4][1] == "media-start"


@pytest.mark.asyncio
async def test_first_frame_rejects_missing_start_before_submit():
    with pytest.raises(ValueError, match="requires start_image_media_id"):
        await generate_omni_flash_first_frame_video(
            start_image_media_id="",
            prompt="test",
            project_id="p",
        )


@pytest.mark.asyncio
async def test_first_last_rejects_missing_end_before_submit():
    with pytest.raises(ValueError, match="non-empty end_image_media_id"):
        await generate_omni_flash_first_last_video(
            start_image_media_id="start",
            end_image_media_id="",
            prompt="test",
            project_id="p",
        )


@pytest.mark.asyncio
async def test_batch_omni_poll_uses_as29s_media():
    client = MagicMock()
    client.resolve_media_url = AsyncMock(return_value={
        "status": 200,
        "data": {
            "url": "https://flow-content.google/video/media-1?Signature=test",
            "contentType": "video/mp4",
        },
    })
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await check_omni_flash_status([{
            "name": "workflow-1", "primary_media_id": "media-1", "project_id": "project-1",
        }])

    assert result["done"] is True
    assert result["status"] == "COMPLETED"
    assert result["workflows"][0]["media"]["resolved_via"] == "as29s"
    client.resolve_media_url.assert_awaited_once_with("media-1")


@pytest.mark.asyncio
async def test_batch_poll_hands_back_signed_url_without_buffering():
    client = MagicMock()
    client.resolve_media_url = AsyncMock(return_value={
        "status": 200, "data": {
            "url": "https://flow-content.google/video/media-1?Signature=test",
            "contentType": "video/mp4",
        },
    })
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await check_omni_flash_status(
            [{"name": "workflow-1", "primary_media_id": "media-1"}],
            include_encoded_video=True, project_id="project-1",
        )
    media = result["workflows"][0]["media"]
    assert result["done"] is True
    assert media["url"].startswith("https://flow-content.google/video/")
    assert media["encoded_video_available"] is False
    assert media["encoded_video"] is None
    client.resolve_media_url.assert_awaited_once_with("media-1")


@pytest.mark.asyncio
async def test_batch_poll_treats_a_media_record_without_video_as_pending():
    client = MagicMock()
    client.resolve_media_url = AsyncMock(return_value={
        "status": 200, "data": {"url": None, "contentType": None},
    })
    with patch("agent.services.omni_flash.get_flow_client", return_value=client):
        result = await check_omni_flash_status(
            [{"name": "workflow-1", "primary_media_id": "media-1"}],
            project_id="project-1",
        )
    assert result["done"] is False
    assert result["workflows"][0]["status"] == "PENDING"


@pytest.mark.asyncio
async def test_submit_rejects_more_than_seven_references():
    refs = [f"ref-{i}" for i in range(OMNI_FLASH_MAX_REFERENCE_IMAGES + 1)]

    with pytest.raises(ValueError, match="at most 7 reference images"):
        await generate_omni_flash_video(
            reference_media_ids=refs,
            prompt="test",
            project_id="p",
            duration_s=8,
        )


@pytest.mark.asyncio
async def test_submit_rejects_empty_reference_set():
    with pytest.raises(ValueError, match="requires at least one reference image"):
        await generate_omni_flash_video(
            reference_media_ids=[],
            prompt="test",
            project_id="p",
            duration_s=8,
        )


class TestMigratedOmniReferenceBatchModes:

    @pytest.fixture
    def client(self):
        with patch("agent.services.omni_flash.get_flow_client") as factory:
            stub = MagicMock()
            pid = "11111111-2222-3333-4444-555555555555"
            stub._batch_project_id.return_value = pid
            stub._batch_payload = AsyncMock(return_value=[
                None, 50, [["op-ref-1", pid, "scene-1", None]],
            ])
            factory.return_value = stub
            yield stub

    async def test_first_last_uses_nprqif_and_batch_operation_polling(self, client):
        result = await generate_omni_flash_first_last_video(
            start_image_media_id="start", end_image_media_id="end",
            prompt="morph", project_id="pid", duration_s=4,
            resolution="360p", aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE")
        assert result["status"] == 200
        assert result["data"]["model"] == "omni_flash_i2v_4s_first_last_360p"
        assert result["data"]["resolution"] == "360p"
        assert result["data"]["flowkitPolling"]["mode"] == "batch_operation"
        rpcid, freq, captcha = client._batch_payload.await_args.args[:3]
        assert rpcid == omni_flash.fb.RPC_GEN_VIDEO_FIRST_LAST
        assert captcha == omni_flash.fb.CAPTCHA_VIDEO
        payload = __import__("json").loads(__import__("json").loads(freq)[0][0][1])
        req = payload[0][0]
        assert req[1] == "omni_flash_i2v_4s_first_last_360p"
        assert req[4][1] == "start"
        assert req[5][1] == "end"
        client._remember_operation.assert_called_once_with(
            "op-ref-1", "11111111-2222-3333-4444-555555555555")

    async def test_seven_references_submit_rather_than_trip_the_validator(self, client):
        """Seven is the limit, not one past it. This used to assert the
        capability gap; now that r2v submits, it has to reach the wire —
        otherwise an off-by-one in the validator looks like a Flow refusal."""
        refs = [f"ref-{i}" for i in range(OMNI_FLASH_MAX_REFERENCE_IMAGES)]
        result = await generate_omni_flash_video(
            reference_media_ids=refs, prompt="seven", project_id="pid",
            duration_s=4, resolution="720p")
        assert result["status"] == 200
        _rpcid, freq, _captcha = client._batch_payload.await_args.args[:3]
        payload = __import__("json").loads(__import__("json").loads(freq)[0][0][1])
        assert payload[0][0][1] == [[None, r] for r in refs]

    async def test_reference_to_video_uses_mzza6b_and_all_references(self, client):
        result = await generate_omni_flash_video(
            reference_media_ids=["a", "b", "c"], prompt="keep all refs",
            project_id="pid", duration_s=6, resolution="720p",
            aspect_ratio="VIDEO_ASPECT_RATIO_PORTRAIT")
        assert result["status"] == 200
        assert result["data"]["model"] == "abra_r2v_6s"
        assert result["data"]["flowkitPolling"]["mode"] == "batch_operation"
        rpcid, freq, _captcha = client._batch_payload.await_args.args[:3]
        assert rpcid == omni_flash.fb.RPC_GEN_VIDEO_REFERENCES
        payload = __import__("json").loads(__import__("json").loads(freq)[0][0][1])
        req = payload[0][0]
        assert req[1] == [[None, "a"], [None, "b"], [None, "c"]]
        assert req[2] == "abra_r2v_6s"
        assert req[3] == omni_flash.fb.VIDEO_ASPECT_PORTRAIT

    async def test_reference_360p_uses_live_wire_model_and_quality_slot(self, client):
        await generate_omni_flash_video(
            reference_media_ids=["a", "b"], prompt="refs", project_id="pid",
            duration_s=4, resolution="360p",
            aspect_ratio="VIDEO_ASPECT_RATIO_LANDSCAPE")
        _rpcid, freq, _captcha = client._batch_payload.await_args.args[:3]
        payload = __import__("json").loads(__import__("json").loads(freq)[0][0][1])
        req = payload[0][0]
        assert req[2] == "abra_r2v_4s_360p"
        assert req[-1] == [4]

    async def test_invalid_resolution_is_rejected_before_submit(self, client):
        with pytest.raises(ValueError, match="resolution must be 360p or 720p"):
            await generate_omni_flash_first_frame_video(
                start_image_media_id="a", prompt="go", project_id="pid",
                resolution="1080p")
        client._batch_payload.assert_not_called()
