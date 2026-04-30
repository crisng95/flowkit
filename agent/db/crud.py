"""Async CRUD operations with column whitelisting."""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from agent.db.schema import get_db, _db_lock

logger = logging.getLogger(__name__)

_VALID_TABLES = frozenset({"character", "project", "video", "scene", "request", "material"})


def _validate_table(table: str) -> None:
    if table not in _VALID_TABLES:
        raise ValueError(f"Invalid table name: {table!r}")

# Column whitelists per table — prevents SQL injection via kwargs keys
_COLUMNS = {
    "character": {"name", "slug", "entity_type", "description", "image_prompt", "voice_description", "reference_image_url", "media_id", "updated_at"},
    "project": {"name", "description", "story", "thumbnail_url", "language", "status", "user_paygate_tier", "narrator_voice", "narrator_ref_audio", "material", "orientation", "allow_music", "allow_voice", "updated_at"},
    "video": {"title", "description", "display_order", "status", "orientation", "vertical_url", "horizontal_url",
              "thumbnail_url", "duration", "resolution", "youtube_id", "privacy", "tags", "updated_at"},
    "scene": {"prompt", "image_prompt", "video_prompt", "character_names", "parent_scene_id", "chain_type",
              "vertical_image_url", "vertical_image_media_id", "vertical_image_status",
              "vertical_video_url", "vertical_video_media_id", "vertical_video_status",
              "vertical_upscale_url", "vertical_upscale_media_id", "vertical_upscale_status",
              "horizontal_image_url", "horizontal_image_media_id", "horizontal_image_status",
              "horizontal_video_url", "horizontal_video_media_id", "horizontal_video_status",
              "horizontal_upscale_url", "horizontal_upscale_media_id", "horizontal_upscale_status",
              "vertical_end_scene_media_id", "horizontal_end_scene_media_id",
              "trim_start", "trim_end", "duration", "display_order", "source", "transition_prompt", "narrator_text", "updated_at"},
    "request": {"status", "request_id", "media_id", "output_url", "error_message", "retry_count", "next_retry_at", "source_media_id", "updated_at"},
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
    _validate_table(table)
    kwargs = _safe_kwargs(table, kwargs)
    if not kwargs:
        return await _get(table, pk, pk_val)
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [pk_val]
    db = await get_db()
    async with _db_lock:
        await db.execute(f"UPDATE {table} SET {sets} WHERE {pk}=?", vals)
        await db.commit()
    return await _get_with_db(db, table, pk, pk_val)


async def _get(table: str, pk: str, pk_val: str) -> Optional[dict]:
    _validate_table(table)
    db = await get_db()
    return await _get_with_db(db, table, pk, pk_val)


async def _get_with_db(db, table: str, pk: str, pk_val: str) -> Optional[dict]:
    _validate_table(table)
    cur = await db.execute(f"SELECT * FROM {table} WHERE {pk}=?", (pk_val,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def _delete(table: str, pk: str, pk_val: str) -> bool:
    _validate_table(table)
    db = await get_db()
    async with _db_lock:
        cur = await db.execute(f"DELETE FROM {table} WHERE {pk}=?", (pk_val,))
        await db.commit()
    return cur.rowcount > 0


# ─── Character ──────────────────────────────────────────────

async def create_character(name: str, entity_type: str = "character", description: str = None, image_prompt: str = None, voice_description: str = None, reference_image_url: str = None, media_id: str = None, slug: str = None) -> dict:
    from agent.utils.slugify import slugify
    db = await get_db()
    cid, now = _uuid(), _now()
    _slug = slug or slugify(name)
    async with _db_lock:
        await db.execute(
            "INSERT INTO character (id,name,slug,entity_type,description,image_prompt,voice_description,reference_image_url,media_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cid, name, _slug, entity_type, description, image_prompt, voice_description, reference_image_url, media_id, now, now))
        await db.commit()
    return await _get_with_db(db, "character", "id", cid)

async def get_character(cid: str): return await _get("character", "id", cid)
async def update_character(cid: str, **kw): return await _update("character", "id", cid, **kw)
async def delete_character(cid: str): return await _delete("character", "id", cid)

async def list_characters() -> list[dict]:
    db = await get_db()
    cur = await db.execute("SELECT * FROM character ORDER BY created_at DESC")
    return [dict(r) for r in await cur.fetchall()]


# ─── Project ────────────────────────────────────────────────

async def create_project(name: str, description: str = None, story: str = None, language: str = "en", user_paygate_tier: str = "PAYGATE_TIER_ONE", id: str = None, material: str = None, orientation: str = "VERTICAL", allow_music: bool = False, allow_voice: bool = False) -> dict:
    db = await get_db()
    pid, now = id or _uuid(), _now()
    async with _db_lock:
        await db.execute(
            "INSERT INTO project (id,name,description,story,language,user_paygate_tier,material,orientation,allow_music,allow_voice,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, name, description, story, language, user_paygate_tier, material, orientation, int(allow_music), int(allow_voice), now, now))
        await db.commit()
    return await _get_with_db(db, "project", "id", pid)

async def get_project(pid: str): return await _get("project", "id", pid)
async def update_project(pid: str, **kw): return await _update("project", "id", pid, **kw)
async def delete_project(pid: str): return await _delete("project", "id", pid)

async def list_projects(status: str = None) -> list[dict]:
    db = await get_db()
    if status:
        cur = await db.execute("SELECT * FROM project WHERE status=? ORDER BY created_at DESC", (status,))
    else:
        cur = await db.execute("SELECT * FROM project ORDER BY created_at DESC")
    return [dict(r) for r in await cur.fetchall()]

async def link_character_to_project(project_id: str, character_id: str) -> bool:
    db = await get_db()
    try:
        async with _db_lock:
            await db.execute("INSERT OR IGNORE INTO project_character VALUES (?,?)", (project_id, character_id))
            await db.commit()
        return True
    except Exception as e:
        logger.warning("link_character_to_project failed: %s", e)
        return False

async def unlink_character_from_project(project_id: str, character_id: str) -> bool:
    db = await get_db()
    async with _db_lock:
        cur = await db.execute("DELETE FROM project_character WHERE project_id=? AND character_id=?", (project_id, character_id))
        await db.commit()
    return cur.rowcount > 0

async def get_project_characters(project_id: str) -> list[dict]:
    db = await get_db()
    cur = await db.execute(
        "SELECT c.* FROM character c JOIN project_character pc ON c.id=pc.character_id WHERE pc.project_id=?",
        (project_id,))
    return [dict(r) for r in await cur.fetchall()]


# ─── Video ──────────────────────────────────────────────────

async def create_video(project_id: str, title: str, description: str = None, display_order: int = 0, orientation: str = None) -> dict:
    db = await get_db()
    vid, now = _uuid(), _now()
    async with _db_lock:
        await db.execute(
            "INSERT INTO video (id,project_id,title,description,display_order,orientation,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (vid, project_id, title, description, display_order, orientation, now, now))
        await db.commit()
    return await _get_with_db(db, "video", "id", vid)

async def get_video(vid: str): return await _get("video", "id", vid)
async def update_video(vid: str, **kw): return await _update("video", "id", vid, **kw)
async def delete_video(vid: str): return await _delete("video", "id", vid)

async def list_videos(project_id: str) -> list[dict]:
    db = await get_db()
    cur = await db.execute("SELECT * FROM video WHERE project_id=? ORDER BY display_order", (project_id,))
    return [dict(r) for r in await cur.fetchall()]


# ─── Scene ──────────────────────────────────────────────────

async def create_scene(video_id: str, display_order: int, prompt: str,
                       image_prompt: str = None, video_prompt: str = None,
                       transition_prompt: str = None,
                       character_names: list[str] = None,
                       parent_scene_id: str = None, chain_type: str = "ROOT",
                       source: str = "root",
                       narrator_text: str = None) -> dict:
    db = await get_db()
    sid, now = _uuid(), _now()
    chars_json = json.dumps(character_names) if character_names else None
    async with _db_lock:
        await db.execute(
            """INSERT INTO scene (id,video_id,display_order,prompt,image_prompt,video_prompt,transition_prompt,character_names,
               parent_scene_id,chain_type,source,narrator_text,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, video_id, display_order, prompt, image_prompt, video_prompt, transition_prompt, chars_json,
             parent_scene_id, chain_type, source, narrator_text, now, now))
        await db.commit()
    return await _get_with_db(db, "scene", "id", sid)


async def get_scene(sid: str): return await _get("scene", "id", sid)
async def update_scene(sid: str, **kw): return await _update("scene", "id", sid, **kw)
async def delete_scene(sid: str): return await _delete("scene", "id", sid)

async def list_scenes(video_id: str) -> list[dict]:
    db = await get_db()
    cur = await db.execute("SELECT * FROM scene WHERE video_id=? ORDER BY display_order", (video_id,))
    return [dict(r) for r in await cur.fetchall()]


async def list_scenes_by_media_id(media_id: str) -> list[dict]:
    """Find scenes where any media_id field matches the given UUID."""
    db = await get_db()
    cur = await db.execute(
        """SELECT * FROM scene WHERE
           vertical_image_media_id=? OR horizontal_image_media_id=?
           OR vertical_video_media_id=? OR horizontal_video_media_id=?
           OR vertical_upscale_media_id=? OR horizontal_upscale_media_id=?""",
        (media_id, media_id, media_id, media_id, media_id, media_id))
    return [dict(r) for r in await cur.fetchall()]


async def list_characters_by_media_id(media_id: str) -> list[dict]:
    """Find characters where media_id matches."""
    db = await get_db()
    cur = await db.execute("SELECT * FROM character WHERE media_id=?", (media_id,))
    return [dict(r) for r in await cur.fetchall()]


async def clear_redirect_media_urls() -> dict:
    """Clear unstable TRPC redirect URLs so UI will fetch fresh signed URLs.

    Redirect URLs (media.getMediaUrlRedirect) can break after restart/session change.
    We keep media_id and reset URL slots to NULL, forcing refresh on demand.
    """
    db = await get_db()
    now = _now()
    scene_fields = (
        "vertical_image_url",
        "horizontal_image_url",
        "vertical_video_url",
        "horizontal_video_url",
        "vertical_upscale_url",
        "horizontal_upscale_url",
    )
    scene_slots_cleared = 0
    characters_cleared = 0
    async with _db_lock:
        for field in scene_fields:
            cur = await db.execute(
                f"""
                UPDATE scene
                   SET {field}=NULL, updated_at=?
                 WHERE {field} LIKE '%media.getMediaUrlRedirect%'
                """,
                (now,),
            )
            scene_slots_cleared += int(cur.rowcount or 0)

        cur = await db.execute(
            """
            UPDATE character
               SET reference_image_url=NULL, updated_at=?
             WHERE reference_image_url LIKE '%media.getMediaUrlRedirect%'
            """,
            (now,),
        )
        characters_cleared = int(cur.rowcount or 0)
        await db.commit()

    return {
        "scene_slots_cleared": scene_slots_cleared,
        "characters_cleared": characters_cleared,
    }


# ─── Request ────────────────────────────────────────────────

async def create_request(req_type: str, orientation: str = None,
                         scene_id: str = None, character_id: str = None,
                         project_id: str = None, video_id: str = None,
                         source_media_id: str = None, **_kw) -> dict:
    db = await get_db()
    rid, now = _uuid(), _now()
    async with _db_lock:
        await db.execute(
            """INSERT INTO request (id,project_id,video_id,scene_id,character_id,type,orientation,source_media_id,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (rid, project_id, video_id, scene_id, character_id, req_type, orientation, source_media_id, now, now))
        await db.commit()
    return await _get_with_db(db, "request", "id", rid)

async def get_request(rid: str): return await _get("request", "id", rid)
async def update_request(rid: str, **kw): return await _update("request", "id", rid, **kw)

async def list_requests(scene_id: str = None, status: str = None,
                        video_id: str = None, project_id: str = None) -> list[dict]:
    db = await get_db()
    q, params = "SELECT * FROM request WHERE 1=1", []
    if scene_id:
        q += " AND scene_id=?"; params.append(scene_id)
    if status:
        q += " AND status=?"; params.append(status)
    if video_id:
        q += " AND video_id=?"; params.append(video_id)
    if project_id:
        q += " AND project_id=?"; params.append(project_id)
    q += " ORDER BY created_at DESC"
    cur = await db.execute(q, params)
    return [dict(r) for r in await cur.fetchall()]

async def list_pending_requests() -> list[dict]:
    db = await get_db()
    cur = await db.execute("SELECT * FROM request WHERE status='PENDING' ORDER BY created_at")
    return [dict(r) for r in await cur.fetchall()]


async def migrate_upscale_requests_to_local() -> int:
    """Back-compat: convert legacy UPSCALE_VIDEO rows to UPSCALE_VIDEO_LOCAL."""
    db = await get_db()
    now = _now()
    async with _db_lock:
        cur = await db.execute(
            """
            UPDATE request
               SET type='UPSCALE_VIDEO_LOCAL',
                   updated_at=?,
                   next_retry_at=CASE WHEN status='PENDING' THEN NULL ELSE next_retry_at END,
                   retry_count=CASE WHEN status='PENDING' THEN 0 ELSE retry_count END,
                   error_message=CASE WHEN status='PENDING' THEN 'migrated to local upscale' ELSE error_message END
             WHERE type='UPSCALE_VIDEO'
            """,
            (now,),
        )
        await db.commit()
    return int(cur.rowcount or 0)


async def fail_stale_pending_local_upscale(timeout_seconds: int = 5400) -> int:
    """Mark very old pending local-upscale requests as FAILED to avoid restart storms."""
    from datetime import datetime, timedelta, timezone

    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=max(60, int(timeout_seconds)))
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    db = await get_db()
    async with _db_lock:
        cur = await db.execute(
            """
            UPDATE request
               SET status='FAILED',
                   next_retry_at=NULL,
                   error_message=COALESCE(error_message, 'stale pending local upscale auto-stopped on startup'),
                   updated_at=?
             WHERE status='PENDING'
               AND type='UPSCALE_VIDEO_LOCAL'
               AND updated_at < ?
            """,
            (_now(), cutoff),
        )
        await db.commit()
    return int(cur.rowcount or 0)


async def list_actionable_requests(exclude_ids: set[str] = None, limit: int = 5) -> list[dict]:
    """Priority-ordered fetch of PENDING requests ready to process."""
    db = await get_db()
    now = _now()
    exclude = exclude_ids or set()

    # Fetch all pending, filter in Python (SQLite doesn't support parameterized IN with variable length)
    cur = await db.execute("""
        SELECT * FROM request
        WHERE status = 'PENDING'
          AND (next_retry_at IS NULL OR next_retry_at <= ?)
        ORDER BY
          CASE
            WHEN type IN ('GENERATE_VIDEO','REGENERATE_VIDEO','GENERATE_VIDEO_REFS','UPSCALE_VIDEO')
              AND request_id IS NOT NULL THEN 1
            ELSE 0
          END,
          CASE type
            WHEN 'GENERATE_CHARACTER_IMAGE' THEN 0
            WHEN 'REGENERATE_CHARACTER_IMAGE' THEN 0
            WHEN 'EDIT_CHARACTER_IMAGE' THEN 0
            WHEN 'GENERATE_IMAGE' THEN 1
            WHEN 'REGENERATE_IMAGE' THEN 1
            WHEN 'EDIT_IMAGE' THEN 1
            WHEN 'GENERATE_VIDEO' THEN 2
            WHEN 'GENERATE_VIDEO_REFS' THEN 2
            WHEN 'UPSCALE_VIDEO' THEN 3
            WHEN 'UPSCALE_VIDEO_LOCAL' THEN 3
            ELSE 2
          END,
          created_at ASC
    """, (now,))
    rows = [dict(r) for r in await cur.fetchall()]
    # Exclude in-flight IDs
    filtered = [r for r in rows if r["id"] not in exclude]
    return filtered[:limit]


async def reset_stale_processing(cutoff_minutes: int = 10) -> int:
    """Reset PROCESSING requests older than cutoff back to PENDING."""
    db = await get_db()
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=cutoff_minutes)).strftime('%Y-%m-%dT%H:%M:%SZ')
    async with _db_lock:
        cursor = await db.execute(
            "UPDATE request SET status='PENDING', error_message='reset: stale processing' WHERE status='PROCESSING' AND updated_at < ?",
            (cutoff,))
        await db.commit()
        return cursor.rowcount


# ─── Material ────────────────────────────────────────────────

async def create_material(id: str, name: str, style_instruction: str,
                          negative_prompt: str = None, scene_prefix: str = None,
                          lighting: str = None) -> dict:
    db = await get_db()
    now = _now()
    async with _db_lock:
        await db.execute(
            """INSERT INTO material (id,name,style_instruction,negative_prompt,scene_prefix,lighting,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (id, name, style_instruction, negative_prompt, scene_prefix,
             lighting or "Studio lighting, highly detailed", now))
        await db.commit()
    return await _get_with_db(db, "material", "id", id)

async def get_material(mid: str): return await _get("material", "id", mid)
async def delete_material(mid: str): return await _delete("material", "id", mid)
async def list_materials() -> list[dict]:
    db = await get_db()
    cur = await db.execute("SELECT * FROM material ORDER BY created_at")
    return [dict(r) for r in await cur.fetchall()]
