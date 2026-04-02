"""Background worker — processes pending requests via Chrome extension.

Workflow audit:
- W5 (image gen): sync — API returns result immediately → extract mediaGenId + imageUri
- W6 (video gen): async — API returns operations[] → must poll check_video_status until done
- W7 (video chain): same as W6 but with endImage in payload
- W8 (upscale): async — same as video, returns operations[] → poll
- W9 (status poll): poll_operation() handles this for W6/W7/W8
- W11 (retry): on error, increment retry_count, re-queue as PENDING
"""
import asyncio
import json
import logging
from agent.db import crud
from agent.services.flow_client import get_flow_client
from agent.config import POLL_INTERVAL, MAX_RETRIES, VIDEO_POLL_TIMEOUT, API_COOLDOWN

logger = logging.getLogger(__name__)


async def process_pending_requests():
    """Main worker loop — dispatches pending requests concurrently.

    Each request is processed in its own asyncio task so video gen polling
    (which can take 5-10 minutes) doesn't block other requests.

    The _active_requests set prevents the same request from being picked up
    again on the next loop iteration while it's still processing.
    """
    client = get_flow_client()
    _active_requests: set[str] = set()

    while True:
        try:
            if not client.connected:
                await asyncio.sleep(POLL_INTERVAL)
                continue

            pending = await crud.list_pending_requests()
            for req in pending:
                rid = req["id"]
                if rid in _active_requests:
                    continue  # Already processing in a concurrent task
                _active_requests.add(rid)
                asyncio.create_task(_process_one_tracked(client, req, _active_requests))
        except Exception as e:
            logger.exception("Worker loop error: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


async def _process_one_tracked(client, req: dict, active: set):
    """Wrapper that removes request from active set when done."""
    try:
        await _process_one(client, req)
    finally:
        active.discard(req["id"])


async def _process_one(client, req: dict):
    """Process a single request."""
    rid = req["id"]
    req_type = req["type"]
    orientation = req.get("orientation", "VERTICAL")

    # Skip if scene asset is already COMPLETED (prevents wasting captcha-requiring API calls)
    if await _is_already_completed(req, orientation):
        logger.info("Request %s skipped — scene asset already COMPLETED", rid[:8])
        await crud.update_request(rid, status="COMPLETED", error_message="skipped: already completed")
        return

    logger.info("Processing request %s type=%s", rid[:8], req_type)
    await crud.update_request(rid, status="PROCESSING")

    # Anti-spam: cooldown before API calls (gen image, video, upscale)
    api_call_types = {"GENERATE_IMAGES", "GENERATE_VIDEO", "GENERATE_VIDEO_REFS",
                      "UPSCALE_VIDEO", "GENERATE_CHARACTER_IMAGE"}
    if req_type in api_call_types and API_COOLDOWN > 0:
        logger.debug("Cooldown %ds before %s", API_COOLDOWN, req_type)
        await asyncio.sleep(API_COOLDOWN)

    try:
        if req_type == "GENERATE_IMAGES":
            result = await _handle_generate_image(client, req, orientation)
        elif req_type == "GENERATE_VIDEO":
            result = await _handle_generate_video(client, req, orientation)
        elif req_type == "GENERATE_VIDEO_REFS":
            result = await _handle_generate_video_refs(client, req, orientation)
        elif req_type == "UPSCALE_VIDEO":
            result = await _handle_upscale_video(client, req, orientation)
        elif req_type == "GENERATE_CHARACTER_IMAGE":
            result = await _handle_generate_character_image(client, req)
        else:
            result = {"error": f"Unknown request type: {req_type}"}

        if _is_error(result):
            await _handle_failure(rid, req, result)
        else:
            media_id = _extract_media_id(result, req_type)
            output_url = _extract_output_url(result, req_type)
            await crud.update_request(rid, status="COMPLETED", media_id=media_id, output_url=output_url)
            await _update_scene_from_result(req, orientation, media_id, output_url)
            logger.info("Request %s COMPLETED: media=%s", rid[:8], media_id[:20] if media_id else "?")

    except Exception as e:
        logger.exception("Request %s exception: %s", rid[:8], e)
        await _handle_failure(rid, req, {"error": str(e)})


async def _handle_failure(rid: str, req: dict, result: dict):
    """Handle request failure with retry logic."""
    error_msg = result.get("error")
    if not error_msg:
        error_data = result.get("data", {})
        if isinstance(error_data, dict):
            error_field = error_data.get("error", "Unknown error")
            if isinstance(error_field, dict):
                error_msg = error_field.get("message", json.dumps(error_field)[:200])
            else:
                error_msg = str(error_field)
        else:
            error_msg = "Unknown error"
    if isinstance(error_msg, dict):
        error_msg = json.dumps(error_msg)[:200]

    retry = req.get("retry_count", 0) + 1
    if retry < MAX_RETRIES:
        # Back to PENDING for retry
        await crud.update_request(rid, status="PENDING", retry_count=retry, error_message=str(error_msg))
        logger.warning("Request %s failed (retry %d/%d): %s", rid[:8], retry, MAX_RETRIES, error_msg)
    else:
        await crud.update_request(rid, status="FAILED", error_message=str(error_msg))
        # Also mark scene status as FAILED
        await _mark_scene_failed(req)
        logger.error("Request %s FAILED permanently: %s", rid[:8], error_msg)


async def _mark_scene_failed(req: dict):
    """Mark the relevant scene field as FAILED."""
    scene_id = req.get("scene_id")
    if not scene_id:
        return
    orientation = req.get("orientation", "VERTICAL")
    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    req_type = req["type"]
    updates = {}
    if req_type == "GENERATE_IMAGES":
        updates[f"{prefix}_image_status"] = "FAILED"
    elif req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
        updates[f"{prefix}_video_status"] = "FAILED"
    elif req_type == "UPSCALE_VIDEO":
        updates[f"{prefix}_upscale_status"] = "FAILED"
    if updates:
        await crud.update_scene(scene_id, **updates)


async def _is_already_completed(req: dict, orientation: str) -> bool:
    """Check if the scene asset this request targets is already COMPLETED.

    Prevents wasting captcha-requiring API calls (generate image/video/upscale)
    on assets that were already successfully generated.
    """
    scene_id = req.get("scene_id")
    req_type = req.get("type", "")
    if not scene_id or req_type == "GENERATE_CHARACTER_IMAGE":
        return False

    scene = await crud.get_scene(scene_id)
    if not scene:
        return False

    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"

    if req_type == "GENERATE_IMAGES":
        return scene.get(f"{prefix}_image_status") == "COMPLETED"
    elif req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
        return scene.get(f"{prefix}_video_status") == "COMPLETED"
    elif req_type == "UPSCALE_VIDEO":
        return scene.get(f"{prefix}_upscale_status") == "COMPLETED"

    return False


# ─── Error Detection ────────────────────────────────────────

def _is_error(result: dict) -> bool:
    if result.get("error"):
        return True
    status = result.get("status")
    if isinstance(status, int) and status >= 400:
        return True
    # Check nested error in data
    data = result.get("data", {})
    if isinstance(data, dict) and data.get("error"):
        return True
    return False


# ─── Response Parsing ────────────────────────────────────────

def _is_uuid(value: str) -> bool:
    """Check if a string looks like a UUID (8-4-4-4-12 hex format)."""
    import re
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value, re.I))


