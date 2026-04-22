"""Unit tests for agent/sdk/services/operations.py — OperationService."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent.sdk.services import operations as ops_module
from agent.sdk.services.operations import OperationService, init_operations, get_operations


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_UUID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_UUID_2 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
PROJECT_ID = "proj-001"
SCENE_ID = "scene-001"
VIDEO_ID = "video-001"
CHAR_ID = "char-001"


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level _ops singleton between tests."""
    ops_module._ops = None
    yield
    ops_module._ops = None


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.generate_images = AsyncMock(return_value={
        "data": {
            "media": [{
                "name": SAMPLE_UUID,
                "image": {
                    "generatedImage": {
                        "mediaId": SAMPLE_UUID,
                        "fifeUrl": f"https://lh3.googleusercontent.com/image/{SAMPLE_UUID}?sqp=params",
                    }
                }
            }]
        }
    })
    client.edit_image = AsyncMock(return_value={
        "data": {
            "media": [{"name": SAMPLE_UUID}]
        }
    })
    client.upload_image = AsyncMock(return_value={"_mediaId": SAMPLE_UUID_2})
    return client


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_client, mock_repo):
    return OperationService(flow_client=mock_client, repo=mock_repo)


@pytest.fixture
def base_scene():
    return {
        "id": SCENE_ID,
        "_project_id": PROJECT_ID,
        "prompt": "Hero walks into the castle at dawn",
        "image_prompt": None,
        "video_prompt": "0-3s: Hero walks in. 3-6s: Looks around. 6-8s: Close-up.",
        "character_names": '["Hero", "Castle"]',
        "vertical_image_media_id": SAMPLE_UUID,
        "horizontal_image_media_id": None,
        "vertical_end_scene_media_id": None,
    }


# ---------------------------------------------------------------------------
# Test: generate_scene_image
# ---------------------------------------------------------------------------

class TestGenerateSceneImage:
    @pytest.mark.asyncio
    async def test_calls_generate_images_with_correct_args(self, service, base_scene, mock_client):
        """generate_scene_image calls client.generate_images with correct prompt and aspect_ratio."""
        base_scene["character_names"] = None  # skip character resolution
        project = {"user_paygate_tier": "PAYGATE_TIER_ONE"}

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.get_project_characters = AsyncMock(return_value=[])

            result = await service.generate_scene_image(base_scene, "VERTICAL")

        mock_client.generate_images.assert_called_once()
        call_kwargs = mock_client.generate_images.call_args.kwargs
        assert call_kwargs["aspect_ratio"] == "IMAGE_ASPECT_RATIO_PORTRAIT"
        assert call_kwargs["prompt"] == base_scene["prompt"]
        assert call_kwargs["project_id"] == PROJECT_ID
        assert "data" in result

    @pytest.mark.asyncio
    async def test_resolves_character_media_ids_from_project(self, service, base_scene, mock_client):
        """generate_scene_image collects media_ids from project chars matching character_names."""
        project = {"user_paygate_tier": "PAYGATE_TIER_TWO"}
        project_chars = [
            {"name": "Hero", "media_id": SAMPLE_UUID},
            {"name": "Castle", "media_id": SAMPLE_UUID_2},
            {"name": "Other", "media_id": "cccccccc-dddd-eeee-ffff-000000000000"},
        ]

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.get_project_characters = AsyncMock(return_value=project_chars)

            await service.generate_scene_image(base_scene, "VERTICAL")

        call_kwargs = mock_client.generate_images.call_args.kwargs
        char_ids = call_kwargs["character_media_ids"]
        assert SAMPLE_UUID in char_ids
        assert SAMPLE_UUID_2 in char_ids
        # "Other" is not in character_names, should not be included
        assert "cccccccc-dddd-eeee-ffff-000000000000" not in char_ids

    @pytest.mark.asyncio
    async def test_returns_error_when_character_refs_missing_media_id(self, service, base_scene):
        """generate_scene_image returns error dict when a referenced character has no media_id."""
        project = {"user_paygate_tier": "PAYGATE_TIER_ONE"}
        project_chars = [
            {"name": "Hero", "media_id": None},     # missing
            {"name": "Castle", "media_id": SAMPLE_UUID_2},
        ]

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.get_project_characters = AsyncMock(return_value=project_chars)

            result = await service.generate_scene_image(base_scene, "VERTICAL")

        assert "error" in result
        assert "Hero" in result["error"]

    @pytest.mark.asyncio
    async def test_uses_landscape_for_horizontal_orientation(self, service, base_scene, mock_client):
        """generate_scene_image passes LANDSCAPE aspect_ratio for HORIZONTAL orientation."""
        base_scene["character_names"] = None

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value={"user_paygate_tier": "PAYGATE_TIER_TWO"})
            mock_crud.get_project_characters = AsyncMock(return_value=[])

            await service.generate_scene_image(base_scene, "HORIZONTAL")

        call_kwargs = mock_client.generate_images.call_args.kwargs
        assert call_kwargs["aspect_ratio"] == "IMAGE_ASPECT_RATIO_LANDSCAPE"


