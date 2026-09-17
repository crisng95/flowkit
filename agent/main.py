"""Flow Kit — FastAPI + WebSocket server entry point."""
import asyncio
import json
import logging
import re
import secrets
import signal
from contextlib import asynccontextmanager

import websockets
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.config import API_HOST, API_PORT, WS_HOST, WS_PORT, FLOWKIT_ALLOWED_HOSTS
from agent.api.debug_gate import DEBUG as _DEBUG
from agent.db.schema import init_db, close_db
from agent.api.characters import router as characters_router
from agent.api.projects import router as projects_router
from agent.api.videos import router as videos_router
from agent.api.scenes import router as scenes_router
from agent.api.requests import router as requests_router
from agent.api.flow import router as flow_router
from agent.api.reviews import router as reviews_router
from agent.api.tts import router as tts_router
from agent.api.materials import router as materials_router
from agent.api.music import router as music_router
from agent.api.models import router as models_router
from agent.api.providers import router as providers_router
from agent.api.provider_jobs import router as provider_jobs_router
from agent.api.active_project import router as active_project_router
from agent.worker.processor import get_worker_controller
from agent.services.flow_client import get_flow_client
from agent.services.event_bus import event_bus
from agent.sdk import init_sdk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# ─── WebSocket Server for Extension ─────────────────────────

async def ws_handler(websocket):
    """Handle a Chrome extension WebSocket connection."""
    client = get_flow_client()
    client.set_extension(websocket)
    logger.info("Extension connected from %s", websocket.remote_address)

    # Send callback secret so extension can authenticate HTTP callbacks
    await websocket.send(json.dumps({"type": "callback_secret", "secret": _CALLBACK_SECRET}))

    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
                await client.handle_message(data, websocket)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from extension")
            except Exception as e:
                logger.exception("Error handling extension message: %s", e)
    except websockets.ConnectionClosed:
        pass
    finally:
        client.clear_extension(websocket)
        logger.info("Extension disconnected")


async def run_ws_server():
    """Run WebSocket server for extension connections."""
    # A web page can open a WebSocket to localhost too; only the extension (or a
    # local non-browser client, which sends no Origin) may act as the extension.
    origins = [None, re.compile(r"chrome-extension://[a-p]{32}")]
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT, origins=origins):
        logger.info("WebSocket server listening on ws://%s:%d", WS_HOST, WS_PORT)
        await asyncio.Future()  # run forever


# ─── FastAPI App ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Load custom materials from DB into in-memory registry
    from agent.db.crud import list_materials as db_list_materials
    from agent.materials import register_material, _BUILTIN_IDS
    try:
        custom_materials = await db_list_materials()
        for m in custom_materials:
            if m["id"] not in _BUILTIN_IDS:
                register_material(m)
                logger.info("Loaded custom material from DB: %s", m["id"])
    except Exception as e:
        logger.warning("Failed to load custom materials: %s", e)

    ops = init_sdk(get_flow_client())
    logger.info("SDK initialized (OperationService ready)")
    logger.info("Flow Kit starting on %s:%d", API_HOST, API_PORT)

    controller = get_worker_controller()

    # SIGTERM handler for graceful shutdown (Unix only)
    try:
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, controller.request_shutdown)
    except (NotImplementedError, AttributeError):
        pass

    # Start background tasks
    ws_task = asyncio.create_task(run_ws_server())
    worker_task = asyncio.create_task(controller.start())
    logger.info("WS server + worker started")

    yield

    controller.request_shutdown()
    await controller.drain()
    ws_task.cancel()
    worker_task.cancel()
    await close_db()
    logger.info("Flow Kit stopped")


app = FastAPI(title="Flow Kit", version="1.3.1", lifespan=lifespan)

