"""Skill runner API endpoints mirroring fk-* workflow commands."""
import asyncio
import re
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.db import crud
from agent.services.flow_client import get_flow_client

router = APIRouter(prefix="/skills", tags=["skills"])

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class SkillBaseRequest(BaseModel):
    project_id: str
    video_id: Optional[str] = None
    orientation: Optional[Literal["VERTICAL", "HORIZONTAL"]] = None
    regenerate: bool = False
    wait: bool = True
    poll_interval_sec: int = Field(5, ge=1, le=60)
    timeout_sec: int = Field(1800, ge=10, le=7200)


class PipelineRequest(BaseModel):
    project_id: str
    video_id: str
    orientation: Optional[Literal["VERTICAL", "HORIZONTAL"]] = None
    regenerate_refs: bool = False
    regenerate_images: bool = False
    regenerate_videos: bool = False
    include_upscale: bool = False
    poll_interval_sec: int = Field(5, ge=1, le=60)
    timeout_sec: int = Field(1800, ge=10, le=7200)


def _is_uuid(value: Optional[str]) -> bool:
    return bool(value and _UUID_RE.match(value))


def _orientation_prefix(orientation: str) -> str:
    return "vertical" if orientation == "VERTICAL" else "horizontal"


def _scene_ready_for_image(scene: dict, orientation: str) -> bool:
    p = _orientation_prefix(orientation)
    return scene.get(f"{p}_image_status") == "COMPLETED" and _is_uuid(scene.get(f"{p}_image_media_id"))


def _scene_ready_for_video(scene: dict, orientation: str) -> bool:
    p = _orientation_prefix(orientation)
    return scene.get(f"{p}_video_status") == "COMPLETED" and _is_uuid(scene.get(f"{p}_video_media_id"))


def _scene_ready_for_upscale(scene: dict, orientation: str) -> bool:
    p = _orientation_prefix(orientation)
    return scene.get(f"{p}_upscale_status") == "COMPLETED" and _is_uuid(scene.get(f"{p}_upscale_media_id"))


async def _require_extension_connected() -> None:
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")


async def _resolve_orientation(video_id: str, explicit: Optional[str]) -> str:
    if explicit in ("VERTICAL", "HORIZONTAL"):
        return explicit

    video = await crud.get_video(video_id)
    if video and video.get("orientation") in ("VERTICAL", "HORIZONTAL"):
        return video["orientation"]

    scenes = await crud.list_scenes(video_id)
    if scenes:
        first = scenes[0]
        has_vertical = any(first.get(k) not in (None, "", "PENDING") for k in (
            "vertical_image_status", "vertical_video_status", "vertical_upscale_status",
        )) or any(_is_uuid(first.get(k)) for k in (
            "vertical_image_media_id", "vertical_video_media_id", "vertical_upscale_media_id",
        ))
        has_horizontal = any(first.get(k) not in (None, "", "PENDING") for k in (
            "horizontal_image_status", "horizontal_video_status", "horizontal_upscale_status",
        )) or any(_is_uuid(first.get(k)) for k in (
            "horizontal_image_media_id", "horizontal_video_media_id", "horizontal_upscale_media_id",
        ))
        if has_horizontal and not has_vertical:
            return "HORIZONTAL"
        if has_vertical:
            return "VERTICAL"

    return "VERTICAL"


async def _create_batch_requests(items: list[dict]) -> list[dict]:
    """Behavior-compatible with POST /api/requests/batch."""
    seen_videos: set[str] = set()
    for item in items:
        vid = item.get("video_id")
        orient = item.get("orientation")
        if vid and orient and vid not in seen_videos:
            seen_videos.add(vid)
            await crud.update_video(vid, orientation=orient)

    results: list[dict] = []
    for item in items:
        req_type = item["type"]
        scene_id = item.get("scene_id")
        character_id = item.get("character_id")
        project_id = item.get("project_id")

        if scene_id:
            existing = await crud.list_requests(scene_id=scene_id)
            active = [r for r in existing if r.get("type") == req_type and r.get("status") in ("PENDING", "PROCESSING")]
            if active:
                results.append(active[0])
                continue
        if character_id:
            existing = await crud.list_requests(project_id=project_id)
            active = [
                r for r in existing
                if r.get("character_id") == character_id
                and r.get("type") == req_type
                and r.get("status") in ("PENDING", "PROCESSING")
            ]
            if active:
                results.append(active[0])
                continue

        data = dict(item)
        data["req_type"] = data.pop("type")
        results.append(await crud.create_request(**data))
    return results


