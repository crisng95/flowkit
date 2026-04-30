"""Stage payload builders and stage handlers for lane jobs."""

from __future__ import annotations

from pathlib import Path
import httpx

from .client import FlowKitClient
from .config import settings
from .media import concat_clips, local_clip_path, normalize_clip, prefer_scene_video_url, probe_dimensions, probe_duration
from .storage import insert_artifact, update_chapter_state
from .upload import sha256_file, upload_file


def build_ref_requests(project_id: str, character_ids: list[str]) -> dict:
    return {
        "requests": [
            {
                "type": "GENERATE_CHARACTER_IMAGE",
                "character_id": character_id,
                "project_id": project_id,
            }
            for character_id in character_ids
        ]
    }


def build_scene_requests(job_type: str, *, project_id: str, video_id: str, scene_ids: list[str], orientation: str) -> dict:
    return {
        "requests": [
            {
                "type": job_type,
                "scene_id": scene_id,
                "project_id": project_id,
                "video_id": video_id,
                "orientation": orientation,
            }
            for scene_id in scene_ids
        ]
    }


def _ensure_requests_succeeded(job_type: str, records: list[dict]) -> list[dict]:
    failed = [record for record in records if record.get("status", "COMPLETED") != "COMPLETED"]
    if failed:
        summary = ", ".join(
            f"{record.get('id', 'unknown')}:{record.get('status', 'UNKNOWN')}"
            for record in failed
        )
        raise RuntimeError(f"{job_type} returned failed requests: {summary}")
    return records


def _ensure_scene_outputs_available(
    client: FlowKitClient,
    *,
    video_id: str,
    scene_ids: list[str],
    orientation: str,
    asset_kind: str,
) -> None:
    prefix = "vertical" if orientation.upper() == "VERTICAL" else "horizontal"
    url_key = f"{prefix}_{asset_kind}_url"
    status_key = f"{prefix}_{asset_kind}_status"
    scenes = {scene["id"]: scene for scene in client.list_video_scenes(video_id)}

    missing = []
    for scene_id in scene_ids:
        scene = scenes.get(scene_id)
        if not scene:
            missing.append(f"{scene_id}:MISSING")
            continue
        status = scene.get(status_key)
        url = scene.get(url_key)
        if status != "COMPLETED" or not url:
            missing.append(f"{scene_id}:{status or 'UNKNOWN'}")

    if missing:
        raise RuntimeError(f"{asset_kind.upper()} outputs not ready for scenes: {', '.join(missing)}")


def _chapter_local_project_id(chapter: dict) -> str:
    project_id = chapter.get("local_flow_project_id")
    if not project_id:
        raise ValueError("Chapter has no local_flow_project_id yet")
    return project_id


def _chapter_local_video_id(chapter: dict) -> str:
    meta = chapter.get("chapter_metadata") or {}
    video_id = meta.get("local_video_id")
    if not video_id:
        raise ValueError("Chapter metadata has no local_video_id yet")
    return video_id


def handle_create_project(client: FlowKitClient, chapter_id: str, payload: dict) -> dict:
    result = client.create_project(payload)
    update_chapter_state(
        chapter_id,
        status="running",
        local_flow_project_id=result["id"],
        metadata_patch={"local_project_name": result["name"]},
    )
    return result


def handle_create_entities(client: FlowKitClient, chapter: dict, payload: dict) -> list[dict]:
    project_id = _chapter_local_project_id(chapter)
    created = []
    for entity in payload.get("entities", []):
        character = client.create_character(entity)
        client.link_project_character(project_id, character["id"])
        created.append(character)
    update_chapter_state(
        chapter["id"],
        metadata_patch={
            "local_character_ids": [character["id"] for character in created],
            "local_character_names": [character["name"] for character in created],
        },
    )
    return created


def handle_create_video(client: FlowKitClient, chapter: dict, payload: dict) -> dict:
    body = dict(payload)
    body["project_id"] = _chapter_local_project_id(chapter)
    result = client.create_video(body)
    update_chapter_state(chapter["id"], metadata_patch={"local_video_id": result["id"]})
    return result