def _extract_uuid_from_url(url: str) -> str:
    """Extract UUID from fifeUrl like https://storage.googleapis.com/.../image/{UUID}?..."""
    import re
    match = re.search(r'/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', url, re.I)
    return match.group(1) if match else ""


def _extract_media_id(result: dict, req_type: str) -> str:
    """Extract the UUID-format mediaId from API response.

    IMPORTANT: mediaId is a UUID (e.g. "caad9e1b-a1c9-4aab-a2ee-66ca34f689be").
    mediaGenerationId is a base64 protobuf string (e.g. "CAMS...") — do NOT use this.
    Both startImage.mediaId and imageInputs[].name need the UUID format.
    """
    data = result.get("data", result)

    if req_type == "GENERATE_IMAGES":
        # batchGenerateImages → media[].name should be UUID
        media = data.get("media", [])
        if media:
            item = media[0]
            # Try media[].name — should be UUID
            name = item.get("name", "")
            if name and _is_uuid(name):
                return name
            # Try generatedImage fields
            gen = item.get("image", {}).get("generatedImage", {})
            for field in ("mediaId", "mediaGenerationId"):
                val = gen.get(field, "")
                if val and _is_uuid(val):
                    return val
            # Fallback: extract UUID from fifeUrl/imageUri
            for url_field in ("fifeUrl", "imageUri"):
                url = gen.get(url_field, "")
                if url:
                    uuid_val = _extract_uuid_from_url(url)
                    if uuid_val:
                        logger.info("Extracted mediaId from %s: %s", url_field, uuid_val)
                        return uuid_val
            # Last resort: return name even if not UUID (for logging)
            if name:
                logger.warning("media[0].name is not UUID format: %s", name[:30])
                return name

    if req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO"):
        ops = data.get("operations", [])
        if ops:
            video_meta = ops[0].get("operation", {}).get("metadata", {}).get("video", {})
            # Try mediaId first, then extract from fifeUrl
            for field in ("mediaId",):
                val = video_meta.get(field, "")
                if val and _is_uuid(val):
                    return val
            fife = video_meta.get("fifeUrl", "")
            if fife:
                uuid_val = _extract_uuid_from_url(fife)
                if uuid_val:
                    return uuid_val
            # Fallback
            for field in ("mediaId", "mediaGenerationId"):
                val = video_meta.get(field, "")
                if val:
                    return val

    return ""