async def _wait_requests(request_ids: list[str], poll_interval_sec: int, timeout_sec: int) -> dict:
    if not request_ids:
        return {"done": True, "completed": 0, "failed": 0, "pending_or_processing": 0}

    started = asyncio.get_event_loop().time()
    req_id_set = set(request_ids)

    while True:
        all_rows = [await crud.get_request(rid) for rid in request_ids]
        rows = [r for r in all_rows if r]
        if len(rows) != len(req_id_set):
            missing = [rid for rid, row in zip(request_ids, all_rows) if row is None]
            raise HTTPException(500, f"Missing queued requests: {missing}")

        pending_or_processing = [r for r in rows if r.get("status") in ("PENDING", "PROCESSING")]
        failed = [r for r in rows if r.get("status") == "FAILED"]
        completed = [r for r in rows if r.get("status") == "COMPLETED"]

        if not pending_or_processing:
            return {
                "done": True,
                "completed": len(completed),
                "failed": len(failed),
                "pending_or_processing": 0,
                "errors": [f"{r.get('id')[:8]}: {r.get('error_message')}" for r in failed[:5]],
            }

        elapsed = asyncio.get_event_loop().time() - started
        if elapsed > timeout_sec:
            return {
                "done": False,
                "completed": len(completed),
                "failed": len(failed),
                "pending_or_processing": len(pending_or_processing),
            }
        await asyncio.sleep(poll_interval_sec)


def _build_image_waves(scenes: list[dict], only_ids: set[str]) -> list[list[dict]]:
    by_id = {s["id"]: s for s in scenes}
    remaining = set(only_ids)
    waves: list[list[dict]] = []

    while remaining:
        wave_ids: list[str] = []
        for sid in sorted(remaining):
            scene = by_id[sid]
            parent_id = scene.get("parent_scene_id")
            is_cont = scene.get("chain_type") == "CONTINUATION" and parent_id
            if not is_cont:
                wave_ids.append(sid)
                continue
            if parent_id not in remaining:
                wave_ids.append(sid)

        if not wave_ids:
            raise HTTPException(400, "Unable to resolve CONTINUATION dependency chain for image generation")

        for sid in wave_ids:
            remaining.remove(sid)
        waves.append([by_id[sid] for sid in wave_ids])
    return waves


