"""Async CRUD operations with column whitelisting."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from agent.db.schema import get_db

# Column whitelists per table — prevents SQL injection via kwargs keys
_COLUMNS = {
    "character": {"name", "entity_type", "description", "image_prompt", "voice_description", "reference_image_url", "media_id", "updated_at"},
    "project": {"name", "description", "story", "thumbnail_url", "language", "status", "user_paygate_tier", "updated_at"},
    "video": {"title", "description", "display_order", "status", "vertical_url", "horizontal_url",
              "thumbnail_url", "duration", "resolution", "youtube_id", "privacy", "tags", "updated_at"},
    "scene": {"prompt", "image_prompt", "video_prompt", "character_names", "chain_type",
              "vertical_image_url", "vertical_image_media_id", "vertical_image_status",
              "vertical_video_url", "vertical_video_media_id", "vertical_video_status",
              "vertical_upscale_url", "vertical_upscale_media_id", "vertical_upscale_status",
              "horizontal_image_url", "horizontal_image_media_id", "horizontal_image_status",
              "horizontal_video_url", "horizontal_video_media_id", "horizontal_video_status",
              "horizontal_upscale_url", "horizontal_upscale_media_id", "horizontal_upscale_status",
              "vertical_end_scene_media_id", "horizontal_end_scene_media_id",
              "trim_start", "trim_end", "duration", "display_order", "updated_at"},
    "request": {"status", "request_id", "media_id", "output_url", "error_message", "retry_count", "updated_at"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _uuid() -> str:
    return str(uuid.uuid4())


def _safe_kwargs(table: str, kwargs: dict) -> dict:
    """Filter kwargs to only allowed columns."""
    allowed = _COLUMNS.get(table, set())
    return {k: v for k, v in kwargs.items() if k in allowed}


async def _update(table: str, pk: str, pk_val: str, **kwargs) -> Optional[dict]:
    kwargs = _safe_kwargs(table, kwargs)
    if not kwargs:
        return await _get(table, pk, pk_val)
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [pk_val]
    db = await get_db()
    try:
        await db.execute(f"UPDATE {table} SET {sets} WHERE {pk}=?", vals)
        await db.commit()
        return await _get_with_db(db, table, pk, pk_val)
    finally:
        await db.close()


async def _get(table: str, pk: str, pk_val: str) -> Optional[dict]:
    db = await get_db()
    try:
        return await _get_with_db(db, table, pk, pk_val)
    finally:
        await db.close()


async def _get_with_db(db, table: str, pk: str, pk_val: str) -> Optional[dict]:
    cur = await db.execute(f"SELECT * FROM {table} WHERE {pk}=?", (pk_val,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def _delete(table: str, pk: str, pk_val: str) -> bool:
    db = await get_db()
    try:
        cur = await db.execute(f"DELETE FROM {table} WHERE {pk}=?", (pk_val,))
        await db.commit()
        return cur.rowcount > 0
    finally:
        await db.close()


# ─── Character ──────────────────────────────────────────────

async def create_character(name: str, entity_type: str = "character", description: str = None, image_prompt: str = None, voice_description: str = None, reference_image_url: str = None, media_id: str = None) -> dict:
    db = await get_db()
    try:
        cid, now = _uuid(), _now()
        await db.execute(
            "INSERT INTO character (id,name,entity_type,description,image_prompt,voice_description,reference_image_url,media_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, name, entity_type, description, image_prompt, voice_description, reference_image_url, media_id, now, now))
        await db.commit()
        return await _get_with_db(db, "character", "id", cid)
    finally:
        await db.close()

async def get_character(cid: str): return await _get("character", "id", cid)
async def update_character(cid: str, **kw): return await _update("character", "id", cid, **kw)
async def delete_character(cid: str): return await _delete("character", "id", cid)

async def list_characters() -> list[dict]:
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM character ORDER BY created_at DESC")
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


# ─── Project ────────────────────────────────────────────────

async def create_project(name: str, description: str = None, story: str = None, language: str = "en", user_paygate_tier: str = "PAYGATE_TIER_TWO", id: str = None) -> dict:
    db = await get_db()
    try:
        pid, now = id or _uuid(), _now()
        await db.execute(
            "INSERT INTO project (id,name,description,story,language,user_paygate_tier,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (pid, name, description, story, language, user_paygate_tier, now, now))
        await db.commit()
        return await _get_with_db(db, "project", "id", pid)
    finally:
        await db.close()

async def get_project(pid: str): return await _get("project", "id", pid)
async def update_project(pid: str, **kw): return await _update("project", "id", pid, **kw)
async def delete_project(pid: str): return await _delete("project", "id", pid)

async def list_projects(status: str = None) -> list[dict]:
    db = await get_db()
    try:
        if status:
            cur = await db.execute("SELECT * FROM project WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            cur = await db.execute("SELECT * FROM project ORDER BY created_at DESC")
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def link_character_to_project(project_id: str, character_id: str) -> bool:
    db = await get_db()
    try:
        await db.execute("INSERT OR IGNORE INTO project_character VALUES (?,?)", (project_id, character_id))
        await db.commit()
        return True
    except Exception:
        return False
    finally:
        await db.close()

async def unlink_character_from_project(project_id: str, character_id: str) -> bool:
    db = await get_db()
    try:
        cur = await db.execute("DELETE FROM project_character WHERE project_id=? AND character_id=?", (project_id, character_id))
        await db.commit()
        return cur.rowcount > 0
    finally:
        await db.close()

async def get_project_characters(project_id: str) -> list[dict]:
    db = await get_db()
    try:
        cur = await db.execute(
            "SELECT c.* FROM character c JOIN project_character pc ON c.id=pc.character_id WHERE pc.project_id=?",
            (project_id,))
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


# ─── Video ──────────────────────────────────────────────────

async def create_video(project_id: str, title: str, description: str = None, display_order: int = 0) -> dict:
    db = await get_db()
    try:
        vid, now = _uuid(), _now()
        await db.execute(
            "INSERT INTO video (id,project_id,title,description,display_order,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (vid, project_id, title, description, display_order, now, now))
        await db.commit()
        return await _get_with_db(db, "video", "id", vid)
    finally:
        await db.close()

async def get_video(vid: str): return await _get("video", "id", vid)
async def update_video(vid: str, **kw): return await _update("video", "id", vid, **kw)
async def delete_video(vid: str): return await _delete("video", "id", vid)

async def list_videos(project_id: str) -> list[dict]:
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM video WHERE project_id=? ORDER BY display_order", (project_id,))
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


# ─── Scene ──────────────────────────────────────────────────

async def create_scene(video_id: str, display_order: int, prompt: str,
                       image_prompt: str = None, video_prompt: str = None,
                       character_names: list[str] = None,
                       parent_scene_id: str = None, chain_type: str = "ROOT") -> dict:
    db = await get_db()
    try:
        sid, now = _uuid(), _now()
        chars_json = json.dumps(character_names) if character_names else None
        await db.execute(
            """INSERT INTO scene (id,video_id,display_order,prompt,image_prompt,video_prompt,character_names,
               parent_scene_id,chain_type,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, video_id, display_order, prompt, image_prompt, video_prompt, chars_json,
             parent_scene_id, chain_type, now, now))
        await db.commit()
        return await _get_with_db(db, "scene", "id", sid)
    finally:
        await db.close()