def _extract_output_url(result: dict, req_type: str) -> str:
    data = result.get("data", result)

    if req_type == "GENERATE_IMAGES":
        media = data.get("media", [])
        if media:
            gen = media[0].get("image", {}).get("generatedImage", {})
            return gen.get("fifeUrl", gen.get("imageUri", gen.get("encodedImage", "")))

    if req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO"):
        # batchCheckAsyncVideoGenerationStatus response:
        # operations[].operation.metadata.video.fifeUrl
        ops = data.get("operations", [])
        if ops:
            video_meta = ops[0].get("operation", {}).get("metadata", {}).get("video", {})
            return video_meta.get("fifeUrl", "")

    return data.get("videoUri", data.get("imageUri", ""))


def _extract_operations(result: dict) -> list[dict]:
    """Extract operations from video gen / upscale submit response.

    Submit response format:
    {
      "operations": [
        {
          "operation": {"name": "operations/xxx"},
          "status": "MEDIA_GENERATION_STATUS_PROCESSING"
        }
      ]
    }

    For poll input to check_video_status, we pass these as-is.
    """
    data = result.get("data", result)
    ops = data.get("operations", [])
    # Validate structure
    for op in ops:
        op_name = op.get("operation", {}).get("name")
        if not op_name:
            logger.warning("Operation missing name: %s", op)
    return ops


# ─── W9: Video/Upscale Status Polling ────────────────────────

async def _poll_operations(client, operations: list[dict], timeout: int = VIDEO_POLL_TIMEOUT) -> dict:
    """
    Poll check_video_status until all operations complete or timeout.

    Production response format from batchCheckAsyncVideoGenerationStatus:
    {
      "operations": [
        {
          "operation": {
            "name": "operations/xxx",
            "metadata": {
              "video": {
                "mediaId": "...",
                "fifeUrl": "https://..."
              }
            }
          },
          "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL"  // or _FAILED, _PROCESSING
        }
      ]
    }

    Status values:
    - MEDIA_GENERATION_STATUS_PROCESSING / PENDING → keep polling
    - MEDIA_GENERATION_STATUS_SUCCESSFUL → done
    - MEDIA_GENERATION_STATUS_FAILED → error
    """
    if not operations:
        return {"error": "No operations to poll"}

    poll_interval = POLL_INTERVAL
    elapsed = 0
    # Use latest operations for each poll — API returns updated status/metadata
    current_ops = operations

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        status_result = await client.check_video_status(current_ops)
        if _is_error(status_result):
            logger.warning("Status poll error: %s", status_result.get("error"))
            continue

        data = status_result.get("data", status_result)
        ops = data.get("operations", [])

        if not ops:
            continue

        # Update current_ops with latest response for next poll iteration
        current_ops = ops

        all_done = True
        has_error = False

        for op in ops:
            status = op.get("status", "")
            if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                continue  # done
            elif status == "MEDIA_GENERATION_STATUS_FAILED":
                error_msg = f"Operation failed: {op.get('operation', {}).get('name', '?')}"
                logger.error(error_msg)
                has_error = True
                break
            else:
                # Still processing
                all_done = False

        if has_error:
            return {"error": error_msg}

        if all_done:
            logger.info("All %d operations completed after %ds", len(ops), elapsed)
            return {"data": data}

        done_count = sum(1 for o in ops if o.get("status") == "MEDIA_GENERATION_STATUS_SUCCESSFUL")
        logger.debug("Poll %ds/%ds: %d/%d done", elapsed, timeout, done_count, len(ops))

    return {"error": f"Polling timeout after {timeout}s"}