async def _run_gen_refs(body: SkillBaseRequest) -> dict:
    await _require_extension_connected()
    project = await crud.get_project(body.project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    chars = await crud.get_project_characters(body.project_id)
    if not chars:
        raise HTTPException(400, "No entities found in project")

    req_type = "REGENERATE_CHARACTER_IMAGE" if body.regenerate else "GENERATE_CHARACTER_IMAGE"
    targets = chars if body.regenerate else [c for c in chars if not _is_uuid(c.get("media_id"))]
    reqs = [{"type": req_type, "project_id": body.project_id, "character_id": c["id"]} for c in targets]
    queued = await _create_batch_requests(reqs)

    wait_result = None
    if body.wait:
        wait_result = await _wait_requests([r["id"] for r in queued], body.poll_interval_sec, body.timeout_sec)
        if not wait_result.get("done"):
            raise HTTPException(504, f"fk-gen-refs timeout: {wait_result}")

    return {
        "ok": True,
        "skill": "fk-gen-refs",
        "request_type": req_type,
        "total_entities": len(chars),
        "targeted": len(targets),
        "queued": len(queued),
        "wait_result": wait_result,
    }


async def _run_gen_images(body: SkillBaseRequest) -> dict:
    await _require_extension_connected()
    if not body.video_id:
        raise HTTPException(400, "video_id is required")

    project = await crud.get_project(body.project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    video = await crud.get_video(body.video_id)
    if not video or video.get("project_id") != body.project_id:
        raise HTTPException(404, "Video not found in project")

    characters = await crud.get_project_characters(body.project_id)
    missing_refs = [c.get("name", c["id"]) for c in characters if not _is_uuid(c.get("media_id"))]
    if missing_refs:
        raise HTTPException(400, f"Missing reference images for entities: {', '.join(missing_refs[:10])}")

    orientation = await _resolve_orientation(body.video_id, body.orientation)
    scenes = await crud.list_scenes(body.video_id)
    if not scenes:
        raise HTTPException(400, "No scenes found in video")

    target_ids: set[str] = set()
    for s in scenes:
        ready = _scene_ready_for_image(s, orientation)
        if body.regenerate or not ready:
            target_ids.add(s["id"])
    if not target_ids:
        return {"ok": True, "skill": "fk-gen-images", "orientation": orientation, "queued": 0, "waves": 0}

    waves = _build_image_waves(scenes, target_ids)
    if not body.wait and len(waves) > 1:
        raise HTTPException(400, "fk-gen-images with CONTINUATION chains requires wait=true")

    queued_ids: list[str] = []
    wave_results: list[dict] = []
    for idx, wave in enumerate(waves, start=1):
        reqs = []
        for s in wave:
            parent_id = s.get("parent_scene_id")
            is_cont = s.get("chain_type") == "CONTINUATION" and parent_id
            req_type = "EDIT_IMAGE" if is_cont else ("REGENERATE_IMAGE" if body.regenerate else "GENERATE_IMAGE")
            reqs.append({
                "type": req_type,
                "orientation": orientation,
                "project_id": body.project_id,
                "video_id": body.video_id,
                "scene_id": s["id"],
            })
        queued = await _create_batch_requests(reqs)
        ids = [r["id"] for r in queued]
        queued_ids.extend(ids)

        wave_wait = None
        if body.wait:
            wave_wait = await _wait_requests(ids, body.poll_interval_sec, body.timeout_sec)
            if not wave_wait.get("done"):
                raise HTTPException(504, f"fk-gen-images timeout on wave {idx}: {wave_wait}")
        wave_results.append({"wave": idx, "count": len(ids), "wait_result": wave_wait})

    return {
        "ok": True,
        "skill": "fk-gen-images",
        "orientation": orientation,
        "waves": len(waves),
        "queued": len(queued_ids),
        "wave_results": wave_results,
    }


async def _run_gen_videos(body: SkillBaseRequest) -> dict:
    await _require_extension_connected()
    if not body.video_id:
        raise HTTPException(400, "video_id is required")

    project = await crud.get_project(body.project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    video = await crud.get_video(body.video_id)
    if not video or video.get("project_id") != body.project_id:
        raise HTTPException(404, "Video not found in project")

    orientation = await _resolve_orientation(body.video_id, body.orientation)
    scenes = await crud.list_scenes(body.video_id)
    if not scenes:
        raise HTTPException(400, "No scenes found in video")

    not_ready = [s["id"] for s in scenes if not _scene_ready_for_image(s, orientation)]
    if not_ready:
        raise HTTPException(400, f"Scenes missing completed images: {', '.join(not_ready[:10])}")

    req_type = "REGENERATE_VIDEO" if body.regenerate else "GENERATE_VIDEO"
    targets = scenes if body.regenerate else [s for s in scenes if not _scene_ready_for_video(s, orientation)]
    reqs = [{
        "type": req_type,
        "orientation": orientation,
        "project_id": body.project_id,
        "video_id": body.video_id,
        "scene_id": s["id"],
    } for s in targets]
    queued = await _create_batch_requests(reqs)

    wait_result = None
    if body.wait:
        wait_result = await _wait_requests([r["id"] for r in queued], body.poll_interval_sec, body.timeout_sec)
        if not wait_result.get("done"):
            raise HTTPException(504, f"fk-gen-videos timeout: {wait_result}")

    return {
        "ok": True,
        "skill": "fk-gen-videos",
        "orientation": orientation,
        "request_type": req_type,
        "total_scenes": len(scenes),
        "targeted": len(targets),
        "queued": len(queued),
        "wait_result": wait_result,
    }


async def _run_upscale(body: SkillBaseRequest) -> dict:
    await _require_extension_connected()
    if not body.video_id:
        raise HTTPException(400, "video_id is required")

    project = await crud.get_project(body.project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    video = await crud.get_video(body.video_id)
    if not video or video.get("project_id") != body.project_id:
        raise HTTPException(404, "Video not found in project")

    orientation = await _resolve_orientation(body.video_id, body.orientation)
    scenes = await crud.list_scenes(body.video_id)
    if not scenes:
        raise HTTPException(400, "No scenes found in video")

    not_ready = [s["id"] for s in scenes if not _scene_ready_for_video(s, orientation)]
    if not_ready:
        raise HTTPException(400, f"Scenes missing completed videos: {', '.join(not_ready[:10])}")

    targets = scenes if body.regenerate else [s for s in scenes if not _scene_ready_for_upscale(s, orientation)]
    reqs = [{
        "type": "UPSCALE_VIDEO",
        "orientation": orientation,
        "project_id": body.project_id,
        "video_id": body.video_id,
        "scene_id": s["id"],
    } for s in targets]
    queued = await _create_batch_requests(reqs)

    wait_result = None
    if body.wait:
        wait_result = await _wait_requests([r["id"] for r in queued], body.poll_interval_sec, body.timeout_sec)
        if not wait_result.get("done"):
            raise HTTPException(504, f"fk-upscale timeout: {wait_result}")

    return {
        "ok": True,
        "skill": "fk-upscale",
        "orientation": orientation,
        "targeted": len(targets),
        "queued": len(queued),
        "wait_result": wait_result,
    }


@router.post("/fk-gen-refs")
async def fk_gen_refs(body: SkillBaseRequest):
    return await _run_gen_refs(body)


@router.post("/fk-gen-images")
async def fk_gen_images(body: SkillBaseRequest):
    return await _run_gen_images(body)


@router.post("/fk-gen-videos")
async def fk_gen_videos(body: SkillBaseRequest):
    return await _run_gen_videos(body)


@router.post("/fk-upscale")
async def fk_upscale(body: SkillBaseRequest):
    return await _run_upscale(body)


@router.post("/fk-pipeline")
async def fk_pipeline(body: PipelineRequest):
    refs_result = await _run_gen_refs(SkillBaseRequest(
        project_id=body.project_id,
        regenerate=body.regenerate_refs,
        wait=True,
        poll_interval_sec=body.poll_interval_sec,
        timeout_sec=body.timeout_sec,
    ))
    images_result = await _run_gen_images(SkillBaseRequest(
        project_id=body.project_id,
        video_id=body.video_id,
        orientation=body.orientation,
        regenerate=body.regenerate_images,
        wait=True,
        poll_interval_sec=body.poll_interval_sec,
        timeout_sec=body.timeout_sec,
    ))
    videos_result = await _run_gen_videos(SkillBaseRequest(
        project_id=body.project_id,
        video_id=body.video_id,
        orientation=body.orientation,
        regenerate=body.regenerate_videos,
        wait=True,
        poll_interval_sec=body.poll_interval_sec,
        timeout_sec=body.timeout_sec,
    ))

    upscale_result = None
    if body.include_upscale:
        upscale_result = await _run_upscale(SkillBaseRequest(
            project_id=body.project_id,
            video_id=body.video_id,
            orientation=body.orientation,
            regenerate=False,
            wait=True,
            poll_interval_sec=body.poll_interval_sec,
            timeout_sec=body.timeout_sec,
        ))

    return {
        "ok": True,
        "skill": "fk-pipeline",
        "refs": refs_result,
        "images": images_result,
        "videos": videos_result,
        "upscale": upscale_result,
    }
