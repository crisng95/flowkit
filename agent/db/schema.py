"""SQLite schema — async via aiosqlite."""
import asyncio
import aiosqlite
import logging
from agent.config import DB_PATH

logger = logging.getLogger(__name__)

_db_connection: aiosqlite.Connection | None = None
_db_lock = asyncio.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS character (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'character' CHECK(entity_type IN ('character','location','creature','visual_asset','generic_troop','faction')),
    description TEXT,
    image_prompt TEXT,
    voice_description TEXT,  -- max ~30 words, e.g. "Deep gravelly voice with a warm laugh"
    reference_image_url TEXT,
    media_id TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS project (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    story       TEXT,
    thumbnail_url TEXT,
    language    TEXT NOT NULL DEFAULT 'en',
    status      TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','ARCHIVED','DELETED')),
    user_paygate_tier TEXT NOT NULL DEFAULT 'PAYGATE_TIER_ONE',
    narrator_voice TEXT,
    narrator_ref_audio TEXT,
    material TEXT DEFAULT '3d_pixar',
    allow_music INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS material (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    style_instruction TEXT NOT NULL,
    negative_prompt TEXT,
    scene_prefix TEXT,
    lighting    TEXT DEFAULT 'Studio lighting, highly detailed',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS project_character (
    project_id    TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    character_id  TEXT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, character_id)
);

CREATE TABLE IF NOT EXISTS video (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    description   TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','PROCESSING','COMPLETED','FAILED')),
    vertical_url  TEXT,
    horizontal_url TEXT,
    thumbnail_url TEXT,
    duration      REAL,
    resolution    TEXT,
    youtube_id    TEXT,
    privacy       TEXT NOT NULL DEFAULT 'unlisted',
    tags          TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS scene (
    id              TEXT PRIMARY KEY,
    video_id        TEXT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    display_order   INTEGER NOT NULL DEFAULT 0,
    prompt          TEXT,
    image_prompt    TEXT,
    video_prompt    TEXT,
    character_names TEXT,  -- JSON array of reference entity names (characters, locations, assets)

    parent_scene_id TEXT REFERENCES scene(id) ON DELETE SET NULL,
    chain_type      TEXT NOT NULL DEFAULT 'ROOT' CHECK(chain_type IN ('ROOT','CONTINUATION','INSERT')),
    source          TEXT NOT NULL DEFAULT 'root' CHECK(source IN ('root','user','system')),

    -- Vertical orientation
    vertical_image_url          TEXT,
    vertical_image_media_id TEXT,
    vertical_image_status       TEXT NOT NULL DEFAULT 'PENDING' CHECK(vertical_image_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    vertical_video_url          TEXT,
    vertical_video_media_id TEXT,
    vertical_video_status       TEXT NOT NULL DEFAULT 'PENDING' CHECK(vertical_video_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    vertical_upscale_url        TEXT,
    vertical_upscale_media_id TEXT,
    vertical_upscale_status     TEXT NOT NULL DEFAULT 'PENDING' CHECK(vertical_upscale_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),

    -- Horizontal orientation
    horizontal_image_url          TEXT,
    horizontal_image_media_id TEXT,
    horizontal_image_status       TEXT NOT NULL DEFAULT 'PENDING' CHECK(horizontal_image_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    horizontal_video_url          TEXT,
    horizontal_video_media_id TEXT,
    horizontal_video_status       TEXT NOT NULL DEFAULT 'PENDING' CHECK(horizontal_video_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    horizontal_upscale_url        TEXT,
    horizontal_upscale_media_id TEXT,
    horizontal_upscale_status     TEXT NOT NULL DEFAULT 'PENDING' CHECK(horizontal_upscale_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),

    -- Chain source (for continuation scenes)
    vertical_end_scene_media_id   TEXT,
    horizontal_end_scene_media_id TEXT,

    -- Trim
    trim_start  REAL,
    trim_end    REAL,
    duration    REAL,

    -- Narration
    narrator_text TEXT,

    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS request (
    id            TEXT PRIMARY KEY,
    project_id    TEXT REFERENCES project(id) ON DELETE CASCADE,
    video_id      TEXT REFERENCES video(id) ON DELETE CASCADE,
    scene_id      TEXT REFERENCES scene(id) ON DELETE CASCADE,
    character_id  TEXT REFERENCES character(id) ON DELETE CASCADE,
    type          TEXT NOT NULL CHECK(type IN ('GENERATE_IMAGE','REGENERATE_IMAGE','EDIT_IMAGE','GENERATE_VIDEO','GENERATE_VIDEO_REFS','UPSCALE_VIDEO','GENERATE_CHARACTER_IMAGE','REGENERATE_CHARACTER_IMAGE','EDIT_CHARACTER_IMAGE')),
    orientation   TEXT CHECK(orientation IN ('VERTICAL','HORIZONTAL')),
    status        TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    request_id    TEXT,   -- external operation ID
    media_id  TEXT,
    output_url    TEXT,
    error_message TEXT,
    retry_count   INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT,
    edit_prompt   TEXT,    -- prompt for EDIT_IMAGE requests
    source_media_id TEXT,  -- source image media_id for EDIT_IMAGE requests
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_scene_video ON scene(video_id);
CREATE INDEX IF NOT EXISTS idx_scene_order ON scene(video_id, display_order);
CREATE INDEX IF NOT EXISTS idx_request_status ON request(status);
CREATE INDEX IF NOT EXISTS idx_request_scene ON request(scene_id);
CREATE INDEX IF NOT EXISTS idx_video_project ON video(project_id);
"""


async def init_db():
    """Initialize database with schema and run migrations."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(SCHEMA)
        # Migration: add voice_description if missing (added after initial schema)
        cursor = await db.execute("PRAGMA table_info(character)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "voice_description" not in columns:
            await db.execute("ALTER TABLE character ADD COLUMN voice_description TEXT DEFAULT ''")
            logger.info("Migrated: added voice_description column to character table")
        # Migration: add edit_prompt and source_media_id to request table
        cursor = await db.execute("PRAGMA table_info(request)")
        req_columns = {row[1] for row in await cursor.fetchall()}
        if "edit_prompt" not in req_columns:
            await db.execute("ALTER TABLE request ADD COLUMN edit_prompt TEXT")
            logger.info("Migrated: added edit_prompt column to request table")
        if "source_media_id" not in req_columns:
            await db.execute("ALTER TABLE request ADD COLUMN source_media_id TEXT")
            logger.info("Migrated: added source_media_id column to request table")
        # Migration: add queue columns to request table
        cursor = await db.execute("PRAGMA table_info(request)")
        request_columns = {row[1] for row in await cursor.fetchall()}
        if "next_retry_at" not in request_columns:
            await db.execute("ALTER TABLE request ADD COLUMN next_retry_at TEXT")
            logger.info("Migrated: added next_retry_at column to request table")
        if "retry_count" not in request_columns:
            await db.execute("ALTER TABLE request ADD COLUMN retry_count INTEGER DEFAULT 0")
            logger.info("Migrated: added retry_count column to request table")
        # Migration: ensure request table CHECK constraint includes all request types
        # SQLite can't alter CHECK constraints, so recreate the table
        cursor = await db.execute("SELECT sql FROM sqlite_master WHERE name='request' AND type='table'")
        row = await cursor.fetchone()
        needs_recreate = False
        if row:
            table_sql = row[0]
            if 'GENERATE_IMAGES' in table_sql and 'GENERATE_IMAGE,' not in table_sql:
                needs_recreate = True  # old GENERATE_IMAGES typo
            if 'REGENERATE_IMAGE' not in table_sql:
                needs_recreate = True  # missing REGENERATE/EDIT types
        if needs_recreate:
            await db.execute("PRAGMA foreign_keys=OFF")
            await db.execute("ALTER TABLE request RENAME TO _request_old")
            await db.executescript("""
CREATE TABLE IF NOT EXISTS request (
    id            TEXT PRIMARY KEY,
    project_id    TEXT REFERENCES project(id) ON DELETE CASCADE,
    video_id      TEXT REFERENCES video(id) ON DELETE CASCADE,
    scene_id      TEXT REFERENCES scene(id) ON DELETE CASCADE,
    character_id  TEXT REFERENCES character(id) ON DELETE CASCADE,
    type          TEXT NOT NULL CHECK(type IN ('GENERATE_IMAGE','REGENERATE_IMAGE','EDIT_IMAGE','GENERATE_VIDEO','GENERATE_VIDEO_REFS','UPSCALE_VIDEO','GENERATE_CHARACTER_IMAGE','REGENERATE_CHARACTER_IMAGE','EDIT_CHARACTER_IMAGE')),
    orientation   TEXT CHECK(orientation IN ('VERTICAL','HORIZONTAL')),
    status        TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    request_id    TEXT,
    media_id      TEXT,
    output_url    TEXT,
    error_message TEXT,
    retry_count   INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT,
    edit_prompt   TEXT,
    source_media_id TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_request_status ON request(status);
CREATE INDEX IF NOT EXISTS idx_request_scene ON request(scene_id);
""")
            await db.execute("INSERT OR IGNORE INTO request SELECT * FROM _request_old")
            await db.execute("UPDATE request SET type='GENERATE_IMAGE' WHERE type='GENERATE_IMAGES'")
            await db.execute("DROP TABLE _request_old")
            await db.execute("PRAGMA foreign_keys=ON")
            logger.info("Migrated: renamed GENERATE_IMAGES -> GENERATE_IMAGE in request table")
        # Migration: add source column to scene table
        cursor = await db.execute("PRAGMA table_info(scene)")
        scene_columns = {row[1] for row in await cursor.fetchall()}
        if "source" not in scene_columns:
            await db.execute("ALTER TABLE scene ADD COLUMN source TEXT NOT NULL DEFAULT 'root'")
            logger.info("Migrated: added source column to scene table")
        if "narrator_text" not in scene_columns:
            await db.execute("ALTER TABLE scene ADD COLUMN narrator_text TEXT")
            logger.info("Migrated: added narrator_text column to scene table")
        # Migration: add narrator fields to project table
        cursor = await db.execute("PRAGMA table_info(project)")
        project_columns = {row[1] for row in await cursor.fetchall()}
        if "narrator_voice" not in project_columns:
            await db.execute("ALTER TABLE project ADD COLUMN narrator_voice TEXT")
            logger.info("Migrated: added narrator_voice column to project table")
        if "narrator_ref_audio" not in project_columns:
            await db.execute("ALTER TABLE project ADD COLUMN narrator_ref_audio TEXT")
            logger.info("Migrated: added narrator_ref_audio column to project table")
        if "material" not in project_columns:
            await db.execute("ALTER TABLE project ADD COLUMN material TEXT DEFAULT '3d_pixar'")
            logger.info("Migrated: added material column to project table")
        # Migration: create material table if missing
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='material'")
        if not await cursor.fetchone():
            await db.execute("""CREATE TABLE material (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, style_instruction TEXT NOT NULL,
    negative_prompt TEXT, scene_prefix TEXT, lighting TEXT DEFAULT 'Studio lighting, highly detailed',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))""")
            logger.info("Migrated: created material table")
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)


async def get_db() -> aiosqlite.Connection:
    """Return the shared database connection, creating it if needed."""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(str(DB_PATH))
        _db_connection.row_factory = aiosqlite.Row
        await _db_connection.execute("PRAGMA journal_mode=WAL")
        await _db_connection.execute("PRAGMA foreign_keys=ON")
    return _db_connection


async def close_db() -> None:
    """Close the shared database connection."""
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        _db_connection = None
        logger.info("Database connection closed")
