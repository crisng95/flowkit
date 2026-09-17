"""Shared polling helpers for Flow workflow-backed video jobs.

Workflow-producing surfaces (Omni and native video export) return the same
logical pair: a workflow name plus a primary media id. This module owns the
normalization, response annotation and one-pass polling so each feature does
not grow its own copy of transport/status handling.
"""
from __future__ import annotations

from agent.config import USE_BATCH_RPC
from agent.services.flow_client import get_flow_client

_ALLOWED_MEDIA_URL_PREFIX = "https://flow-content.google/"
_POLL_MODES = {"project_media", "batch_media", "media_redirect"}


def normalize_workflow(workflow: dict) -> dict | None:
    """Normalize a raw Flow workflow or a FlowKit polling descriptor."""
    if not isinstance(workflow, dict):
        return None
    name = workflow.get("name")
    primary_media_id = workflow.get("primary_media_id")
    if not primary_media_id:
        metadata = workflow.get("metadata")
        if isinstance(metadata, dict):
            primary_media_id = metadata.get("primaryMediaId")
    if not isinstance(name, str) or not name:
        return None
    if not isinstance(primary_media_id, str) or not primary_media_id:
        return None
    item = {"name": name, "primary_media_id": primary_media_id}
    project_id = workflow.get("project_id") or workflow.get("projectId")
    if isinstance(project_id, str) and project_id:
        item["project_id"] = project_id
    return item


def extract_workflows(result: dict) -> list[dict]:
    """Extract normalized workflow descriptors from a submit response."""
    if not isinstance(result, dict):
        return []
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    workflows = data.get("workflows", []) if isinstance(data, dict) else []
    return [item for workflow in workflows if (item := normalize_workflow(workflow))]


def annotate_polling(result: dict, *, mode: str, project_id: str = "") -> dict:
    """Attach the descriptor callers can pass back to ``/flow/check-status``."""
    if mode not in _POLL_MODES:
        raise ValueError(f"Unknown Flow polling mode: {mode}")
    workflows = extract_workflows(result)
    if not workflows:
        return result
    if project_id:
        for workflow in workflows:
            workflow["project_id"] = project_id
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    if isinstance(data, dict):
        descriptor = {"mode": mode, "workflows": workflows}
        if project_id:
            descriptor["project_id"] = project_id
        data["flowkitPolling"] = descriptor
    return result


def _normalize_workflows(workflows: list[dict]) -> list[dict]:
    return [item for workflow in (workflows or []) if (item := normalize_workflow(workflow))]


def _parse_media_redirect(response: dict) -> tuple[str | None, str | None, str | None]:
    if not isinstance(response, dict):
        return None, None, "Flow media redirect returned an invalid response"
    status = response.get("status")
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    candidate = data.get("url")
    content_type = data.get("contentType")
    if (
        isinstance(status, int)
        and status < 400
        and isinstance(candidate, str)
        and candidate.startswith(_ALLOWED_MEDIA_URL_PREFIX)
    ):
        return candidate, content_type if isinstance(content_type, str) else None, None
    error = response.get("error")
    if not error and isinstance(status, int) and status >= 400:
        error = f"API_{status}"
    return None, content_type if isinstance(content_type, str) else None, str(error or "media redirect not ready")


async def _check_media_ready(
    workflows: list[dict],
    *,
    client,
    include_encoded_video: bool,
    project_id: str,
) -> dict:
    resolved_project_id = project_id or next(
        (item.get("project_id", "") for item in workflows if item.get("project_id")), ""
    )
    items = []
    for workflow in workflows:
        media_id = workflow["primary_media_id"]
        response = await client.resolve_media_url(media_id)
        url, content_type, diagnostic = _parse_media_redirect(response)
        item_project = workflow.get("project_id") or resolved_project_id
        if url:
            media = {
                "media_id": media_id,
                "url": url,
                "encoded_video_available": False,
                "resolved_via": "as29s" if USE_BATCH_RPC else "media.getMediaUrlRedirect",
            }
            if content_type:
                media["content_type"] = content_type
            if include_encoded_video:
                media["encoded_video"] = None
            item = {
                "name": workflow["name"],
                "primary_media_id": media_id,
                "done": True,
                "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                "error": None,
                "media": media,
            }
        else:
            item = {
                "name": workflow["name"],
                "primary_media_id": media_id,
                "done": False,
                "status": "PENDING",
                "error": None,
            }
            if diagnostic:
                item["probe"] = {"diagnostic": diagnostic}
                if isinstance(response, dict) and isinstance(response.get("status"), int):
                    item["probe"]["http_status"] = response["status"]
        if item_project:
            item["project_id"] = item_project
        items.append(item)

    all_done = bool(items) and all(item["done"] for item in items)
    result = {
        "done": all_done,
        "status": "COMPLETED" if all_done else "PENDING",
        "workflows": items,
    }
    if resolved_project_id:
        result["project_id"] = resolved_project_id
    return result


