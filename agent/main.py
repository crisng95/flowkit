"""Google Flow Agent — FastAPI + WebSocket server entry point."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager

import websockets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.config import API_HOST, API_PORT, WS_HOST, WS_PORT
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
from agent.worker.processor import process_pending_requests
from agent.services.flow_client import get_flow_client
from agent.sdk import init_sdk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# ─── WebSocket Server for Extension ─────────────────────────

async def ws_handler(websocket):
    """Handle a Chrome extension WebSocket connection."""
    client = get_flow_client()
    client.set_extension(websocket)
    logger.info("Extension connected from %s", websocket.remote_address)

    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
                await client.handle_message(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from extension")
            except Exception as e:
                logger.exception("Error handling extension message: %s", e)
    except websockets.ConnectionClosed:
        pass
    finally:
        client.clear_extension()
        logger.info("Extension disconnected")


async def run_ws_server():
    """Run WebSocket server for extension connections."""
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
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
    logger.info("Google Flow Agent starting on %s:%d", API_HOST, API_PORT)

    # Start background tasks
    ws_task = asyncio.create_task(run_ws_server())
    worker_task = asyncio.create_task(process_pending_requests())
    logger.info("WS server + worker started")

    yield

    ws_task.cancel()
    worker_task.cancel()
    await close_db()
    logger.info("Google Flow Agent stopped")


app = FastAPI(title="Google Flow Agent", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(characters_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(videos_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")
app.include_router(requests_router, prefix="/api")
app.include_router(flow_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(tts_router, prefix="/api")
app.include_router(materials_router, prefix="/api")


@app.get("/health")
async def health():
    client = get_flow_client()
    return {
        "status": "ok",
        "version": "0.2.0",
        "extension_connected": client.connected,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent.main:app", host=API_HOST, port=API_PORT, reload=True)
