"""Shared pytest fixtures for Flow Kit tests."""

import pytest


@pytest.fixture
def sample_uuid():
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def sample_cams_id():
    """A CAMS... base64 mediaGenerationId — NOT a valid UUID."""
    return "CAMSJDkxMTYwNzM4LTRlMjYtNDVkZi05OTMz"


@pytest.fixture
def sample_image_success(sample_uuid):
    """Successful image generation response from Google Flow API."""
    return {
        "data": {
            "media": [{
                "name": sample_uuid,
                "image": {
                    "generatedImage": {
                        "mediaId": sample_uuid,
                        "fifeUrl": f"https://lh3.googleusercontent.com/image/{sample_uuid}?sqp=params",
                    }
                }
            }]
        }
    }


@pytest.fixture
def sample_image_success_no_uuid():
    """Image response where media[0].name is NOT a UUID (CAMS format)."""
    return {
        "data": {
            "media": [{
                "name": "CAMSJDkxMTYwNzM4LTRlMjYtNDVkZi05OTMz",
                "image": {
                    "generatedImage": {
                        "mediaId": "CAMSJDkxMTYwNzM4",
                        "fifeUrl": "https://lh3.googleusercontent.com/image/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee?sqp=params",
                    }
                }
            }]
        }
    }


@pytest.fixture
def sample_video_success(sample_uuid):
    """Successful video generation response."""
    return {
        "data": {
            "operations": [{
                "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                "operation": {
                    "name": "operations/video-123",
                    "metadata": {
                        "video": {
                            "mediaId": sample_uuid,
                            "fifeUrl": f"https://storage.googleapis.com/video/{sample_uuid}",
                        }
                    }
                }
            }]
        }
    }


@pytest.fixture
def sample_error_response():
    """Error response from Google Flow API."""
    return {"error": "Internal error encountered"}


@pytest.fixture
def sample_nested_error():
    """Error nested inside data.error."""
    return {
        "data": {
            "error": {
                "code": 403,
                "message": "caller does not have permission",
            }
        }
    }


@pytest.fixture
def sample_scene_row(sample_uuid):
    """A flat DB row for a scene with completed vertical image."""
    return {
        "id": "scene-001",
        "video_id": "video-001",
        "display_order": 0,
        "prompt": "Hero walks into the castle courtyard at dawn",
        "image_prompt": None,
        "video_prompt": "0-3s: Hero pushes open gate. 3-6s: Looks up. 6-8s: Zoom on sword.",
        "character_names": '["Hero", "Castle"]',
        "parent_scene_id": None,
        "chain_type": "ROOT",
        "vertical_image_media_id": sample_uuid,
        "vertical_image_url": f"https://example.com/image/{sample_uuid}",
        "vertical_image_status": "COMPLETED",
        "vertical_video_media_id": None,
        "vertical_video_url": None,
        "vertical_video_status": "PENDING",
        "vertical_upscale_media_id": None,
        "vertical_upscale_url": None,
        "vertical_upscale_status": "PENDING",
        "vertical_end_scene_media_id": None,
        "horizontal_image_media_id": None,
        "horizontal_image_url": None,
        "horizontal_image_status": "PENDING",
        "horizontal_video_media_id": None,
        "horizontal_video_url": None,
        "horizontal_video_status": "PENDING",
        "horizontal_upscale_media_id": None,
        "horizontal_upscale_url": None,
        "horizontal_upscale_status": "PENDING",
        "horizontal_end_scene_media_id": None,
        "trim_start": None,
        "trim_end": None,
        "duration": None,
        "created_at": "2026-04-01T00:00:00",
        "updated_at": "2026-04-01T00:00:00",
    }


@pytest.fixture
def sample_character_row(sample_uuid):
    """A flat DB row for a character entity."""
    return {
        "id": "char-001",
        "name": "Hero",
        "entity_type": "character",
        "description": "A brave warrior with golden armor",
        "image_prompt": "Full body portrait of a warrior in golden armor, front-facing, neutral background",
        "voice_description": "Deep calm heroic voice",
        "reference_image_url": f"https://example.com/ref/{sample_uuid}",
        "media_id": sample_uuid,
        "created_at": "2026-04-01T00:00:00",
        "updated_at": "2026-04-01T00:00:00",
    }