# ─── W5: Image Generation (sync) ────────────────────────────

async def _handle_generate_image(client, req: dict, orientation: str) -> dict:
    """W5: Image generation — synchronous, returns result immediately.

    Response path: data.media[].name = mediaId

    If scene has character_names, looks up their media_ids from project
    and passes them as imageInputs (edit_image flow).
    """
    scene = await crud.get_scene(req["scene_id"]) if req.get("scene_id") else None
    if not scene:
        return {"error": "Scene not found"}

    project = await crud.get_project(req["project_id"]) if req.get("project_id") else None
    aspect = "IMAGE_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "IMAGE_ASPECT_RATIO_LANDSCAPE"
    prompt = scene.get("image_prompt") or scene.get("prompt", "")
    tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"
    pid = req.get("project_id", "0")

    # Reference image flow:
    #   1. Each entity (character/location/asset) has media_id from GENERATE_CHARACTER_IMAGE
    #   2. Trust media_id if present — skip expensive validate calls
    #   3. If entity has no media_id yet, block (ref image not generated yet)
    #   4. Pass all media_ids as imageInputs to batchGenerateImages
    char_media_ids = None
    char_names_raw = scene.get("character_names")
    if char_names_raw and req.get("project_id"):
        if isinstance(char_names_raw, str):
            try:
                char_names_raw = json.loads(char_names_raw)
            except json.JSONDecodeError:
                char_names_raw = []
        if not isinstance(char_names_raw, list):
            char_names_raw = []
        if char_names_raw:
            project_chars = await crud.get_project_characters(req["project_id"])
            valid_ids = []
            missing_refs = []
            for c in project_chars:
                if c["name"] not in char_names_raw:
                    continue
                mid = c.get("media_id")
                if mid:
                    valid_ids.append(mid)
                else:
                    # No media_id — ref image not generated yet, block
                    missing_refs.append(c["name"])

            # If ANY referenced entity is missing its ref image, block this request
            if missing_refs:
                return {"error": f"Waiting for reference images: {', '.join(missing_refs)}"}

            char_media_ids = valid_ids if valid_ids else None
            if char_media_ids:
                logger.info("Scene %s: using %d reference images", req.get("scene_id", "?")[:8], len(char_media_ids))

    return await client.generate_images(
        prompt=prompt, project_id=pid, aspect_ratio=aspect,
        user_paygate_tier=tier, character_media_ids=char_media_ids,
    )


async def _upload_character_image(client, char: dict, project_id: str) -> str | None:
    """Download character reference image and upload to Google Flow to get media_id.

    Returns media.name (used as mediaId in video gen) or None on failure.
    """
    import base64
    import aiohttp

    ref_url = char.get("reference_image_url")
    if not ref_url:
        return None

    try:
        # Download image
        async with aiohttp.ClientSession() as session:
            async with session.get(ref_url) as resp:
                if resp.status != 200:
                    logger.error("Failed to download character image: HTTP %d", resp.status)
                    return None
                image_bytes = await resp.read()
                content_type = resp.headers.get("content-type", "image/jpeg")

        # Determine mime type
        if "png" in content_type:
            mime = "image/png"
        elif "gif" in content_type:
            mime = "image/gif"
        else:
            mime = "image/jpeg"

        # Build file name from character name + mime extension
        ext = mime.split("/")[-1]
        file_name = f"{char.get('name', 'character')}.{ext}"

        # Upload
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        result = await client.upload_image(
            encoded, mime_type=mime, project_id=project_id, file_name=file_name,
        )

        # Extract media.name (set as _mediaId by upload_image)
        if result.get("_mediaId"):
            return result["_mediaId"]

        # Fallback: parse response directly
        data = result.get("data", {})
        if isinstance(data, dict):
            media = data.get("media", {})
            if isinstance(media, dict) and media.get("name"):
                return media["name"]

        return None
    except Exception as e:
        logger.exception("Failed to upload character image: %s", e)
        return None


