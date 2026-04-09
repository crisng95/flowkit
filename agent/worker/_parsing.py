"""Response parsing utilities for the worker layer.

Shared by processor.py and sdk/services/operations.py.
"""

import logging
import re

logger = logging.getLogger(__name__)


def _is_error(result: dict) -> bool:
    if result.get("error"):
        return True
    status = result.get("status")
    if isinstance(status, int) and status >= 400:
        return True
    data = result.get("data", {})
    if isinstance(data, dict) and data.get("error"):
        return True
    return False


def _is_uuid(value: str) -> bool:
    """Check if a string looks like a UUID (8-4-4-4-12 hex format)."""
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value, re.I))


def _extract_uuid_from_url(url: str) -> str:
    """Extract UUID from fifeUrl like https://storage.googleapis.com/.../image/{UUID}?..."""
    match = re.search(r'/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', url, re.I)
    return match.group(1) if match else ""


def _extract_media_id(result: dict, req_type: str) -> str:
    """Extract the UUID-format mediaId from API response.

    IMPORTANT: mediaId is a UUID. mediaGenerationId is a base64 protobuf
    string (CAMS...) — do NOT use this.
    """
    data = result.get("data", result)

    if req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE", "GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"):
        media = data.get("media", [])
        if media:
            item = media[0]
            name = item.get("name", "")
            if name and _is_uuid(name):
                return name
            gen = item.get("image", {}).get("generatedImage", {})
            val = gen.get("mediaId", "")
            if val and _is_uuid(val):
                return val
            for url_field in ("fifeUrl", "imageUri"):
                url = gen.get(url_field, "")
                if url:
                    uuid_val = _extract_uuid_from_url(url)
                    if uuid_val:
                        logger.info("Extracted mediaId from %s: %s", url_field, uuid_val)
                        return uuid_val
            if name:
                logger.warning("media[0].name is not UUID format: %s", name[:30])
            return None

    if req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO"):
        ops = data.get("operations", [])
        if ops:
            video_meta = ops[0].get("operation", {}).get("metadata", {}).get("video", {})
            for field in ("mediaId",):
                val = video_meta.get(field, "")
                if val and _is_uuid(val):
                    return val
            fife = video_meta.get("fifeUrl", "")
            if fife:
                uuid_val = _extract_uuid_from_url(fife)
                if uuid_val:
                    return uuid_val
            val = video_meta.get("mediaId", "")
            if val and _is_uuid(val):
                return val
            # Inline rawBytes format (upscale returns video data directly)
            # Do NOT return mediaGenerationId — it's CAMS format, not UUID (Rule #1)
            if ops[0].get("rawBytes"):
                logger.info("Inline rawBytes response, no UUID media_id available")
                return None
            return None

    return None


def _extract_output_url(result: dict, req_type: str) -> str:
    data = result.get("data", result)

    if req_type in ("GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE", "GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"):
        media = data.get("media", [])
        if media:
            gen = media[0].get("image", {}).get("generatedImage", {})
            return gen.get("fifeUrl", gen.get("imageUri", gen.get("encodedImage", "")))

    if req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO"):
        ops = data.get("operations", [])
        if ops:
            video_meta = ops[0].get("operation", {}).get("metadata", {}).get("video", {})
            url = video_meta.get("fifeUrl", "")
            if url:
                return url
            # Inline rawBytes — no URL, check if saved locally
            if ops[0].get("rawBytes") or ops[0].get("mediaGenerationId"):
                return ""  # URL will be set by _save_raw_bytes in operations.py

    return data.get("videoUri", data.get("imageUri", ""))
