import base64
import builtins
import io

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from starlette.datastructures import Headers, UploadFile

from agent.api import flow as flow_api


PROJECT = "11111111-2222-3333-4444-555555555555"
SESSION_PROJECT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
MEDIA = "99999999-8888-7777-6666-555555555555"
IMAGE = b"\x89PNG\r\n\x1a\nflowkit-test-image"


class FakeFlowClient:
    connected = True

    def __init__(self):
        self.uploads = []

    async def upload_image(self, image_base64, mime_type="image/jpeg", project_id="", file_name="image.jpg"):
        self.uploads.append(
            {
                "bytes": base64.b64decode(image_base64),
                "mime_type": mime_type,
                "project_id": project_id,
                "file_name": file_name,
            }
        )
        return {
            "status": 200,
            "data": {"media": {"name": MEDIA}},
            "_mediaId": MEDIA,
        }


@pytest.mark.asyncio
async def test_base64_upload_is_direct_bytes_path(monkeypatch):
    client = FakeFlowClient()
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: client)

    result = await flow_api.upload_image(
        flow_api.UploadImageRequest(
            image_base64=base64.b64encode(IMAGE).decode(),
            mime_type="image/png",
            file_name="source.png",
            project_id=PROJECT,
        )
    )

    assert result["media_id"] == MEDIA
    assert result["project_id"] == PROJECT
    assert client.uploads == [
        {
            "bytes": IMAGE,
            "mime_type": "image/png",
            "project_id": PROJECT,
            "file_name": "source.png",
        }
    ]


@pytest.mark.asyncio
async def test_unreadable_server_local_path_returns_403(monkeypatch):
    client = FakeFlowClient()
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: client)

    def deny_open(*args, **kwargs):
        raise PermissionError("permission denied")

    monkeypatch.setattr(builtins, "open", deny_open)

    with pytest.raises(HTTPException) as excinfo:
        await flow_api.upload_image(
            flow_api.UploadImageRequest(file_path="/root/private/source.jpg", project_id=PROJECT)
        )

    assert excinfo.value.status_code == 403
    assert "not readable by FlowKit service" in excinfo.value.detail
    assert client.uploads == []


@pytest.mark.asyncio
async def test_private_tmp_like_invisible_path_returns_descriptive_404(monkeypatch):
    client = FakeFlowClient()
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: client)

    def missing_open(*args, **kwargs):
        raise FileNotFoundError("not in service namespace")

    monkeypatch.setattr(builtins, "open", missing_open)

    with pytest.raises(HTTPException) as excinfo:
        await flow_api.upload_image(
            flow_api.UploadImageRequest(file_path="/tmp/caller-only/source.jpg", project_id=PROJECT)
        )

    assert excinfo.value.status_code == 404
    assert "not visible to the FlowKit service" in excinfo.value.detail
    assert "PrivateTmp" in excinfo.value.detail
    assert "/api/flow/upload-image-file" in excinfo.value.detail
    assert client.uploads == []


@pytest.mark.asyncio
async def test_session_project_auto_creation_then_base64_upload(monkeypatch):
    client = FakeFlowClient()
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: client)
    calls = []

    async def fake_ensure_session_project(received_client):
        calls.append(received_client)
        return {"project_id": SESSION_PROJECT}

    monkeypatch.setattr(flow_api, "ensure_session_project", fake_ensure_session_project)

    result = await flow_api.upload_image(
        flow_api.UploadImageRequest(
            image_base64=base64.b64encode(IMAGE).decode(),
            file_name="auto.png",
        )
    )

    assert calls == [client]
    assert result["project_id"] == SESSION_PROJECT
    assert client.uploads[0]["project_id"] == SESSION_PROJECT


@pytest.mark.asyncio
async def test_multipart_upload_uses_request_bytes_and_session_project(monkeypatch):
    client = FakeFlowClient()
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: client)

    async def fake_ensure_session_project(received_client):
        assert received_client is client
        return {"project_id": SESSION_PROJECT}

    monkeypatch.setattr(flow_api, "ensure_session_project", fake_ensure_session_project)
    upload = UploadFile(
        file=io.BytesIO(IMAGE),
        filename="caller.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )

    result = await flow_api.upload_image_file(
        file=upload,
        project_id="",
        file_name=None,
        mime_type=None,
    )

    assert result["project_id"] == SESSION_PROJECT
    assert client.uploads == [
        {
            "bytes": IMAGE,
            "mime_type": "image/jpeg",
            "project_id": SESSION_PROJECT,
            "file_name": "caller.jpg",
        }
    ]


def test_openapi_distinguishes_json_base64_and_multipart_uploads():
    app = FastAPI()
    app.include_router(flow_api.router, prefix="/api")
    schema = app.openapi()

    json_upload = schema["paths"]["/api/flow/upload-image"]["post"]
    multipart_upload = schema["paths"]["/api/flow/upload-image-file"]["post"]
    request_schema = schema["components"]["schemas"]["UploadImageRequest"]["properties"]

    assert "application/json" in json_upload["requestBody"]["content"]
    assert "multipart/form-data" in multipart_upload["requestBody"]["content"]
    assert "Recommended for external/API callers" in request_schema["image_base64"]["description"]
    assert "Server-local convenience mode only" in request_schema["file_path"]["description"]


@pytest.mark.asyncio
async def test_multipart_route_parses_real_form_data(monkeypatch):
    client = FakeFlowClient()
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: client)

    async def fake_ensure_session_project(received_client):
        assert received_client is client
        return {"project_id": SESSION_PROJECT}

    monkeypatch.setattr(flow_api, "ensure_session_project", fake_ensure_session_project)
    app = FastAPI()
    app.include_router(flow_api.router, prefix="/api")
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
        response = await http.post(
            "/api/flow/upload-image-file",
            files={"file": ("browser.png", IMAGE, "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["project_id"] == SESSION_PROJECT
    assert client.uploads[0]["bytes"] == IMAGE
    assert client.uploads[0]["file_name"] == "browser.png"
    assert client.uploads[0]["mime_type"] == "image/png"
