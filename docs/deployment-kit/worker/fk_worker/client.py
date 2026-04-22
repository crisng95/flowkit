"""HTTP client for the local FlowKit runtime."""

from __future__ import annotations

import time
from typing import Iterable

import httpx

from .config import settings


class FlowKitClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.local_api_base
        self._client = httpx.Client(base_url=self.base_url, timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def _request_json(self, method: str, path: str, **kwargs) -> dict | list:
        response = self._client.request(method, path, **kwargs)
        try:
            payload = response.json()
        except ValueError:
            payload = {"detail": response.text}
        if response.status_code >= 400:
            detail = payload.get("detail") if isinstance(payload, dict) else payload
            raise RuntimeError(f"{method} {path} failed: {detail}")
        return payload

    def get_health(self) -> dict:
        return self._request_json("GET", "/health")

    def get_flow_status(self) -> dict:
        return self._request_json("GET", "/api/flow/status")

    def get_flow_credits(self) -> dict:
        return self._request_json("GET", "/api/flow/credits")

    def create_project(self, payload: dict) -> dict:
        return self._request_json("POST", "/api/projects", json=payload)

    def create_character(self, payload: dict) -> dict:
        return self._request_json("POST", "/api/characters", json=payload)

    def link_project_character(self, project_id: str, character_id: str) -> dict:
        return self._request_json("POST", f"/api/projects/{project_id}/characters/{character_id}")

    def create_video(self, payload: dict) -> dict:
        return self._request_json("POST", "/api/videos", json=payload)

    def create_scene(self, payload: dict) -> dict:
        return self._request_json("POST", "/api/scenes", json=payload)

    def get_project_output_dir(self, project_id: str) -> dict:
        return self._request_json("GET", f"/api/projects/{project_id}/output-dir")

    def get_video(self, video_id: str) -> dict:
        return self._request_json("GET", f"/api/videos/{video_id}")

    def list_project_characters(self, project_id: str) -> list[dict]:
        return self._request_json("GET", f"/api/projects/{project_id}/characters")

    def list_video_scenes(self, video_id: str) -> list[dict]:
        return self._request_json("GET", "/api/scenes", params={"video_id": video_id})

    def submit_requests_batch(self, payload: dict) -> list[dict]:
        return self._request_json("POST", "/api/requests/batch", json=payload)

    def get_request(self, request_id: str) -> dict:
        return self._request_json("GET", f"/api/requests/{request_id}")

    def wait_for_requests(self, request_ids: Iterable[str], timeout_seconds: int = 900, poll_interval: int = 6) -> list[dict]:
        pending = set(request_ids)
        done: dict[str, dict] = {}
        deadline = time.time() + timeout_seconds
        while pending and time.time() < deadline:
            time.sleep(poll_interval)
            for request_id in list(pending):
                record = self.get_request(request_id)
                if record["status"] in {"COMPLETED", "FAILED"}:
                    done[request_id] = record
                    pending.remove(request_id)
        if pending:
            raise TimeoutError(f"Timed out waiting for requests: {sorted(pending)}")
        return [done[request_id] for request_id in request_ids]