# The API has no auth: it trusts whoever can reach 127.0.0.1. A browser lets any
# web page send requests there, so cross-site requests are refused outright
# (CORS alone only hides the response; a text/plain POST still runs) and CORS
# is limited to the local dashboard and the extension.
_LOCAL_ORIGIN = re.compile(
    r"(https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?|chrome-extension://[a-p]{32})"
)


_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "[::1]", API_HOST, *FLOWKIT_ALLOWED_HOSTS}


def _host_name(host: str) -> str:
    """The Host header without its port ("[::1]:8100" -> "[::1]")."""
    if host.startswith("["):
        return host[:host.find("]") + 1]
    return host.rsplit(":", 1)[0]


@app.middleware("http")
async def reject_cross_site(request: Request, call_next):
    # DNS rebinding: a page on evil.example re-pointed at 127.0.0.1 is
    # "same-origin" to the browser, but still says evil.example in Host.
    host = _host_name(request.headers.get("host") or "")
    if host and host.lower() not in _ALLOWED_HOSTS:
        logger.warning("Refused %s %s for host %s", request.method, request.url.path, host)
        return JSONResponse({"detail": "host not allowed"}, status_code=403)
    origin = request.headers.get("origin")
    if origin is not None:
        allowed = bool(_LOCAL_ORIGIN.fullmatch(origin))
    else:
        # No Origin: a non-browser client, or a plain cross-site GET (<img>, link).
        allowed = request.headers.get("sec-fetch-site") != "cross-site"
    if not allowed:
        logger.warning("Refused cross-site %s %s (origin=%s)",
                       request.method, request.url.path, origin)
        return JSONResponse({"detail": "cross-site request refused"}, status_code=403)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=_LOCAL_ORIGIN.pattern,
    allow_methods=["*"],
    allow_headers=["*"],
)

_GENERATION_PATHS = {
    "/api/flow/generate-image",
    "/api/flow/generate-video",
    "/api/flow/generate-video-refs",
    "/api/flow/generate-video-omni",
    "/api/flow/generate-video-omni-text",
    "/api/flow/edit-image",
}


@app.middleware("http")
async def flow_caller_observability(request: Request, call_next):
    """Attribute generation submits without logging prompts, media or secrets."""
    response = await call_next(request)
    if request.method == "POST" and request.url.path in _GENERATION_PATHS:
        caller = (request.headers.get("x-flowkit-caller") or "unknown")[:80]
        logger.info(
            "Flow generation request caller=%s path=%s status=%s",
            caller,
            request.url.path,
            response.status_code,
        )
    return response