# ---------------------------------------------------------------------------
# Test: edit_scene_image
# ---------------------------------------------------------------------------

class TestEditSceneImage:
    @pytest.mark.asyncio
    async def test_calls_edit_image_with_source_media_id(self, service, base_scene, mock_client):
        """edit_scene_image calls client.edit_image with the provided source_media_id."""
        project = {"user_paygate_tier": "PAYGATE_TIER_ONE"}

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.get_project_characters = AsyncMock(return_value=[])

            result = await service.edit_scene_image(base_scene, "VERTICAL", source_media_id=SAMPLE_UUID)

        mock_client.edit_image.assert_called_once()
        call_kwargs = mock_client.edit_image.call_args.kwargs
        assert call_kwargs["source_media_id"] == SAMPLE_UUID
        assert call_kwargs["aspect_ratio"] == "IMAGE_ASPECT_RATIO_PORTRAIT"

    @pytest.mark.asyncio
    async def test_falls_back_to_scene_image_media_id(self, service, base_scene, mock_client):
        """edit_scene_image uses vertical_image_media_id from scene when no source provided."""
        project = {"user_paygate_tier": "PAYGATE_TIER_ONE"}

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.get_project_characters = AsyncMock(return_value=[])

            result = await service.edit_scene_image(base_scene, "VERTICAL", source_media_id=None)

        mock_client.edit_image.assert_called_once()
        call_kwargs = mock_client.edit_image.call_args.kwargs
        assert call_kwargs["source_media_id"] == SAMPLE_UUID  # from scene["vertical_image_media_id"]

    @pytest.mark.asyncio
    async def test_returns_error_when_no_source_image(self, service, base_scene):
        """edit_scene_image returns error when neither source_media_id nor scene image exists."""
        base_scene["vertical_image_media_id"] = None
        project = {"user_paygate_tier": "PAYGATE_TIER_ONE"}

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=project)

            result = await service.edit_scene_image(base_scene, "VERTICAL", source_media_id=None)

        assert "error" in result
        assert "No source image" in result["error"]


# ---------------------------------------------------------------------------
# Test: generate_reference_image
# ---------------------------------------------------------------------------

