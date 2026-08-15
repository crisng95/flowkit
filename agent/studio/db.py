"""SQLite store for Flow Studio (stdlib sqlite3, accessed via asyncio.to_thread).

One module-level connection (check_same_thread=False) guarded by a lock. The full
schema from video-app.md §4 is created up-front so later phases need no migration.
"""
import asyncio
import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from agent.config import BASE_DIR

DB_PATH = Path(os.environ.get("STUDIO_DB", BASE_DIR / "agent" / "studio.db"))

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
  id TEXT PRIMARY KEY, title TEXT, flow_project_id TEXT,
  style TEXT DEFAULT 'Realistic',
  aspect_ratio TEXT DEFAULT 'VIDEO_ASPECT_RATIO_LANDSCAPE',
  paygate_tier TEXT DEFAULT 'PAYGATE_TIER_ONE',
  image_model TEXT, video_model TEXT,
  voice_id INTEGER, agent TEXT,
  idea TEXT, target_duration INTEGER, shot_duration INTEGER DEFAULT 8,
  storytelling INTEGER DEFAULT 0,
  voiceover_raw TEXT, script_raw TEXT,
  prompt_header TEXT, prompt_footer TEXT, culture_hint TEXT,
  image_text_lang TEXT DEFAULT 'Vietnamese',
  script_lang TEXT DEFAULT 'Vietnamese',
  bgm_path TEXT, bgm_volume REAL DEFAULT 0.18, bgm_duck INTEGER DEFAULT 1,
  tts_speed REAL DEFAULT 1.0,
  seed INTEGER,
  thumb_media_key TEXT,
  status TEXT DEFAULT 'draft',
  created_at REAL, updated_at REAL
);

CREATE TABLE IF NOT EXISTS entity (
  id TEXT PRIMARY KEY, project_id TEXT, type TEXT,
  name TEXT, description TEXT, ref_prompt TEXT,
  media_id TEXT, primary_media_id TEXT, workflow_id TEXT,
  image_path TEXT, image_url TEXT, graph_json TEXT,
  extra_media TEXT,
  created_at REAL, updated_at REAL
);

CREATE TABLE IF NOT EXISTS scene (
  id TEXT PRIMARY KEY, project_id TEXT, idx INTEGER,
  heading TEXT, slug TEXT, action TEXT, dialog TEXT,
  location_entity_id TEXT, source_segment TEXT,
  source_start INTEGER, source_end INTEGER,
  created_at REAL
);

CREATE TABLE IF NOT EXISTS shot (
  id TEXT PRIMARY KEY, scene_id TEXT, idx INTEGER, title TEXT,
  beat_id TEXT, part_idx INTEGER DEFAULT 0, is_chained INTEGER DEFAULT 0,
  description TEXT, ref_entity_ids TEXT,
  image_media_id TEXT, image_primary_id TEXT, image_workflow_id TEXT, image_path TEXT,
  visual_prompt TEXT, motion_prompt TEXT, beat_action TEXT,
  video_model TEXT, duration INTEGER DEFAULT 8,
  video_media_id TEXT, video_primary_id TEXT, video_workflow_id TEXT, video_path TEXT,
  upscale_path TEXT, upscale_url TEXT, operation_json TEXT, graph_json TEXT,
  narrator_text TEXT, narration_path TEXT, narration_duration REAL, start_time REAL,
  status TEXT DEFAULT 'pending', created_at REAL, updated_at REAL
);

CREATE TABLE IF NOT EXISTS job (
  id TEXT PRIMARY KEY, project_id TEXT, type TEXT, target_id TEXT,
  status TEXT, progress REAL, message TEXT, error TEXT,
  created_at REAL, updated_at REAL
);

CREATE TABLE IF NOT EXISTS asset (
  id TEXT PRIMARY KEY, project_id TEXT, kind TEXT,
  path TEXT, meta_json TEXT, created_at REAL
);

CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);

