"""The local API has no auth, so it must refuse what a web page can send it."""

import pytest
from fastapi.testclient import TestClient

import agent.main as main
from agent import config

EXT_ORIGIN = "chrome-extension://" + "a" * 32


@pytest.fixture
def client():
    # No context manager: the lifespan (DB, WS server, worker) is not started.
    return TestClient(main.app, base_url="http://127.0.0.1:8100")


@pytest.mark.parametrize("headers", [
    {"origin": "https://evil.example"},
    {"origin": "null"},
    {"origin": "http://localhost.evil.example"},
    {"sec-fetch-site": "cross-site"},
])
def test_cross_site_requests_are_refused(client, headers):
    resp = client.post("/api/ext/eval-tab", headers=headers, content='{"code": "1"}')
    assert resp.status_code == 403
    assert client.get("/health", headers=headers).status_code == 403


@pytest.mark.parametrize("headers", [
    {},
    {"origin": "http://localhost:5173"},
    {"origin": "http://127.0.0.1:8100", "sec-fetch-site": "same-origin"},
    {"origin": EXT_ORIGIN},
])
def test_local_callers_pass(client, headers):
    assert client.get("/health", headers=headers).status_code == 200


def test_cors_is_limited_to_local_origins(client):
    def preflight(origin):
        return client.options("/api/projects", headers={
            "origin": origin, "access-control-request-method": "POST"})
    assert preflight("http://localhost:5173").headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in preflight("https://evil.example").headers


def test_debug_routes_are_off_by_default(client):
    assert client.post("/api/ext/eval-tab", json={"code": "1"}).status_code == 404
    assert client.get("/api/ext/test-captcha").status_code == 404
    assert client.post("/api/test-direct", json={"prompt": "x"}).status_code == 404
    for path in ("/api/ext/debug-tab", "/api/flow/debug-cache", "/api/flow/debug-project-media",
                 "/api/flow/debug-listing/op"):
        assert client.get(path).status_code == 404, path
    assert client.post("/api/ext/reload").status_code == 404


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8100", "localhost.evil.example"])
def test_rebound_hosts_are_refused(client, host):
    assert client.get("/health", headers={"host": host}).status_code == 403


@pytest.mark.parametrize("host", ["localhost:5173", "127.0.0.1:8100", "[::1]:8100"])
def test_local_hosts_pass(client, host):
    assert client.get("/health", headers={"host": host}).status_code == 200


def test_dashboard_ws_refuses_lookalike_origin(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/dashboard",
                                      headers={"origin": "http://localhost.evil.example"}) as ws:
            ws.receive_text()


def test_debug_routes_can_be_turned_on(client, monkeypatch):
    monkeypatch.setattr(config, "FLOWKIT_DEBUG_ENDPOINTS", True)
    # Past the gate; fails only because no extension is connected.
    assert client.post("/api/ext/eval-tab", json={"code": "1"}).status_code == 503


def test_netlog_recorder_is_gone(client):
    assert client.post("/api/ext/netlog", json={}).status_code in (404, 405)
    assert client.get("/api/ext/netlog").status_code in (404, 405)


def test_callback_requires_the_secret(client):
    assert client.post("/api/ext/callback", json={"id": "x"}).status_code == 403
    bad = {"x-callback-secret": "nope"}
    assert client.post("/api/ext/callback", json={"id": "x"}, headers=bad).status_code == 403
    good = {"x-callback-secret": main._CALLBACK_SECRET}
    resp = client.post("/api/ext/callback", json={"id": "x"}, headers=good)
    assert resp.status_code == 200 and resp.json()["ok"] is False  # nothing pending
