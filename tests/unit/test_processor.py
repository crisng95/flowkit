"""Unit tests for agent/worker/processor.py — heavy mocking of crud, flow_client, operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent.worker.processor import (
    _is_already_completed,
    _mark_scene_failed,
    _handle_failure,
)
from agent.config import MAX_RETRIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_req(
    req_type="GENERATE_IMAGE",
    scene_id="scene-001",
    orientation="VERTICAL",
    retry_count=0,
    rid="aaaaaaaa-bbbb-cccc-dddd-000000000001",
    character_id=None,
    **extra,
):
    d = {
        "id": rid,
        "type": req_type,
        "scene_id": scene_id,
        "character_id": character_id,
        "orientation": orientation,
        "retry_count": retry_count,
        "project_id": "proj-001",
        "video_id": "video-001",
    }
    d.update(extra)
    return d


# ---------------------------------------------------------------------------
# _is_already_completed
# ---------------------------------------------------------------------------

class TestIsAlreadyCompleted:
    @pytest.mark.asyncio
    async def test_returns_true_when_vertical_image_completed(self, sample_scene_row):
        """Should return True when vertical_image_status is COMPLETED."""
        req = make_req(req_type="GENERATE_IMAGE", scene_id="scene-001")
        # sample_scene_row has vertical_image_status = "COMPLETED"
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.get_scene = AsyncMock(return_value=sample_scene_row)
            result = await _is_already_completed(req, "VERTICAL")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_vertical_image_pending(self, sample_scene_row):
        """Should return False when vertical_image_status is PENDING."""
        pending_scene = {**sample_scene_row, "vertical_image_status": "PENDING"}
        req = make_req(req_type="GENERATE_IMAGE", scene_id="scene-001")
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.get_scene = AsyncMock(return_value=pending_scene)
            result = await _is_already_completed(req, "VERTICAL")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_generate_character_image_without_media_id(self):
        """GENERATE_CHARACTER_IMAGE should return False if character has no media_id."""
        req = make_req(req_type="GENERATE_CHARACTER_IMAGE", character_id="char-001")
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.get_character = AsyncMock(return_value={"id": "char-001", "media_id": None})
            result = await _is_already_completed(req, "VERTICAL")
        assert result is False
        mock_crud.get_character.assert_called_once_with("char-001")

    @pytest.mark.asyncio
    async def test_returns_true_for_generate_character_image_with_media_id(self):
        """GENERATE_CHARACTER_IMAGE should return True if character already has media_id."""
        req = make_req(req_type="GENERATE_CHARACTER_IMAGE", character_id="char-001")
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.get_character = AsyncMock(return_value={"id": "char-001", "media_id": "uuid-1234"})
            result = await _is_already_completed(req, "VERTICAL")
        assert result is True
        mock_crud.get_character.assert_called_once_with("char-001")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_scene_id(self):
        """If scene_id is missing, should return False without querying DB."""
        req = make_req(req_type="GENERATE_IMAGE", scene_id=None)
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.get_scene = AsyncMock()
            result = await _is_already_completed(req, "VERTICAL")
        assert result is False
        mock_crud.get_scene.assert_not_called()

    @pytest.mark.asyncio
    async def test_edit_image_never_skipped_even_when_image_completed(self, sample_scene_row):
        """EDIT_IMAGE should always run — it replaces the existing image."""
        req = make_req(req_type="EDIT_IMAGE", scene_id="scene-001")
        # sample_scene_row has vertical_image_status = "COMPLETED"
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.get_scene = AsyncMock(return_value=sample_scene_row)
            result = await _is_already_completed(req, "VERTICAL")
        assert result is False


# ---------------------------------------------------------------------------
# _mark_scene_failed
# ---------------------------------------------------------------------------

class TestMarkSceneFailed:
    @pytest.mark.asyncio
    async def test_sets_vertical_image_status_failed_for_generate_image(self):
        req = make_req(req_type="GENERATE_IMAGE", scene_id="scene-001", orientation="VERTICAL")
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_scene = AsyncMock()
            await _mark_scene_failed(req)
        mock_crud.update_scene.assert_awaited_once_with("scene-001", vertical_image_status="FAILED")

    @pytest.mark.asyncio
    async def test_sets_vertical_video_status_failed_for_generate_video(self):
        req = make_req(req_type="GENERATE_VIDEO", scene_id="scene-001", orientation="VERTICAL")
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_scene = AsyncMock()
            await _mark_scene_failed(req)
        mock_crud.update_scene.assert_awaited_once_with("scene-001", vertical_video_status="FAILED")

    @pytest.mark.asyncio
    async def test_sets_vertical_upscale_status_failed_for_upscale_video(self):
        req = make_req(req_type="UPSCALE_VIDEO", scene_id="scene-001", orientation="VERTICAL")
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_scene = AsyncMock()
            await _mark_scene_failed(req)
        mock_crud.update_scene.assert_awaited_once_with("scene-001", vertical_upscale_status="FAILED")

    @pytest.mark.asyncio
    async def test_no_update_when_no_scene_id(self):
        req = make_req(req_type="GENERATE_IMAGE", scene_id=None)
        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_scene = AsyncMock()
            await _mark_scene_failed(req)
        mock_crud.update_scene.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_failure
# ---------------------------------------------------------------------------

class TestHandleFailure:
    @pytest.mark.asyncio
    async def test_retries_when_under_max_retries(self):
        """When retry_count+1 < MAX_RETRIES, request should go back to PENDING."""
        req = make_req(retry_count=0)
        rid = req["id"]
        result = {"error": "timeout"}

        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_request = AsyncMock()
            mock_crud.update_scene = AsyncMock()
            await _handle_failure(rid, req, result)

        mock_crud.update_request.assert_awaited_once()
        call_kwargs = mock_crud.update_request.call_args
        assert call_kwargs[0][0] == rid
        assert call_kwargs[1]["status"] == "PENDING"
        assert call_kwargs[1]["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_marks_failed_when_at_max_retries(self):
        """When retry_count+1 >= MAX_RETRIES, request + scene should be marked FAILED."""
        req = make_req(req_type="GENERATE_IMAGE", scene_id="scene-001", retry_count=MAX_RETRIES - 1)
        rid = req["id"]
        result = {"error": "permanent failure"}

        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_request = AsyncMock()
            mock_crud.update_scene = AsyncMock()
            await _handle_failure(rid, req, result)

        mock_crud.update_request.assert_awaited_once()
        call_kwargs = mock_crud.update_request.call_args
        assert call_kwargs[0][0] == rid
        assert call_kwargs[1]["status"] == "FAILED"
        # Scene should also be marked failed
        mock_crud.update_scene.assert_awaited_once_with("scene-001", vertical_image_status="FAILED")

    @pytest.mark.asyncio
    async def test_unusual_activity_is_not_retried_as_captcha(self):
        """Google unusual-activity blocks must stop instead of entering the CAPTCHA retry loop."""
        req = make_req(req_type="GENERATE_VIDEO", scene_id="scene-001", retry_count=0)
        rid = req["id"]
        result = {"error": "reCAPTCHA evaluation failed [PUBLIC_ERROR_UNUSUAL_ACTIVITY]"}

        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_request = AsyncMock()
            mock_crud.update_scene = AsyncMock()
            await _handle_failure(rid, req, result)

        call_kwargs = mock_crud.update_request.call_args
        assert call_kwargs[0][0] == rid
        assert call_kwargs[1]["status"] == "FAILED"
        assert "retry_count" not in call_kwargs[1]
        mock_crud.update_scene.assert_awaited_once_with("scene-001", vertical_video_status="FAILED")

    @pytest.mark.asyncio
    async def test_extracts_error_message_from_nested_data(self):
        """Error message extraction from data.error.message should work."""
        req = make_req(retry_count=MAX_RETRIES - 1)
        rid = req["id"]
        result = {
            "data": {
                "error": {
                    "code": 403,
                    "message": "caller does not have permission",
                }
            }
        }

        with patch("agent.worker.processor.crud") as mock_crud:
            mock_crud.update_request = AsyncMock()
            mock_crud.update_scene = AsyncMock()
            await _handle_failure(rid, req, result)

        call_kwargs = mock_crud.update_request.call_args
        assert "caller does not have permission" in call_kwargs[1]["error_message"]
