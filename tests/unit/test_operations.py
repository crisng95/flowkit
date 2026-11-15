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

    @pytest.mark.asyncio
    async def test_continuation_scene_enriches_prompt_without_crashing(
            self, service, base_scene, mock_client):
        """A CONTINUATION scene (has parent_scene_id, no image_prompt) must route
        through _build_continuation_prompt without raising NameError, and the
        enriched prompt must reach the provider call.

        Regression test: a prior refactor (provider-neutral platform, 76c4d3f)
        dropped the _build_continuation_prompt definition but left both call
        sites in place. No existing fixture set parent_scene_id, so the dead
        code path went untested and the NameError only surfaced at runtime
        against a live Flow project.
        """
        base_scene["parent_scene_id"] = "parent-scene-001"
        base_scene["image_prompt"] = None
        base_scene["character_names"] = None

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value={"user_paygate_tier": "PAYGATE_TIER_ONE"})
            mock_crud.get_project_characters = AsyncMock(return_value=[])

            result = await service.generate_scene_image(base_scene, "VERTICAL")

        assert "error" not in result
        call_kwargs = mock_client.generate_images.call_args.kwargs
        assert "Transform this image into a completely different moment" in call_kwargs["prompt"]
        assert base_scene["prompt"] in call_kwargs["prompt"]


# ---------------------------------------------------------------------------
# Test: generate_scene_video — the retry branch
# ---------------------------------------------------------------------------