# ─── Video Prompt Enhancement ──────────────────────────────

async def _build_video_prompt(base_prompt: str, scene: dict, project_id: str | None) -> str:
    """Enhance video prompt with character voice context and audio instructions.

    Appends:
    1. Voice descriptions from characters referenced in the scene (max 30 words each)
    2. No-background-music instruction (keep sound effects only)

    Example output:
        "0-3s: Luna walks to bed. 3-5s: Hand turns off lamp. 5-8s: Window starry sky.
        Character voices: Luna: Soft gentle whisper with slight purring.
        Audio: No background music. Keep natural sound effects only."
    """
    parts = [base_prompt.strip()]

    # Collect voice descriptions from referenced characters
    if project_id:
        char_names_raw = scene.get("character_names")
        if isinstance(char_names_raw, str):
            try:
                char_names_raw = json.loads(char_names_raw)
            except json.JSONDecodeError:
                char_names_raw = []
        if isinstance(char_names_raw, list) and char_names_raw:
            project_chars = await crud.get_project_characters(project_id)
            voices = []
            for c in project_chars:
                if c["name"] in char_names_raw and c.get("voice_description"):
                    voices.append(f"{c['name']}: {c['voice_description']}")
            if voices:
                parts.append("Character voices: " + ". ".join(voices) + ".")

    # No background music — sound effects only
    parts.append("Audio: No background music. Keep only natural sound effects and ambient sounds.")

    return " ".join(parts)


# ─── W6/W7: Video Generation (async — needs polling) ────────

async def _handle_generate_video(client, req: dict, orientation: str) -> dict:
    scene = await crud.get_scene(req["scene_id"]) if req.get("scene_id") else None
    if not scene:
        return {"error": "Scene not found"}

    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    image_media_id = scene.get(f"{prefix}_image_media_id")
    if not image_media_id:
        return {"error": f"No {prefix} image media_id for scene"}

    project = await crud.get_project(req["project_id"]) if req.get("project_id") else None
    aspect = "VIDEO_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "VIDEO_ASPECT_RATIO_LANDSCAPE"
    base_prompt = scene.get("video_prompt") or scene.get("prompt", "")
    tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"
    end_id = scene.get(f"{prefix}_end_scene_media_id")

    # Build enhanced prompt: base + voice context + no-music instruction
    prompt = await _build_video_prompt(base_prompt, scene, req.get("project_id"))

    # Step 1: Submit video generation
    submit_result = await client.generate_video(
        start_image_media_id=image_media_id,
        prompt=prompt,
        project_id=req.get("project_id", "0"),
        scene_id=req.get("scene_id", ""),
        aspect_ratio=aspect,
        end_image_media_id=end_id,
        user_paygate_tier=tier,
    )

    if _is_error(submit_result):
        return submit_result

    # Step 2: Extract operations — may already be complete
    operations = _extract_operations(submit_result)
    if not operations:
        return {"error": "Video gen returned no operations"}

    op_name = operations[0].get("operation", {}).get("name", "")
    await crud.update_request(req["id"], request_id=op_name)

    # Check if already complete (skip polling)
    status = operations[0].get("status", "")
    if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
        logger.info("Video gen completed immediately")
        return submit_result
    if status == "MEDIA_GENERATION_STATUS_FAILED":
        return {"error": "Video generation failed immediately"}

    logger.info("Video gen submitted, polling %d operations...", len(operations))
    return await _poll_operations(client, operations)


# ─── R2V: Video from References (async — needs polling) ─────