class TestGenerateReferenceImage:
    @pytest.fixture
    def char_no_media(self):
        return {
            "id": CHAR_ID,
            "name": "Hero",
            "entity_type": "character",
            "description": "Brave warrior",
            "image_prompt": "Full body warrior portrait",
            "reference_image_url": None,
            "media_id": None,
        }

    @pytest.fixture
    def char_has_url_no_media(self):
        """Character already has reference_image_url but no media_id — fast path."""
        return {
            "id": CHAR_ID,
            "name": "Hero",
            "entity_type": "character",
            "description": "Brave warrior",
            "image_prompt": "Full body warrior portrait",
            "reference_image_url": f"https://lh3.googleusercontent.com/image/{SAMPLE_UUID}?sqp=params",
            "media_id": None,
        }

    @pytest.mark.asyncio
    async def test_normal_path_generates_and_uploads(self, service, char_no_media, mock_client):
        """Normal path: calls generate_images, extracts URL, uploads to get media_id."""
        project = {"user_paygate_tier": "PAYGATE_TIER_TWO"}

        with patch("agent.sdk.services.operations.crud") as mock_crud, \
             patch("agent.sdk.services.operations._upload_character_image",
                   new_callable=AsyncMock) as mock_upload:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.update_character = AsyncMock()
            mock_upload.return_value = SAMPLE_UUID_2

            result = await service.generate_reference_image(char_no_media, PROJECT_ID)

        mock_client.generate_images.assert_called_once()
        call_kwargs = mock_client.generate_images.call_args.kwargs
        assert call_kwargs["aspect_ratio"] == "IMAGE_ASPECT_RATIO_PORTRAIT"
        assert call_kwargs["prompt"] == char_no_media["image_prompt"]

    @pytest.mark.asyncio
    async def test_fast_path_upload_only_when_url_exists(self, service, char_has_url_no_media, mock_client):
        """Fast path: skips generate_images when URL exists but media_id is missing."""
        with patch("agent.sdk.services.operations.crud") as mock_crud, \
             patch("agent.sdk.services.operations._upload_character_image",
                   new_callable=AsyncMock) as mock_upload:
            mock_crud.update_character = AsyncMock()
            mock_upload.return_value = SAMPLE_UUID_2

            result = await service.generate_reference_image(char_has_url_no_media, PROJECT_ID)

        # generate_images must NOT be called on fast path
        mock_client.generate_images.assert_not_called()
        mock_crud.update_character.assert_called_once_with(CHAR_ID, media_id=SAMPLE_UUID_2)
        assert "data" in result

    @pytest.mark.asyncio
    async def test_fast_path_falls_back_to_uuid_from_url(self, service, char_has_url_no_media):
        """Fast path: when upload fails, extracts UUID directly from the image URL."""
        with patch("agent.sdk.services.operations.crud") as mock_crud, \
             patch("agent.sdk.services.operations._upload_character_image",
                   new_callable=AsyncMock) as mock_upload:
            mock_crud.update_character = AsyncMock()
            mock_upload.return_value = None  # upload fails

            result = await service.generate_reference_image(char_has_url_no_media, PROJECT_ID)

        # Should extract UUID from URL: SAMPLE_UUID is embedded in the URL
        mock_crud.update_character.assert_called_once_with(CHAR_ID, media_id=SAMPLE_UUID)
        assert "data" in result


# ---------------------------------------------------------------------------
# Test: Queue wrappers
# ---------------------------------------------------------------------------