-- Playlist nhạc của dự án (music video): NHIỀU bài phát nối tiếp, cách nhau `project.music_gap`
-- giây im lặng. Khác `project.bgm_path` (một bài duy nhất trộn CHÌM dưới lời đọc) — ở đây nhạc
-- là tiếng chính và tổng thời lượng playlist quyết định độ dài video.
CREATE TABLE IF NOT EXISTS music_track (
  id TEXT PRIMARY KEY, project_id TEXT, idx INTEGER,
  title TEXT, path TEXT, duration REAL,
  source TEXT,              -- flowmusic | upload
  audio_url TEXT, meta_json TEXT,
  created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_track_project ON music_track(project_id, idx);

-- Tài khoản Google đã từng đăng nhập Flow qua extension. id = email viết thường (Flow chỉ
-- có một account hoạt động tại một thời điểm — theo phiên Chrome), `sub` giữ id Google bền
-- vững để nhận ra cùng một người nếu email đổi.
CREATE TABLE IF NOT EXISTS account (
  id TEXT PRIMARY KEY, email TEXT, name TEXT, picture TEXT, sub TEXT,
  paygate_tier TEXT, created_at REAL, last_seen_at REAL
);

-- Lịch sử media (§13#8): mỗi lần một ảnh/video được gán cho shot/entity → 1 dòng,
-- để xem lại & khôi phục bản cũ thay vì ghi đè mất.
CREATE TABLE IF NOT EXISTS media_history (
  id TEXT PRIMARY KEY, project_id TEXT,
  owner_kind TEXT, owner_id TEXT, slot TEXT,   -- shot|entity ; image|video
  media_id TEXT, primary_media_id TEXT, path TEXT,
  created_at REAL
);

CREATE INDEX IF NOT EXISTS idx_entity_project ON entity(project_id);
CREATE INDEX IF NOT EXISTS idx_scene_project ON scene(project_id);
CREATE INDEX IF NOT EXISTS idx_mhist_owner ON media_history(owner_id, slot);
CREATE INDEX IF NOT EXISTS idx_shot_scene ON shot(scene_id);
"""

# Columns added after the initial schema shipped — ALTER on existing DBs (idempotent).
_MIGRATIONS = [
    ("project", "prompt_header", "TEXT"),
    ("project", "prompt_footer", "TEXT"),
    ("project", "culture_hint", "TEXT"),
    # Language for any text drawn/written INSIDE generated images (signs, captions,
    # labels). Default Vietnamese; domain-specific foreign terms stay as-is.
    ("project", "image_text_lang", "TEXT DEFAULT 'Vietnamese'"),
    # Language the script / dialogue / voiceover is written in (default Vietnamese).
    ("project", "script_lang", "TEXT DEFAULT 'Vietnamese'"),
    # Optional background music mixed under the narration when assembling the final video.
    ("project", "bgm_path", "TEXT"),
    ("project", "bgm_volume", "REAL DEFAULT 0.18"),
    # Auto-duck the music under the narration (1 = on).
    ("project", "bgm_duck", "INTEGER DEFAULT 1"),
    # Narration reading speed for OmniVoice TTS (1.0 = normal).
    ("project", "tts_speed", "REAL DEFAULT 1.0"),
    # Silent breathing pause inserted between beats in the scene narration (seconds). Also the
    # room a cross-dissolve has to land in; set ~1s (24f) for a full dissolve in silence.
    ("project", "tts_gap", "REAL DEFAULT 0.4"),
    # Silent pause inserted between SENTENCES within a beat (seconds). Sentences are read one
    # at a time so the engine pauses at every '.'/'?'/'!' — this is the breath between them.
    ("project", "tts_sentence_gap", "REAL DEFAULT 0.3"),
    # Silent edge padding prepended AND appended to each scene WAV (seconds). Gives a
    # cross-dissolve in the editor (DaVinci etc.) silent "handles" to chew on at both ends so
    # the transition never eats the first/last spoken words. ~0.5s covers a 24f dissolve.
    ("project", "tts_edge_pad", "REAL DEFAULT 0.5"),
    # Seed-lock: when set, image generation reuses this seed (reproducible). NULL = random.
    ("project", "seed", "INTEGER"),
    # A shot has two independent node graphs: graph_json = the storyboard IMAGE graph,
    # video_graph_json = the shots-tab VIDEO graph. They must not share storage.
    ("shot", "video_graph_json", "TEXT"),
    # Storytelling (§2.6, audio-first): ONE continuous TTS per scene (kept whole so the
    # narration keeps its emotional flow); beats are timing windows over it.
    ("scene", "narration_text", "TEXT"),
    ("scene", "narration_path", "TEXT"),
    ("scene", "narration_duration", "REAL"),
    # Timed keyword captions burned on the video / exported to DaVinci (JSON list of
    # {text, start, end} in scene-local seconds).
    ("shot", "captions", "TEXT"),
    # Ảnh Flow sinh ra chỉ là bản HD; bật cờ này để tự tải thêm bản 2K/4K (theo tier) qua
    # upsampleImage sau mỗi lần sinh ảnh — dùng khi dựng video từ ảnh / export DaVinci.
    ("project", "auto_hires", "INTEGER DEFAULT 0"),
    # Bản hi-res của ảnh shot: file riêng cạnh bản HD (image_path vẫn là bản nhẹ để hiển thị).
    # image_hires_media_id = ảnh HD mà bản này được phóng to từ đó → regen ảnh làm nó cũ đi.
    ("shot", "image_hires_path", "TEXT"),
    ("shot", "image_hires_media_id", "TEXT"),
    ("shot", "image_hires_res", "TEXT"),
    # Video cũng chỉ sinh ra bản HD. Bật cờ này để tự upscale sau khi render xong — trần theo
    # tier (ONE → 1080p, TWO → 4K). Mỗi lượt mất ~1 phút (render bất đồng bộ).
    ("project", "auto_upscale_video", "INTEGER DEFAULT 0"),
    # upscale_path/upscale_url đã có sẵn; thêm nguồn + độ phân giải để biết bản upscale còn
    # đúng với video hiện tại hay đã cũ (shot render lại video sau khi upscale).
    ("shot", "upscale_media_id", "TEXT"),
    ("shot", "upscale_res", "TEXT"),
    # Độ phân giải upscale MONG MUỐN. Rỗng = kịch trần của tier. Tier TWO có thể chọn 1080p
    # thay vì 4K cho nhẹ/rẻ; giá trị vượt trần tier bị hạ xuống chứ không làm Flow từ chối.
    ("project", "upscale_res", "TEXT"),
    # Music video: nhạc (playlist `music_track`) là tiếng chính thay cho lời đọc, và tổng thời
    # lượng playlist quyết định độ dài video — hình được lặp lại cho phủ kín. 0 = video thường
    # (dùng `bgm_path` trộn chìm dưới narration như cũ).
    ("project", "music_mode", "INTEGER DEFAULT 0"),
    # Khoảng lặng chèn GIỮA hai bài liên tiếp (giây). Không cộng vào sau bài cuối.
    ("project", "music_gap", "REAL DEFAULT 3.0"),
    # Chủ sở hữu dự án = tài khoản Flow đã tạo nó (account.id). Media/media_id của Flow chỉ
    # resolve được bằng token của đúng account đó, nên dự án không dùng chung được giữa các
    # account. NULL = dự án có từ trước khi có phân tài khoản (được nhận về cho account đầu
    # tiên nhìn thấy — xem _adopt_orphan_projects).
    ("project", "account_id", "TEXT"),
    # Location entities get extra angle views (besides the primary establishing shot) so a
    # shot has several angles of the place to reference — JSON list of {media_id,
    # primary_media_id, path}. Stops shots from copying one fixed location framing.
    ("entity", "extra_media", "TEXT"),
    # Ảnh tham chiếu của một BỐI CẢNH: 4 = lưới 2x2 bốn góc máy (mặc định, có dán nhãn
    # Toàn cảnh/Góc ngược/Trên cao/Cận cảnh lên bản hiển thị), 1 = một ảnh một góc máy
    # (không lưới, không dán nhãn). Xem brain.location_frames().
    ("project", "location_frames", "INTEGER DEFAULT 4"),
    # Ảnh tham chiếu của một NHÂN VẬT: 0 = bảng "Character Production Bible" 13 mục (mặc
    # định), 1 = MỘT ảnh toàn thân chính diện nền trơn. Xem brain.character_one().
    ("project", "character_one", "INTEGER DEFAULT 0"),
    # Cách viết shot trong một scene: 0 = khung RỜI minh hoạ lời đọc (mặc định, hợp kể
    # chuyện), 1 = chuỗi LIÊN TỤC theo ngữ pháp dựng phim (hợp khi đích đến là video).
    # Xem brain.shot_continuity() + hai bản của khối CINEMATOGRAPHY.
    ("project", "shot_continuity", "INTEGER DEFAULT 0"),
    # Ghi đè các PROMPT NGẦM (brain.PROMPT_DEFAULTS): trống = dùng mặc định trong code,
    # "-" = tắt hẳn khối đó. Mỗi cột ứng với một khoá của PROMPT_DEFAULTS.
    *[("project", f"tpl_{k}", "TEXT") for k in (
        "single_frame", "single_frame_grid", "image_text", "video_text",
        "sheet_character", "sheet_character_one", "sheet_prop",
        "sheet_location", "sheet_location_one",
        "cine", "cine_continuous", "motion", "omni_timeline")],
]


def _migrate(conn: sqlite3.Connection) -> None:
    for table, col, decl in _MIGRATIONS:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(_SCHEMA)
        _conn.commit()
        _migrate(_conn)
    return _conn


def now() -> float:
    return time.time()


def new_id() -> str:
    return str(uuid.uuid4())


# ─── Sync primitives (run inside to_thread) ─────────────────

def _query_all(sql: str, params: tuple = ()) -> list[dict]:
    with _lock:
        cur = _get_conn().execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def _query_one(sql: str, params: tuple = ()) -> dict | None:
    with _lock:
        cur = _get_conn().execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def _execute(sql: str, params: tuple = ()) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute(sql, params)
        conn.commit()


# ─── Async wrappers ─────────────────────────────────────────

async def query_all(sql: str, params: tuple = ()) -> list[dict]:
    return await asyncio.to_thread(_query_all, sql, params)


async def query_one(sql: str, params: tuple = ()) -> dict | None:
    return await asyncio.to_thread(_query_one, sql, params)


async def execute(sql: str, params: tuple = ()) -> None:
    await asyncio.to_thread(_execute, sql, params)


# ─── Generic helpers ────────────────────────────────────────

async def insert(table: str, data: dict) -> None:
    cols = ", ".join(data)
    placeholders = ", ".join("?" for _ in data)
    await execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(data.values()))


async def update(table: str, id_: str, data: dict) -> None:
    if not data:
        return
    sets = ", ".join(f"{k}=?" for k in data)
    await execute(f"UPDATE {table} SET {sets} WHERE id=?", (*data.values(), id_))


async def delete(table: str, id_: str) -> None:
    await execute(f"DELETE FROM {table} WHERE id=?", (id_,))


# ─── kv settings ────────────────────────────────────────────

async def kv_get_all() -> dict:
    rows = await query_all("SELECT key, value FROM kv")
    out = {}
    for r in rows:
        try:
            out[r["key"]] = json.loads(r["value"])
        except (json.JSONDecodeError, TypeError):
            out[r["key"]] = r["value"]
    return out


async def kv_get(key: str, default=None):
    row = await query_one("SELECT value FROM kv WHERE key=?", (key,))
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return row["value"]


async def kv_set(key: str, value) -> None:
    await execute(
        "INSERT INTO kv(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)),
    )