async def _handle_generate_video_refs(client, req: dict, orientation: str) -> dict:
    """Generate video from multiple character reference images (r2v).

    Instead of startImage (i2v), uses referenceImages — a list of character
    media_ids. The model composes a video from all references.
    """
    scene = await crud.get_scene(req["scene_id"]) if req.get("scene_id") else None
    if not scene:
        return {"error": "Scene not found"}

    project = await crud.get_project(req["project_id"]) if req.get("project_id") else None
    aspect = "VIDEO_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "VIDEO_ASPECT_RATIO_LANDSCAPE"
    base_prompt = scene.get("video_prompt") or scene.get("prompt", "")
    tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"

    # Build enhanced prompt with voice context + no-music
    prompt = await _build_video_prompt(base_prompt, scene, req.get("project_id"))

    # Get character media_ids
    char_names_raw = scene.get("character_names")
    if isinstance(char_names_raw, str):
        try:
            char_names_raw = json.loads(char_names_raw)
        except json.JSONDecodeError:
            char_names_raw = []

    if not char_names_raw or not req.get("project_id"):
        return {"error": "No characters for r2v video generation"}

    project_chars = await crud.get_project_characters(req["project_id"])
    ref_ids = []
    for c in project_chars:
        if c["name"] not in char_names_raw:
            continue
        mid = c.get("media_id")
        if mid:
            is_valid = await client.validate_media_id(mid)
            if is_valid:
                ref_ids.append(mid)
                continue
            # Re-upload
            logger.warning("Character %s media_id expired for r2v, re-uploading", c["name"])
            new_mid = await _upload_character_image(client, c, req.get("project_id", ""))
            if new_mid:
                await crud.update_character(c["id"], media_id=new_mid)
                ref_ids.append(new_mid)

    if not ref_ids:
        return {"error": "No valid character media_ids for r2v"}

    # Submit r2v
    submit_result = await client.generate_video_from_references(
        reference_media_ids=ref_ids,
        prompt=prompt,
        project_id=req.get("project_id", "0"),
        scene_id=req.get("scene_id", ""),
        aspect_ratio=aspect,
        user_paygate_tier=tier,
    )

    if _is_error(submit_result):
        return submit_result

    operations = _extract_operations(submit_result)
    if not operations:
        return {"error": "R2V returned no operations"}

    op_name = operations[0].get("operation", {}).get("name", "")
    await crud.update_request(req["id"], request_id=op_name)

    status = operations[0].get("status", "")
    if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
        logger.info("R2V completed immediately")
        return submit_result
    if status == "MEDIA_GENERATION_STATUS_FAILED":
        return {"error": "R2V failed immediately"}

    logger.info("R2V submitted with %d refs, polling %d operations...", len(ref_ids), len(operations))
    return await _poll_operations(client, operations)


# ─── W8: Upscale Video (async — needs polling) ──────────────

async def _handle_upscale_video(client, req: dict, orientation: str) -> dict:
    scene = await crud.get_scene(req["scene_id"]) if req.get("scene_id") else None
    if not scene:
        return {"error": "Scene not found"}

    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    video_media_id = scene.get(f"{prefix}_video_media_id")
    if not video_media_id:
        return {"error": f"No {prefix} video media_id for scene"}

    aspect = "VIDEO_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "VIDEO_ASPECT_RATIO_LANDSCAPE"

    # Step 1: Submit upscale
    submit_result = await client.upscale_video(
        media_id=video_media_id,
        scene_id=req.get("scene_id", ""),
        aspect_ratio=aspect,
    )

    if _is_error(submit_result):
        return submit_result

    # Step 2: Extract operations — may already be complete
    operations = _extract_operations(submit_result)
    if not operations:
        return {"error": "Upscale returned no operations"}

    op_name = operations[0].get("operation", {}).get("name", "")
    await crud.update_request(req["id"], request_id=op_name)

    status = operations[0].get("status", "")
    if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
        logger.info("Upscale completed immediately")
        return submit_result
    if status == "MEDIA_GENERATION_STATUS_FAILED":
        return {"error": "Upscale failed immediately"}

    logger.info("Upscale submitted, polling %d operations...", len(operations))
    return await _poll_operations(client, operations, timeout=300)


# ─── Reference Image Aspect Ratio ──────────────────────────

# Entity types that need landscape (wide) reference images
_LANDSCAPE_ENTITY_TYPES = {"location"}
# Everything else (character, creature, visual_asset, generic_troop, faction) uses portrait


def _reference_aspect_ratio(entity_type: str) -> str:
    """Pick aspect ratio based on entity type.

    Locations need landscape (16:9) for establishing shots.
    Characters/creatures/assets need portrait for full-body head-to-toe.
    """
    if entity_type in _LANDSCAPE_ENTITY_TYPES:
        return "IMAGE_ASPECT_RATIO_LANDSCAPE"
    return "IMAGE_ASPECT_RATIO_PORTRAIT"


# ─── Character/Reference Image (sync, like W5) ──────────────