def handle_create_scenes(client: FlowKitClient, chapter: dict, payload: dict) -> list[dict]:
    video_id = _chapter_local_video_id(chapter)
    created = []
    previous_scene_id = None
    for scene in payload["scenes"]:
        scene_body = dict(scene)
        scene_body["video_id"] = video_id
        if previous_scene_id and scene_body.get("chain_type") == "CONTINUATION" and not scene_body.get("parent_scene_id"):
            scene_body["parent_scene_id"] = previous_scene_id
        if not created:
            scene_body.pop("parent_scene_id", None)
        created.append(client.create_scene(scene_body))
        previous_scene_id = created[-1]["id"]
    update_chapter_state(chapter["id"], metadata_patch={"local_scene_ids": [scene["id"] for scene in created]})
    return created


def handle_gen_refs(client: FlowKitClient, chapter: dict, payload: dict) -> list[dict]:
    project_id = _chapter_local_project_id(chapter)
    character_ids = payload.get("character_ids")
    if not character_ids:
        character_ids = [character["id"] for character in client.list_project_characters(project_id)]
    requests = client.submit_requests_batch(build_ref_requests(project_id, character_ids))
    return _ensure_requests_succeeded("GENERATE_CHARACTER_IMAGE", client.wait_for_requests([request["id"] for request in requests]))


def handle_gen_images(client: FlowKitClient, chapter: dict, payload: dict) -> list[dict]:
    project_id = _chapter_local_project_id(chapter)
    video_id = _chapter_local_video_id(chapter)
    scene_ids = payload.get("scene_ids")
    if not scene_ids:
        scene_ids = [scene["id"] for scene in client.list_video_scenes(video_id)]
    requests = client.submit_requests_batch(
        build_scene_requests(
            "GENERATE_IMAGE",
            project_id=project_id,
            video_id=video_id,
            scene_ids=scene_ids,
            orientation=payload.get("orientation", "VERTICAL"),
        )
    )
    records = _ensure_requests_succeeded("GENERATE_IMAGE", client.wait_for_requests([request["id"] for request in requests]))
    _ensure_scene_outputs_available(client, video_id=video_id, scene_ids=scene_ids, orientation=payload.get("orientation", "VERTICAL"), asset_kind="image")
    return records


def handle_gen_videos(client: FlowKitClient, chapter: dict, payload: dict) -> list[dict]:
    project_id = _chapter_local_project_id(chapter)
    video_id = _chapter_local_video_id(chapter)
    scene_ids = payload.get("scene_ids")
    if not scene_ids:
        scene_ids = [scene["id"] for scene in client.list_video_scenes(video_id)]
    requests = client.submit_requests_batch(
        build_scene_requests(
            "GENERATE_VIDEO",
            project_id=project_id,
            video_id=video_id,
            scene_ids=scene_ids,
            orientation=payload.get("orientation", "VERTICAL"),
        )
    )
    records = _ensure_requests_succeeded(
        "GENERATE_VIDEO",
        client.wait_for_requests([request["id"] for request in requests], timeout_seconds=1800, poll_interval=10),
    )
    _ensure_scene_outputs_available(client, video_id=video_id, scene_ids=scene_ids, orientation=payload.get("orientation", "VERTICAL"), asset_kind="video")
    return records


def handle_upscale(client: FlowKitClient, chapter: dict, payload: dict) -> list[dict]:
    project_id = _chapter_local_project_id(chapter)
    video_id = _chapter_local_video_id(chapter)
    scene_ids = payload.get("scene_ids")
    if not scene_ids:
        scene_ids = [scene["id"] for scene in client.list_video_scenes(video_id)]
    requests = client.submit_requests_batch(
        build_scene_requests(
            "UPSCALE_VIDEO",
            project_id=project_id,
            video_id=video_id,
            scene_ids=scene_ids,
            orientation=payload.get("orientation", "VERTICAL"),
        )
    )
    records = _ensure_requests_succeeded(
        "UPSCALE_VIDEO",
        client.wait_for_requests([request["id"] for request in requests], timeout_seconds=1800, poll_interval=10),
    )
    _ensure_scene_outputs_available(client, video_id=video_id, scene_ids=scene_ids, orientation=payload.get("orientation", "VERTICAL"), asset_kind="upscale")
    return records