async def _check_project_media(
    workflows: list[dict],
    *,
    client,
    include_encoded_video: bool,
    project_id: str,
) -> dict:
    resolved_project_id = project_id or next(
        (item.get("project_id", "") for item in workflows if item.get("project_id")), ""
    )
    if not resolved_project_id:
        raise ValueError(
            "Flow project polling requires project_id. Use the project_id returned "
            "inside flowkitPolling or pass project_id explicitly."
        )
    if any(
        item.get("project_id") and item["project_id"] != resolved_project_id
        for item in workflows
    ):
        raise ValueError("All workflows in one project poll must belong to the same project_id")

    response = await client.get_project_initial_data(resolved_project_id)
    http_status = response.get("status") if isinstance(response, dict) else None
    if isinstance(http_status, int) and http_status >= 400:
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            error = error.get("message") or error.get("code")
        raise RuntimeError(error or response.get("error") or f"Flow project poll failed: API_{http_status}")

    envelope = response.get("data") if isinstance(response, dict) else None
    result = envelope.get("result") if isinstance(envelope, dict) else None
    result_data = result.get("data") if isinstance(result, dict) else None
    project_json = result_data.get("json") if isinstance(result_data, dict) else None
    contents = project_json.get("projectContents") if isinstance(project_json, dict) else None
    if not isinstance(contents, dict):
        raise RuntimeError("Flow project poll returned an unexpected response shape")

    project_workflows = contents.get("workflows")
    project_media = contents.get("media")
    project_workflows = project_workflows if isinstance(project_workflows, list) else []
    project_media = project_media if isinstance(project_media, list) else []
    known_workflow_names = {
        item.get("name") for item in project_workflows
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    media_by_id = {
        item.get("name"): item for item in project_media
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    media_by_workflow = {
        item.get("workflowId"): item for item in project_media
        if isinstance(item, dict) and isinstance(item.get("workflowId"), str)
    }

    items = []
    for workflow in workflows:
        name = workflow["name"]
        media_id = workflow["primary_media_id"]
        payload = media_by_id.get(media_id) or media_by_workflow.get(name)
        if not isinstance(payload, dict):
            items.append({
                "name": name,
                "primary_media_id": media_id,
                "project_id": resolved_project_id,
                "done": False,
                "status": "PENDING",
                "error": None,
                "workflow_present": name in known_workflow_names,
            })
            continue

        metadata = payload.get("mediaMetadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        media_status = metadata.get("mediaStatus")
        media_status = media_status if isinstance(media_status, dict) else {}
        generation_status = media_status.get("mediaGenerationStatus")
        if isinstance(generation_status, str) and (
            generation_status.endswith("FAILED") or generation_status.endswith("CANCELLED")
        ):
            items.append({
                "name": name,
                "primary_media_id": media_id,
                "project_id": resolved_project_id,
                "done": True,
                "status": "FAILED",
                "error": generation_status,
            })
            continue
        if generation_status != "MEDIA_GENERATION_STATUS_SUCCESSFUL":
            items.append({
                "name": name,
                "primary_media_id": media_id,
                "project_id": resolved_project_id,
                "done": False,
                "status": "PENDING",
                "error": None,
            })
            continue

        url_response = await client.resolve_media_url(media_id)
        url, _, url_error = _parse_media_redirect(url_response)
        media = {
            "media_id": media_id,
            "url": url,
            "encoded_video_available": False,
        }
        if include_encoded_video:
            media["encoded_video"] = None
        if url_error:
            media["url_error"] = url_error
        items.append({
            "name": name,
            "primary_media_id": media_id,
            "project_id": resolved_project_id,
            "done": True,
            "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
            "error": None,
            "media": media,
        })

    all_done = bool(items) and all(item["done"] for item in items)
    any_failed = any(item.get("status") == "FAILED" for item in items)
    return {
        "project_id": resolved_project_id,
        "done": all_done,
        "status": "FAILED" if any_failed else ("COMPLETED" if all_done else "PENDING"),
        "workflows": items,
    }


async def check_workflow_status(
    workflows: list[dict],
    *,
    mode: str,
    include_encoded_video: bool = False,
    project_id: str = "",
    client=None,
) -> dict:
    """Perform one non-blocking poll pass for a workflow-backed Flow job."""
    if mode not in _POLL_MODES:
        raise ValueError(f"Unknown Flow polling mode: {mode}")
    normalized = _normalize_workflows(workflows)
    if not normalized:
        raise ValueError(
            "Flow polling requires workflow descriptors with name and primary_media_id "
            "(or raw Flow metadata.primaryMediaId)"
        )

    client = client or get_flow_client()
    if mode in {"batch_media", "media_redirect"}:
        return await _check_media_ready(
            normalized,
            client=client,
            include_encoded_video=include_encoded_video,
            project_id=project_id,
        )
    return await _check_project_media(
        normalized,
        client=client,
        include_encoded_video=include_encoded_video,
        project_id=project_id,
    )