app.include_router(characters_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(videos_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")
app.include_router(requests_router, prefix="/api")
app.include_router(flow_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(tts_router, prefix="/api")
app.include_router(materials_router, prefix="/api")
app.include_router(music_router, prefix="/api")
app.include_router(provider_jobs_router, prefix="/api")
app.include_router(models_router)
app.include_router(providers_router)
app.include_router(active_project_router)


_CALLBACK_SECRET = secrets.token_urlsafe(32)


@app.post("/api/ext/callback")
async def ext_callback(request: Request):
    """HTTP callback for extension to deliver API responses.

    Replaces ws.send() for response delivery — immune to WS disconnect.
    Extension POSTs {id, status, data, error} here instead of sending via WS.
    Requires X-Callback-Secret header matching the secret sent to extension on WS connect.
    """
    supplied = request.headers.get("x-callback-secret") or ""
    if not secrets.compare_digest(supplied, _CALLBACK_SECRET):
        raise HTTPException(403, "bad callback secret")
    data = await request.json()
    client = get_flow_client()
    req_id = data.get("id")
    logger.info("ext/callback: id=%s pending=%d match=%s",
                str(req_id)[:8] if req_id else "none",
                len(client._pending),
                "yes" if req_id and req_id in client._pending else "no")
    if req_id and req_id in client._pending:
        future = client._pending[req_id]
        try:
            future.set_result(data)
        except asyncio.InvalidStateError:
            pass
        return {"ok": True}
    return {"ok": False, "reason": "no matching pending request"}


@app.post("/api/ext/reload", dependencies=_DEBUG)
async def ext_reload():
    """Trigger extension to reload its background service worker."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    for ws in list(client._extensions.keys()):
        try:
            await ws.send(json.dumps({"id": "reload-1", "method": "reload_extension"}))
        except Exception:
            pass
    return {"ok": True}


@app.post("/api/ext/reload-flow-tab", dependencies=_DEBUG)
async def ext_reload_flow_tab():
    """Trigger extension to reload open Flow tabs."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    return await client._send("reload_flow_tab", {})


@app.get("/api/ext/tabs")
async def ext_tabs():
    """List open Flow tabs from the extension."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    return await client._send("list_tabs", {})


@app.get("/api/ext/debug-tab", dependencies=_DEBUG)
async def ext_debug_tab():
    """Inspect candidate Flow tab status."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    return await client._send("debug_tab", {})


@app.get("/api/ext/test-captcha", dependencies=_DEBUG)
async def ext_test_captcha(action: str = "IMAGE_GENERATION"):
    """Test reCAPTCHA minting via extension."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    return await client._send("solve_captcha", {"captchaAction": action})


@app.get("/api/ext/test-project-media", dependencies=_DEBUG)
async def ext_test_project_media():
    """Test listing media from active Flow project."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    from agent.services import flow_batch as fb
    pid = "594758cc-11f5-4f92-8b3c-1213686591f4"
    freq = fb.project_media_request(pid)
    res = await client.batch_rpc(fb.RPC_PROJECT_MEDIA, freq)
    raw = res.get("data", "")
    with open("scratch/project_media_dump.txt", "w", encoding="utf-8") as f:
        f.write(raw)
    images = fb.read_images(raw) if raw else []
    return {
        "status": res.get("status"),
        "error": res.get("error"),
        "data_len": len(raw),
        "images": [{"media_id": img.media_id, "url": img.url} for img in images[:10]],
    }


@app.get("/api/ext/test-op", dependencies=_DEBUG)
async def ext_test_op(op: str):
    """Fetch raw operation status for an operation ID."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    from agent.services import flow_batch as fb
    res = await client.batch_rpc(fb.RPC_OPERATION, fb.operation_request(op))
    return res


@app.get("/api/ext/test-op-match", dependencies=_DEBUG)
async def ext_test_op_match(op: str):
    """Test matching an operation in project media listing."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    from agent.services import flow_batch as fb
    pid = "594758cc-11f5-4f92-8b3c-1213686591f4"
    res = await client.batch_rpc(fb.RPC_PROJECT_MEDIA, fb.project_media_request(pid), match=op)
    raw = res.get("data", "")
    found_mid = fb.find_media_id_in_text(raw, op)
    return {
        "status": res.get("status"),
        "error": res.get("error"),
        "raw_len": len(raw),
        "raw": raw,
        "found_mid": found_mid,
    }


@app.get("/api/ext/media-url", dependencies=_DEBUG)
async def ext_media_url(media_id: str):
    """Fetch signed media URLs for a media_id."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    from agent.services import flow_batch as fb
    freq = fb.media_request(media_id)
    res = await client.batch_rpc(fb.RPC_MEDIA, freq)
    raw = res.get("data", "")
    urls = None
    if raw:
        try:
            payload = fb.first_payload(raw, fb.RPC_MEDIA)
            urls = fb.read_media_urls(payload, media_id)
        except Exception as e:
            logger.warning("Failed to parse media urls for %s: %s", media_id, e)
    return {
        "status": res.get("status"),
        "error": res.get("error"),
        "raw": raw,
        "urls": {"video": urls.video, "image": urls.image} if urls else None,
    }


@app.post("/api/ext/stream-chat", dependencies=_DEBUG)
async def ext_stream_chat(request: Request):
    """Trigger image generation via FlowCreationAgentService/StreamChat."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    data = await request.json()
    prompt = data.get("prompt")
    if not prompt:
        from fastapi import HTTPException
        raise HTTPException(400, "prompt is required")
    project_id = data.get("project_id")
    res = await client.stream_chat(prompt, project_id=project_id)
    return res


@app.post("/api/ext/submit-ui-prompt", dependencies=_DEBUG)
async def ext_submit_ui_prompt(request: Request):
    """Type prompt into Flow web UI ProseMirror editor and click create button."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    data = await request.json()
    prompt = data.get("prompt")
    if not prompt:
        from fastapi import HTTPException
        raise HTTPException(400, "prompt is required")
    return await client._send("submit_ui_prompt", {"prompt": prompt})


@app.post("/api/ext/eval-tab", dependencies=_DEBUG)
async def ext_eval_tab(request: Request):
    """Execute javascript in the active Flow tab's MAIN world and return result."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    data = await request.json()
    return await client._send("eval_tab", {"code": data.get("code", "")})


@app.get("/api/ext/find-actions", dependencies=_DEBUG)
async def ext_find_actions():
    """Find reCAPTCHA action names in Flow web scripts."""
    client = get_flow_client()
    if not client.connected:
        from fastapi import HTTPException
        raise HTTPException(503, "Extension not connected")
    return await client._send("find_actions", {})


@app.get("/health")
async def health():
    client = get_flow_client()
    return {
        "status": "ok",
        "version": app.version,
        "extension_connected": client.connected,
        "ws": client.ws_stats,
    }


# ─── Dashboard WebSocket ──────────────────────────────────────

@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    """WebSocket endpoint for dashboard clients (Chrome extension side panel)."""
    # Reject cross-origin connections (only allow localhost)
    origin = websocket.headers.get("origin")
    if origin and not _LOCAL_ORIGIN.fullmatch(origin):
        await websocket.close(code=4003, reason="Origin not allowed")
        return
    await websocket.accept()

    q = event_bus.subscribe()
    try:
        # Send initial snapshot
        client = get_flow_client()
        controller = get_worker_controller()
        from agent.db import crud
        pending_requests = await crud.list_requests(status="PENDING")
        processing_requests = await crud.list_requests(status="PROCESSING")
        snapshot = {
            "type": "snapshot",
            "health": {
                "status": "ok",
                "extension_connected": client.connected,
            },
            "requests": pending_requests + processing_requests,
            "worker": {
                "active": controller.active_count,
                "slots": max(0, 5 - controller.active_count),
            },
        }
        await websocket.send_text(json.dumps(snapshot))

        # Forward events from event_bus to this client
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=30.0)
                await websocket.send_text(msg)
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("Dashboard WS client disconnected: %s", e)
    finally:
        event_bus.unsubscribe(q)


@app.post("/api/test-direct", dependencies=_DEBUG)
async def test_direct(request: Request):
    from agent.services import flow_batch as fb
    client = get_flow_client()
    data = await request.json()
    pid = data.get("project_id", "594758cc-11f5-4f92-8b3c-1213686591f4")
    prompt = data.get("prompt")
    ref_ids = data.get("ref_media_ids")
    freq = fb.image_request(
        prompt, pid, count=1,
        aspect="IMAGE_ASPECT_RATIO_LANDSCAPE",
        ref_media_ids=ref_ids,
    )
    try:
        res = await client._batch_payload(fb.RPC_GEN_IMAGE, freq, fb.CAPTCHA_IMAGE)
        imgs = fb.read_images(res)
        return {"ok": True, "count": len(imgs), "images": [img.__dict__ for img in imgs]}
    except Exception as e:
        logger.exception("test_direct failed: %s", e)
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    import os
    import uvicorn
    reload_enabled = os.environ.get("GLA_RELOAD", "0") == "1"
    uvicorn.run(
        "agent.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=reload_enabled,
        reload_excludes=["*.db", "*.db-wal", "*.db-shm", "output/*"],
    )