async def _handle_generate_character_image(client, req: dict) -> dict:
    char = await crud.get_character(req["character_id"]) if req.get("character_id") else None
    if not char:
        return {"error": "Character not found"}

    pid = req.get("project_id", "0")
    # Prefer image_prompt (detailed generation prompt) over description
    prompt = char.get("image_prompt") or f"Character reference: {char['name']}. {char.get('description', '')}"

    project = await crud.get_project(pid) if pid != "0" else None
    tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"
    entity_type = char.get("entity_type", "character")
    aspect = _reference_aspect_ratio(entity_type)

    result = await client.generate_images(
        prompt=prompt,
        project_id=pid,
        aspect_ratio=aspect,
        user_paygate_tier=tier,
    )

    if not _is_error(result):
        output_url = _extract_output_url(result, "GENERATE_IMAGES")

        if output_url:
            # Step 2: Upload the generated image to get a proper UUID media_id.
            # batchGenerateImages returns mediaGenerationId (CAMS...) but
            # imageInputs[].name needs the UUID from uploadImage (media.name).
            upload_mid = await _upload_character_image(client, {
                "name": char["name"],
                "reference_image_url": output_url,
            }, pid)

            if upload_mid:
                await crud.update_character(char["id"], media_id=upload_mid, reference_image_url=output_url)
                logger.info("%s '%s' ref image uploaded (%s): media_id=%s",
                            entity_type, char["name"], aspect.split("_")[-1].lower(),
                            upload_mid[:30] if upload_mid else "?")
            else:
                # Upload failed — store ref URL but NOT a bad media_id.
                # This forces retry on next scene image gen (reference blocking will catch it).
                await crud.update_character(char["id"], reference_image_url=output_url)
                logger.warning("%s '%s' upload failed, no media_id stored — will retry on next use", entity_type, char["name"])
                return {"error": f"Upload failed for {char['name']} — image generated but could not get UUID media_id"}

    return result


# ─── Scene Update ────────────────────────────────────────────

async def _update_scene_from_result(req: dict, orientation: str, media_id: str, output_url: str):
    """Update scene fields based on completed request.

    CRITICAL: When regenerating, must cascade-clear downstream data.
    Otherwise the system silently uses stale media_ids:
      - Regen image → old video/upscale media_ids still point to OLD image's derivatives
      - Regen video → old upscale media_id still points to OLD video
    This causes silent failures where everything looks "complete" but uses wrong assets.
    """
    scene_id = req.get("scene_id")
    if not scene_id:
        return

    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    req_type = req["type"]
    updates = {}

    if req_type == "GENERATE_IMAGES":
        # Set new image data
        updates[f"{prefix}_image_media_id"] = media_id
        updates[f"{prefix}_image_url"] = output_url
        updates[f"{prefix}_image_status"] = "COMPLETED"

        # CASCADE: Clear downstream video + upscale (they depend on this image)
        updates[f"{prefix}_video_media_id"] = None
        updates[f"{prefix}_video_url"] = None
        updates[f"{prefix}_video_status"] = "PENDING"
        updates[f"{prefix}_upscale_media_id"] = None
        updates[f"{prefix}_upscale_url"] = None
        updates[f"{prefix}_upscale_status"] = "PENDING"
        logger.info("Cascade clear: %s video + upscale reset for scene %s (image regen)", prefix, scene_id[:8])

    elif req_type in ("GENERATE_VIDEO", "GENERATE_VIDEO_REFS"):
        # Set new video data
        updates[f"{prefix}_video_media_id"] = media_id
        updates[f"{prefix}_video_url"] = output_url
        updates[f"{prefix}_video_status"] = "COMPLETED"

        # CASCADE: Clear downstream upscale (it depends on this video)
        updates[f"{prefix}_upscale_media_id"] = None
        updates[f"{prefix}_upscale_url"] = None
        updates[f"{prefix}_upscale_status"] = "PENDING"
        logger.info("Cascade clear: %s upscale reset for scene %s (video regen)", prefix, scene_id[:8])

    elif req_type == "UPSCALE_VIDEO":
        # Terminal — no downstream to clear
        updates[f"{prefix}_upscale_media_id"] = media_id
        updates[f"{prefix}_upscale_url"] = output_url
        updates[f"{prefix}_upscale_status"] = "COMPLETED"

    if updates:
        await crud.update_scene(scene_id, **updates)