async def get_scene(sid: str): return await _get("scene", "id", sid)
async def update_scene(sid: str, **kw): return await _update("scene", "id", sid, **kw)
async def delete_scene(sid: str): return await _delete("scene", "id", sid)

async def list_scenes(video_id: str) -> list[dict]:
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM scene WHERE video_id=? ORDER BY display_order", (video_id,))
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


# ─── Request ────────────────────────────────────────────────

async def create_request(req_type: str, orientation: str = None,
                         scene_id: str = None, character_id: str = None,
                         project_id: str = None, video_id: str = None) -> dict:
    db = await get_db()
    try:
        rid, now = _uuid(), _now()
        await db.execute(
            """INSERT INTO request (id,project_id,video_id,scene_id,character_id,type,orientation,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (rid, project_id, video_id, scene_id, character_id, req_type, orientation, now, now))
        await db.commit()
        return await _get_with_db(db, "request", "id", rid)
    finally:
        await db.close()

async def get_request(rid: str): return await _get("request", "id", rid)
async def update_request(rid: str, **kw): return await _update("request", "id", rid, **kw)

async def list_requests(scene_id: str = None, status: str = None) -> list[dict]:
    db = await get_db()
    try:
        q, params = "SELECT * FROM request WHERE 1=1", []
        if scene_id:
            q += " AND scene_id=?"; params.append(scene_id)
        if status:
            q += " AND status=?"; params.append(status)
        q += " ORDER BY created_at DESC"
        cur = await db.execute(q, params)
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def list_pending_requests() -> list[dict]:
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM request WHERE status='PENDING' ORDER BY created_at")
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()