class TestQueueWrappers:
    @pytest.mark.asyncio
    async def test_queue_scene_image_creates_generate_image_request(self, service):
        """queue_scene_image creates a GENERATE_IMAGE request in the DB and returns its id."""
        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.create_request = AsyncMock(return_value={"id": "req-001"})

            req_id = await service.queue_scene_image(SCENE_ID, PROJECT_ID, VIDEO_ID, "VERTICAL")

        assert req_id == "req-001"
        mock_crud.create_request.assert_called_once_with(
            req_type="GENERATE_IMAGE", orientation="VERTICAL",
            scene_id=SCENE_ID, project_id=PROJECT_ID, video_id=VIDEO_ID,
        )

    @pytest.mark.asyncio
    async def test_queue_scene_video_creates_generate_video_request(self, service):
        """queue_scene_video creates a GENERATE_VIDEO request in the DB and returns its id."""
        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.create_request = AsyncMock(return_value={"id": "req-002"})

            req_id = await service.queue_scene_video(SCENE_ID, PROJECT_ID, VIDEO_ID, "VERTICAL")

        assert req_id == "req-002"
        mock_crud.create_request.assert_called_once_with(
            req_type="GENERATE_VIDEO", orientation="VERTICAL",
            scene_id=SCENE_ID, project_id=PROJECT_ID, video_id=VIDEO_ID,
        )

    @pytest.mark.asyncio
    async def test_queue_upscale_video_creates_upscale_video_request(self, service):
        """queue_upscale_video creates an UPSCALE_VIDEO request in the DB and returns its id."""
        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.create_request = AsyncMock(return_value={"id": "req-003"})

            req_id = await service.queue_upscale_video(SCENE_ID, PROJECT_ID, VIDEO_ID, "VERTICAL")

        assert req_id == "req-003"
        mock_crud.create_request.assert_called_once_with(
            req_type="UPSCALE_VIDEO", orientation="VERTICAL",
            scene_id=SCENE_ID, project_id=PROJECT_ID, video_id=VIDEO_ID,
        )

    @pytest.mark.asyncio
    async def test_generate_character_image_delegates_to_queue_reference_image(self, service):
        """generate_character_image alias delegates to queue_reference_image (GENERATE_CHARACTER_IMAGE)."""
        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.create_request = AsyncMock(return_value={"id": "req-004"})

            req_id = await service.generate_character_image(CHAR_ID, PROJECT_ID)

        assert req_id == "req-004"
        mock_crud.create_request.assert_called_once_with(
            req_type="GENERATE_CHARACTER_IMAGE",
            character_id=CHAR_ID, project_id=PROJECT_ID,
        )


# ---------------------------------------------------------------------------
# Test: Singleton init/get
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_operations_raises_before_init(self):
        """get_operations raises RuntimeError when called before init_operations."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_operations()

    def test_init_operations_returns_instance(self, mock_client, mock_repo):
        """init_operations creates and returns an OperationService instance."""
        instance = init_operations(mock_client, mock_repo)
        assert isinstance(instance, OperationService)

    def test_get_operations_returns_initialized_instance(self, mock_client, mock_repo):
        """get_operations returns the same instance created by init_operations."""
        instance = init_operations(mock_client, mock_repo)
        retrieved = get_operations()
        assert retrieved is instance


class TestPollOperations:
    @pytest.mark.asyncio
    async def test_poll_operations_surfaces_error_details(self):
        client = AsyncMock()
        client.check_video_status = AsyncMock(return_value={
            "data": {
                "operations": [
                    {
                        "status": "MEDIA_GENERATION_STATUS_FAILED",
                        "operation": {
                            "name": "op-123",
                            "error": {
                                "message": "Flow blocked request",
                                "details": [{"reason": "PUBLIC_ERROR_UNSAFE_GENERATION"}],
                            },
                        },
                    }
                ]
            }
        })

        with patch("agent.sdk.services.operations.VIDEO_POLL_INTERVAL", 0):
            result = await ops_module._poll_operations(client, [{"operation": {"name": "op-123"}}], timeout=1)

        assert result["error"] == "Flow blocked request [PUBLIC_ERROR_UNSAFE_GENERATION]"

    @pytest.mark.asyncio
    async def test_poll_operations_falls_back_to_operation_name_when_error_missing(self):
        client = AsyncMock()
        client.check_video_status = AsyncMock(return_value={
            "data": {
                "operations": [
                    {
                        "status": "MEDIA_GENERATION_STATUS_FAILED",
                        "operation": {"name": "op-456"},
                    }
                ]
            }
        })

        with patch("agent.sdk.services.operations.VIDEO_POLL_INTERVAL", 0):
            result = await ops_module._poll_operations(client, [{"operation": {"name": "op-456"}}], timeout=1)

        assert result["error"] == "Operation failed: op-456"