def handle_concat_chapter(chapter: dict, payload: dict) -> dict:
    client = FlowKitClient()
    project_id = _chapter_local_project_id(chapter)
    video_id = payload.get("video_id") or _chapter_local_video_id(chapter)
    orientation = payload.get("orientation", "VERTICAL")
    prefer_4k = bool(payload.get("prefer_4k", False))

    out_meta = client.get_project_output_dir(project_id)
    output_dir = Path(settings.flow_agent_dir) / out_meta["path"]
    scenes = sorted(client.list_video_scenes(video_id), key=lambda scene: scene["display_order"])
    if not scenes:
        raise ValueError("No scenes found for concat")

    downloaded = []
    with httpx.Client(timeout=120.0, follow_redirects=True) as http:
        for scene in scenes:
            local_path = local_clip_path(output_dir, scene["display_order"], scene["id"])
            if not local_path.exists():
                source_url = prefer_scene_video_url(scene, orientation=orientation, prefer_4k=prefer_4k)
                if not source_url:
                    raise ValueError(f"Scene {scene['id']} has no downloadable video source")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with http.stream("GET", source_url) as resp:
                    resp.raise_for_status()
                    with local_path.open("wb") as handle:
                        for chunk in resp.iter_bytes():
                            handle.write(chunk)
            downloaded.append(local_path)

    width, height = probe_dimensions(downloaded[0])
    normalized = []
    for scene, source in zip(scenes, downloaded):
        target = output_dir / "norm" / source.name
        normalize_clip(source, target, width, height)
        normalized.append(target)

    final_name = f"{out_meta['slug']}_final.mp4"
    final_path = output_dir / final_name
    concat_clips(normalized, final_path)
    duration = probe_duration(final_path)
    update_chapter_state(chapter["id"], chapter_output_uri=str(final_path), metadata_patch={"local_final_path": str(final_path)})
    return {
        "status": "completed",
        "chapter_id": chapter["id"],
        "final_path": str(final_path),
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "scene_count": len(scenes),
    }


def handle_upload_artifacts(chapter: dict, payload: dict) -> dict:
    project_id = chapter["project_id"]
    project_slug = chapter["project_slug"]
    chapter_slug = chapter["chapter_slug"]
    meta = chapter.get("chapter_metadata") or {}

    final_path = Path(meta.get("local_final_path", ""))
    if not final_path.exists():
        raise ValueError("Chapter final file not found for upload")

    uploads = []
    upload_mode = "r2"

    def store_artifact(path: Path, key: str) -> str:
        nonlocal upload_mode
        try:
            return upload_file(path, key)
        except Exception:
            if not settings.allow_local_artifact_fallback:
                raise
            upload_mode = "local_fallback"
            return path.resolve().as_uri()

    key = f"{settings.r2_prefix}/{project_slug}/{chapter_slug}/final.mp4"
    uri = store_artifact(final_path, key)
    checksum = sha256_file(final_path)
    insert_artifact(
        project_id=project_id,
        chapter_id=chapter["id"],
        lane_id=settings.lane_id,
        artifact_type="chapter_final",
        local_path=str(final_path),
        storage_uri=uri,
        checksum_sha256=checksum,
        size_bytes=final_path.stat().st_size,
        artifact_metadata={"chapter_slug": chapter_slug, "upload_mode": upload_mode},
    )
    uploads.append(uri)

    meta_path = final_path.parent / "meta.json"
    if meta_path.exists():
        meta_key = f"{settings.r2_prefix}/{project_slug}/{chapter_slug}/meta.json"
        meta_uri = store_artifact(meta_path, meta_key)
        insert_artifact(
            project_id=project_id,
            chapter_id=chapter["id"],
            lane_id=settings.lane_id,
            artifact_type="manifest",
            local_path=str(meta_path),
            storage_uri=meta_uri,
            checksum_sha256=sha256_file(meta_path),
            size_bytes=meta_path.stat().st_size,
            artifact_metadata={"chapter_slug": chapter_slug, "upload_mode": upload_mode},
        )
        uploads.append(meta_uri)

    update_chapter_state(
        chapter["id"],
        status="completed",
        metadata_patch={"uploaded_uris": uploads, "upload_mode": upload_mode},
    )
    return {
        "status": "completed",
        "chapter_id": chapter["id"],
        "uploaded": uploads,
        "upload_mode": upload_mode,
    }