class TestGenerateSceneVideoRetry:
    """A retry must re-poll a submitted render, never resubmit it.

    This is the one branch where a wrong answer costs money: resubmitting
    abandons a render Flow is already paying for and starts a second one. It
    was previously gated on the transport (`bare_uuid and not USE_BATCH_RPC`),
    which made it dead on the only transport that exists, so it went untested.
    """

    @pytest.mark.asyncio
    async def test_a_submitted_operation_is_repolled_not_resubmitted(
            self, service, base_scene, mock_client):
        mock_client.generate_video = AsyncMock()
        polled = {"data": {"operations": [{"status": "MEDIA_GENERATION_STATUS_SUCCESSFUL"}]}}

        # Retry logic now lives in FlowProvider — patch its crud/_poll_operations.
        # generate_scene_video itself still reads the project tier via operations.crud.
        with patch("agent.sdk.services.operations.crud") as ops_crud, \
             patch("agent.sdk.services.flow_provider.crud") as flow_crud, \
             patch("agent.sdk.services.operations._build_video_prompt",
                   new=AsyncMock(return_value="p")), \
             patch("agent.sdk.services.flow_provider._poll_operations",
                   new=AsyncMock(return_value=polled)) as mock_poll:
            ops_crud.get_project = AsyncMock(return_value={"user_paygate_tier": "PAYGATE_TIER_ONE"})
            flow_crud.get_request = AsyncMock(return_value={"request_id": SAMPLE_UUID_2})

            result = await service.generate_scene_video(
                base_scene, "VERTICAL", request_id="req-1")

        mock_client.generate_video.assert_not_called()
        assert mock_poll.await_args.args[1][0]["operation"]["name"] == SAMPLE_UUID_2
        assert result is polled

    @pytest.mark.asyncio
    async def test_no_prior_operation_still_submits(self, service, base_scene, mock_client):
        """The complement — the guard must not swallow a first attempt."""
        mock_client.generate_video = AsyncMock(
            return_value={"data": {"operations": [{"operation": {"name": "op-new"}}]}})

        with patch("agent.sdk.services.operations.crud") as ops_crud, \
             patch("agent.sdk.services.flow_provider.crud") as flow_crud, \
             patch("agent.sdk.services.operations._build_video_prompt",
                   new=AsyncMock(return_value="p")), \
             patch("agent.sdk.services.flow_provider._poll_operations",
                   new=AsyncMock(return_value={"data": {}})):
            ops_crud.get_project = AsyncMock(return_value={"user_paygate_tier": "PAYGATE_TIER_ONE"})
            flow_crud.get_request = AsyncMock(return_value=None)
            flow_crud.update_request = AsyncMock()

            await service.generate_scene_video(base_scene, "VERTICAL", request_id="req-1")

        mock_client.generate_video.assert_called_once()


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
            mock_crud.get_project_characters = AsyncMock(return_value=[])

            result = await service.edit_scene_image(base_scene, "VERTICAL", source_media_id=None)

        assert "error" in result
        assert "No source image" in result["error"]

    @pytest.mark.asyncio
    async def test_continuation_scene_enriches_prompt_without_crashing(
            self, service, base_scene, mock_client):
        """A CONTINUATION scene (has parent_scene_id, no image_prompt) must route
        through _build_continuation_prompt without raising NameError.

        Regression test for the same dropped-function bug as
        TestGenerateSceneImage.test_continuation_scene_enriches_prompt_without_crashing,
        on the edit_scene_image call site (used for actual CONTINUATION scenes
        in the real pipeline — generate_scene_image's call site is only hit on
        a direct regenerate-with-parent edge case).
        """
        base_scene["parent_scene_id"] = "parent-scene-001"
        base_scene["image_prompt"] = None
        base_scene["character_names"] = None
        parent_scene = {
            "vertical_image_media_id": SAMPLE_UUID_2,
            "vertical_image_url": "https://lh3.googleusercontent.com/image/parent?sqp=params",
        }

        with patch("agent.sdk.services.operations.crud") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value={"user_paygate_tier": "PAYGATE_TIER_ONE"})
            mock_crud.get_project_characters = AsyncMock(return_value=[])
            mock_crud.get_scene = AsyncMock(return_value=parent_scene)

            result = await service.edit_scene_image(base_scene, "VERTICAL", source_media_id=None)

        assert "error" not in result
        mock_client.edit_image.assert_called_once()
        call_kwargs = mock_client.edit_image.call_args.kwargs
        assert "Transform this image into a completely different moment" in call_kwargs["prompt"]
        assert call_kwargs["source_media_id"] == SAMPLE_UUID_2  # resolved from parent


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
        """Normal path: calls generate_images; non-UUID media id triggers upload to get one."""
        project = {"user_paygate_tier": "PAYGATE_TIER_TWO"}
        # No UUID anywhere (media name is CAMS-format, URL has no UUID) →
        # must upload to obtain a UUID media id.
        fife_url = "https://lh3.googleusercontent.com/image/CAMS_non_uuid_media?sqp=params"
        mock_client.generate_images = AsyncMock(return_value={
            "data": {"media": [{
                "name": "CAMS_non_uuid_media",
                "image": {"generatedImage": {"mediaId": "CAMS_non_uuid_media", "fifeUrl": fife_url}},
            }]}
        })

        with patch("agent.sdk.services.operations.crud") as mock_crud, \
             patch("agent.sdk.services.flow_provider._upload_character_image",
                   new_callable=AsyncMock) as mock_upload:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.update_character = AsyncMock()
            mock_upload.return_value = SAMPLE_UUID_2

            result = await service.generate_reference_image(char_no_media, PROJECT_ID)

        mock_client.generate_images.assert_called_once()
        call_kwargs = mock_client.generate_images.call_args.kwargs
        assert call_kwargs["aspect_ratio"] == "IMAGE_ASPECT_RATIO_PORTRAIT"
        assert call_kwargs["prompt"] == char_no_media["image_prompt"]
        mock_upload.assert_awaited_once()
        mock_crud.update_character.assert_called_once_with(
            CHAR_ID, media_id=SAMPLE_UUID_2, reference_image_url=fife_url)
        assert "data" in result

    @pytest.mark.asyncio
    async def test_normal_path_skips_upload_when_uuid_returned(self, service, char_no_media, mock_client):
        """Normal path: Flow returns a UUID media id directly → no upload needed."""
        project = {"user_paygate_tier": "PAYGATE_TIER_TWO"}

        with patch("agent.sdk.services.operations.crud") as mock_crud, \
             patch("agent.sdk.services.flow_provider._upload_character_image",
                   new_callable=AsyncMock) as mock_upload:
            mock_crud.get_project = AsyncMock(return_value=project)
            mock_crud.update_character = AsyncMock()

            result = await service.generate_reference_image(char_no_media, PROJECT_ID)

        # mock_client.generate_images returns media name=SAMPLE_UUID (a UUID)
        mock_client.generate_images.assert_called_once()
        mock_upload.assert_not_awaited()
        assert "data" in result

    @pytest.mark.asyncio
    async def test_fast_path_upload_only_when_url_exists(self, service, char_has_url_no_media, mock_client):
        """Fast path: skips generate_images when URL exists but media_id is missing."""
        url = char_has_url_no_media["reference_image_url"]
        with patch("agent.sdk.services.operations.crud") as mock_crud, \
             patch("agent.sdk.services.flow_provider._upload_character_image",
                   new_callable=AsyncMock) as mock_upload:
            mock_crud.update_character = AsyncMock()
            mock_upload.return_value = SAMPLE_UUID_2

            result = await service.generate_reference_image(char_has_url_no_media, PROJECT_ID)

        # generate_images must NOT be called on fast path
        mock_client.generate_images.assert_not_called()
        mock_crud.update_character.assert_called_once_with(
            CHAR_ID, media_id=SAMPLE_UUID_2, reference_image_url=url)
        assert "data" in result

    @pytest.mark.asyncio
    async def test_fast_path_falls_back_to_uuid_from_url(self, service, char_has_url_no_media):
        """Fast path: when upload fails, extracts UUID directly from the image URL."""
        url = char_has_url_no_media["reference_image_url"]
        with patch("agent.sdk.services.operations.crud") as mock_crud, \
             patch("agent.sdk.services.flow_provider._upload_character_image",
                   new_callable=AsyncMock) as mock_upload:
            mock_crud.update_character = AsyncMock()
            mock_upload.return_value = None  # upload fails

            result = await service.generate_reference_image(char_has_url_no_media, PROJECT_ID)

        # Should extract UUID from URL: SAMPLE_UUID is embedded in the URL
        mock_crud.update_character.assert_called_once_with(
            CHAR_ID, media_id=SAMPLE_UUID, reference_image_url=url)
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
            provider=None,
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
            provider=None,
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
            provider=None,
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
            provider=None,
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
