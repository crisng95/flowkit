"""Flow Studio API — stateful orchestration over the Flow proxy (video-app.md).

Phase 0: project CRUD (DB + Flow), Flow project import with thumbnails, options,
settings, health. Heavier pipeline endpoints land in later phases.
"""
import asyncio
import json
import logging
import math
import os
import random
import re
import shutil
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from agent.config import (
    IMAGE_MODELS, VIDEO_MODELS, UPSCALE_MODELS, OMNI_FLASH_MODELS,
    UPSAMPLE_VIDEO_RESOLUTIONS, VIDEO_POLL_TIMEOUT,
    VEO_LITE_MODELS, VEO_LITE_FRAME_DURATIONS, VEO_LITE_DEFAULT_S, VEO_LITE_TIERS,
)
from agent.services.flow_client import get_flow_client
from agent.services.music_client import get_music_client
from agent.studio import (
    db, media_store, brain, assembler, davinci_xml, vntext, align, hires,
    accounts, music as music_mod, graph as graph_mod, videopoll,
)
from agent.studio.jobs import get_job_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio", tags=["studio"])

# Storytelling: one shot = one generated image, so shot length drives how many images a chapter
# costs. Aim each shot at the [MIN, MAX] band of narration (~8–10s) rather than merely capping it
# — packing to fill the band avoids the swarm of 3–5s shots that blew up the image count.
MIN_SHOT_SECS = float(os.environ.get("FLOWKIT_MIN_SHOT_SECS", "8"))
MAX_SHOT_SECS = float(os.environ.get("FLOWKIT_MAX_SHOT_SECS", "10"))
SHOT_TARGET_SECS = (MIN_SHOT_SECS + MAX_SHOT_SECS) / 2      # drives how many beats we ask AI for
# When one beat is split into several sub-shots, rotate the framing so they don't render as
# the same still — a natural coverage cycle (establish → tighten → reaction → insert).
_SUBSHOT_ANGLES = [
    "wide establishing shot", "medium shot", "over-the-shoulder shot", "close-up",
    "reaction close-up", "low-angle medium shot", "high-angle wide shot", "insert detail shot",
]
# A whole chapter sometimes parses to ONE scene; split it into ~this-many-second sub-scenes so
# each gets its own coherent shot plan (env FLOWKIT_TARGET_SCENE_SECS).
TARGET_SCENE_SECS = float(os.environ.get("FLOWKIT_TARGET_SCENE_SECS", "90"))
# Max reference images per frame generate. Flow returns HTTP 400 above 8, so cap here (location
# is kept first, then the most relevant entities; the overflow is dropped). Env-overridable.
MAX_FRAME_REFS = max(1, int(os.environ.get("FLOWKIT_MAX_FRAME_REFS", "8")))
_PART_SUFFIX_RE = re.compile(r"\s*·\s*phần\s*\d+/\d+\s*$")


def _part_heading(heading: str, i: int, n: int) -> str:
    """Sub-scene heading = the parent's (location intact at the front) + a '· phần i/n' suffix.
    The location text stays at the START so heading→location matching is unchanged; the suffix
    only distinguishes the parts in the UI. Strips any prior suffix so re-splitting won't stack."""
    base = _PART_SUFFIX_RE.sub("", heading or "").rstrip()
    return f"{base} · phần {i}/{n}"
# Google đôi khi chặn ảnh theo policy (không trả media) hoặc trả filtered → thử lại.
IMAGE_GEN_RETRIES = 3
# Video tốn thời gian (15–30s/lần) nên thử lại ít hơn.
VIDEO_GEN_RETRIES = 2
# Storyboard batch image gen: fire this many frames at once sharing ONE Flow batch id (like
# the web UI's 4-image batch), then wait the cooldown before the next group. Cuts wall-clock
# time on big storyboards (400+ frames) ~batch-fold. Env-overridable.
IMAGE_BATCH_SIZE = int(os.environ.get("FLOWKIT_IMAGE_BATCH_SIZE", "4"))
IMAGE_BATCH_COOLDOWN = (
    float(os.environ.get("FLOWKIT_IMAGE_BATCH_COOLDOWN", "10")),
    float(os.environ.get("FLOWKIT_IMAGE_BATCH_COOLDOWN_MAX", "13")),
)
# Spread a batch's submits by up to index*random(stagger) seconds so the group doesn't hit
# Flow at the exact same instant (dodges the 'unusual activity' heuristic) while staying mostly
# concurrent. Set FLOWKIT_IMAGE_BATCH_STAGGER=0 to fire simultaneously, or SIZE=1 for sequential.
IMAGE_BATCH_STAGGER = (
    float(os.environ.get("FLOWKIT_IMAGE_BATCH_STAGGER", "0.3")),
    float(os.environ.get("FLOWKIT_IMAGE_BATCH_STAGGER_MAX", "0.8")),
)

# Batch VIDEO — cùng cơ chế batch ảnh nhưng CONSERVATIVE hơn hẳn, có lý do đo được: bắn 4
# submit video thật sự đồng thời bị Google chặn ("hoạt động bất thường", 3/4 lượt hỏng),
# trong khi batch 4 ảnh chạy êm. Video nhạy với đồng thời hơn ảnh nhiều.
#
# Cái ăn tiền ở đây KHÔNG phải submit song song mà là POLL song song: submit đi qua
# single-flight lock của flow_client nên vốn đã nối đuôi nhau, còn render mất 30–240s và
# trước đây job chờ hết clip này mới submit clip sau. Chạy theo lô N clip thì tổng thời gian
# ≈ clip lâu nhất của lô thay vì tổng cả lô.
# Stagger để dài hơn hẳn bên ảnh (giây, không phải phần mười giây) cho mỗi submit tự giải
# captcha riêng — đó là khoảng cách tự nhiên mà Flow UI cũng có.
VIDEO_BATCH_SIZE = int(os.environ.get("FLOWKIT_VIDEO_BATCH_SIZE", "3"))
VIDEO_BATCH_COOLDOWN = (
    float(os.environ.get("FLOWKIT_VIDEO_BATCH_COOLDOWN", "20")),
    float(os.environ.get("FLOWKIT_VIDEO_BATCH_COOLDOWN_MAX", "30")),
)
VIDEO_BATCH_STAGGER = (
    float(os.environ.get("FLOWKIT_VIDEO_BATCH_STAGGER", "4")),
    float(os.environ.get("FLOWKIT_VIDEO_BATCH_STAGGER_MAX", "8")),
)
# Google anti-abuse block ("unusual activity"/429): retrying fast EXTENDS the block, so on a
# detected block we wait this long before retrying (vs a few seconds for a normal transient),
# and grant a few EXTRA attempts so one block doesn't burn the normal retry budget.
ABUSE_BLOCK_BACKOFF = (
    float(os.environ.get("FLOWKIT_ABUSE_BACKOFF", "30")),
    float(os.environ.get("FLOWKIT_ABUSE_BACKOFF_MAX", "60")),
)
ABUSE_EXTRA_RETRIES = int(os.environ.get("FLOWKIT_ABUSE_EXTRA_RETRIES", "3"))
_ABUSE_RE = re.compile(
    r"unusual activity|bất thường|rate.?limit|too many request|resource_exhausted|quota|"
    r"try again later|temporarily",
    re.I)


def _is_abuse_block(res: dict) -> bool:
    """True if a Flow response is a Google anti-abuse / rate-limit block ('unusual activity',
    HTTP 429/403). Such a block must be backed off LONG — an immediate retry extends it."""
    if not isinstance(res, dict):
        return False
    if res.get("status") in (429, 403):
        return True
    try:
        return bool(_ABUSE_RE.search(json.dumps(res, ensure_ascii=False)))
    except (TypeError, ValueError):
        return False


# ─── Models ──────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    title: str
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE"
    style: str = "Realistic"
    storytelling: bool = False
    script_lang: str = "Vietnamese"       # ngôn ngữ kịch bản / lời thoại / lời đọc
    image_text_lang: str = "Vietnamese"   # ngôn ngữ chữ viết/vẽ trong ảnh
    import_flow_project_id: Optional[str] = None   # gắn vào project Flow có sẵn
    import_thumb_media_key: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    style: Optional[str] = None
    aspect_ratio: Optional[str] = None
    paygate_tier: Optional[str] = None
    image_model: Optional[str] = None
    video_model: Optional[str] = None
    voice_id: Optional[int] = None
    agent: Optional[str] = None
    idea: Optional[str] = None
    target_duration: Optional[int] = None
    shot_duration: Optional[int] = None
    storytelling: Optional[bool] = None
    auto_hires: Optional[bool] = None
    auto_upscale_video: Optional[bool] = None
    upscale_res: Optional[str] = None
    script_lang: Optional[str] = None
    image_text_lang: Optional[str] = None
    bgm_volume: Optional[float] = None
    bgm_duck: Optional[bool] = None
    tts_speed: Optional[float] = None
    tts_gap: Optional[float] = None
    tts_sentence_gap: Optional[float] = None
    tts_edge_pad: Optional[float] = None
    seed: Optional[int] = None
    prompt_header: Optional[str] = None
    prompt_footer: Optional[str] = None
    culture_hint: Optional[str] = None
    location_frames: Optional[int] = None    # ảnh bối cảnh: 4 = lưới 2x2, 1 = một ảnh
    character_one: Optional[int] = None      # ảnh nhân vật: 0 = bảng sheet, 1 = một ảnh
    shot_continuity: Optional[int] = None    # shot: 0 = khung rời, 1 = chuỗi liên tục
    # Ghi đè prompt ngầm — trống = dùng mặc định của code, "-" = tắt khối đó.
    tpl_single_frame: Optional[str] = None
    tpl_single_frame_grid: Optional[str] = None
    tpl_scene_physics: Optional[str] = None
    tpl_image_text: Optional[str] = None
    tpl_video_text: Optional[str] = None
    tpl_sheet_character: Optional[str] = None
    tpl_sheet_character_one: Optional[str] = None
    tpl_sheet_prop: Optional[str] = None
    tpl_sheet_location: Optional[str] = None
    tpl_sheet_location_one: Optional[str] = None
    tpl_cine: Optional[str] = None
    tpl_cine_continuous: Optional[str] = None
    tpl_scene_arc: Optional[str] = None
    tpl_scene_arc_in: Optional[str] = None
    tpl_scene_arc_out: Optional[str] = None
    tpl_motion: Optional[str] = None
    tpl_omni_timeline: Optional[str] = None


class GenerateScriptRequest(BaseModel):
    idea: str
    target_duration: Optional[int] = None   # giây


class SaveScriptRequest(BaseModel):
    script: str


class ScriptChatRequest(BaseModel):
    instruction: str


class AddEntityRequest(BaseModel):
    type: str = "character"        # character | location | prop
    name: str
    description: str = ""
    ref_prompt: str = ""


class UpdateEntityRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ref_prompt: Optional[str] = None
    type: Optional[str] = None


class SetMediaRequest(BaseModel):
    media_id: str


class ImportEntityRequest(BaseModel):
    source_entity_id: str


class LinkEntityRequest(BaseModel):
    source_entity_id: str


class ImportMediaRequest(BaseModel):
    media_id: str
    name: str = "Flow asset"
    type: str = "character"
    description: str = ""


# ─── Helpers ─────────────────────────────────────────────────

def _deep_find(obj, key: str):
    """First value for `key` anywhere in a nested dict/list (tRPC envelopes)."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _deep_find(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _deep_find(v, key)
            if found is not None:
                return found
    return None


def _flow_projects(raw: dict) -> list[dict]:
    """Pull the projects array out of the tRPC envelope."""
    data = raw.get("data", raw) if isinstance(raw, dict) else {}
    projects = _deep_find(data, "projects")
    out = []
    for p in projects or []:
        info = p.get("projectInfo", {})
        out.append({
            "flow_project_id": p.get("projectId"),
            "title": info.get("projectTitle"),
            "thumb_media_key": info.get("thumbnailMediaKey"),
            "creation_time": p.get("creationTime"),
        })
    return out


def _require_extension():
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension chưa kết nối (mở Google Flow trong Chrome)")
    return client


_tier_cache = {"value": None, "ts": 0.0}


async def _current_tier() -> str:
    """User's paygate tier from /api/flow/credits (không do người dùng chọn). Cache 60s."""
    import time as _t
    if _tier_cache["value"] and _t.monotonic() - _tier_cache["ts"] < 60:
        return _tier_cache["value"]
    client = get_flow_client()
    if client.connected:
        try:
            res = await client.get_credits()
            data = res.get("data", res)
            tier = data.get("userPaygateTier") if isinstance(data, dict) else None
            if tier:
                _tier_cache.update(value=tier, ts=_t.monotonic())
                return tier
        except Exception:
            pass
    return _tier_cache["value"] or "PAYGATE_TIER_ONE"


async def _current_tier_for(project: dict) -> str:
    """Tier để gọi Flow cho MỘT dự án cụ thể.

    `_current_tier()` trả TIER_ONE khi chưa đọc được gì từ Flow, mà đoán thấp là âm thầm hạ
    trần độ phân giải: tài khoản Ultra đáng lẽ tải ảnh 4K lại nhận 2K, và không có chỗ nào
    trên UI nói vì sao. Chưa đọc được thì tin cột `paygate_tier` đã lưu của dự án hơn — nó
    được `_sync_project_tier` cập nhật mỗi lần mở dự án."""
    tier = await _current_tier()
    return tier if _tier_cache["value"] else (project.get("paygate_tier") or tier)


# ─── Chủ sở hữu dự án (xem agent/studio/accounts.py) ─────────

async def _assert_owner(project: dict) -> None:
    """Chặn khi dự án thuộc tài khoản Flow KHÁC tài khoản đang đăng nhập.

    Bỏ qua khi: dự án chưa có chủ (tạo trước lúc có phân tài khoản), hoặc chưa xác định được
    tài khoản hiện tại — mất extension không được phép khoá người dùng khỏi dữ liệu của họ."""
    owner = project.get("account_id")
    if not owner:
        return
    me = await accounts.current_id()
    if not me or me == owner:
        return
    raise HTTPException(
        403,
        f"Dự án “{project.get('title') or project.get('id')}” thuộc tài khoản "
        f"{await accounts.owner_label(owner)}, nhưng Chrome đang đăng nhập Flow bằng {me}. "
        f"Đăng nhập lại đúng tài khoản đó rồi mở dự án.")


async def _assert_owner_of(project_id: Optional[str]) -> None:
    if not project_id or not await accounts.multi_account():
        return
    row = await db.query_one("SELECT * FROM project WHERE id=?", (project_id,))
    if row:
        await _assert_owner(row)


async def _assert_owner_of_scene(scene_id: Optional[str]) -> None:
    if not scene_id or not await accounts.multi_account():
        return
    row = await db.query_one(
        "SELECT project.* FROM project JOIN scene ON scene.project_id = project.id "
        "WHERE scene.id=?", (scene_id,))
    if row:
        await _assert_owner(row)


# ─── Health / options / settings ────────────────────────────

@router.get("/health")
async def health():
    client = get_flow_client()
    omni = await _safe_omni_health()
    return {
        "status": "ok",
        "extension_connected": client.connected,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "tts": omni,
        # probe=False: /health bị poll 15s/lần, không được phép chờ một vòng WS hỏi extension.
        # Extension tự đẩy identity lúc kết nối; /credits mới là chỗ chịu hỏi lại.
        "account": _account_public(await accounts.current(probe=False)),
    }


async def _safe_omni_health() -> bool:
    try:
        from agent.api.tts import _state
        return bool(_state.get("base_url"))
    except Exception:
        return False


@router.get("/options")
async def options():
    """Lựa chọn cho Settings: models, styles, aspect, tiers, voices, agents."""
    voices, agents = [], []
    try:
        from agent.api.tts import _proxy
        voices = await _proxy("GET", "/api/voices/list", timeout=10.0)
    except Exception:
        voices = []
    try:
        from agent.api.ai_agent import list_agents
        agents = (await list_agents())["agents"]
    except Exception:
        agents = []
    tier = await _current_tier()
    veo_lite_ok = tier in VEO_LITE_TIERS
    return {
        "image_models": list(IMAGE_MODELS.keys()),
        # Người dùng chỉ chọn ENGINE, không chọn model key: Veo i2v tự chọn theo tier + khung
        # hình, còn Omni Flash chọn theo thời lượng clip. (`veo_tiers` giữ lại cho tương thích —
        # nó là danh sách TIER, không phải model, dropdown cũ hiển thị nhầm thành model.)
        "video_models": {"veo_tiers": list(VIDEO_MODELS.keys()),
                          "omni_flash_durations": list(OMNI_FLASH_MODELS.keys())},
        # Thứ tự = thứ tự nên chọn. Veo 3.1 Lite [Lower Priority] đứng đầu vì nó KHÔNG trừ
        # credit; "Lite" bản thường (không có [Lower Priority]) thì VẪN tính tiền — đừng gộp
        # hai cái làm một, model key khác nhau ở đuôi `_low_priority`.
        "video_engines": ([{"value": "veo_lite",
                            "label": "Veo 3.1 Lite [Lower Priority] — 0 credit (Ultra)"}]
                          if veo_lite_ok else [])
                         + [{"value": "", "label": "Tự động (Ultra → Lite miễn phí, còn lại Veo i2v)"},
                            {"value": "veo", "label": "Veo i2v theo tier (tốn credit)"}]
                         + [{"value": s, "label": f"Omni Flash {s}s (r2v)"}
                            for s in OMNI_FLASH_MODELS],
        # UI cần biết tài khoản có Ultra không để giải thích vì sao thiếu lựa chọn Lite.
        # `frame_durations` CHỈ áp dụng cho kiểu nội suy khung đầu/cuối — kiểu "inference"
        # Flow cứng 8s, đừng dựng ô chọn độ dài cho nó.
        "veo_lite": {"available": veo_lite_ok, "tier": tier,
                     "frame_durations": VEO_LITE_FRAME_DURATIONS,
                     "inference_duration": VEO_LITE_DEFAULT_S,
                     "default_duration": VEO_LITE_DEFAULT_S},
        "upscale_models": list(UPSCALE_MODELS.keys()),
        "aspect_ratios": ["VIDEO_ASPECT_RATIO_LANDSCAPE", "VIDEO_ASPECT_RATIO_PORTRAIT"],
        "paygate_tiers": ["PAYGATE_TIER_ONE", "PAYGATE_TIER_TWO"],
        "style_presets": ["Realistic", "Cinematic", "Anime", "3D Pixar", "Watercolor", "Noir"],
        "voices": voices,
        "agents": agents,
        # Prompt ngầm: bản mặc định trong code, để UI hiện làm placeholder của ô `tpl_<key>`
        # (trống = dùng đúng bản này) và cho nút "chép mặc định vào ô để sửa".
        "prompt_defaults": brain.PROMPT_DEFAULTS,
        "prompt_placeholders": brain.PROMPT_PLACEHOLDERS,
    }


@router.get("/fonts")
async def list_fonts():
    """Các font có trên máy để chọn cho caption (vẽ chữ lên video)."""
    fonts = await asyncio.to_thread(assembler.list_fonts)
    return {"fonts": fonts, "current": (await db.kv_get_all()).get("caption_font") or ""}


@router.get("/settings")
async def get_settings():
    return await db.kv_get_all()


@router.put("/settings")
async def put_settings(body: dict):
    for k, v in body.items():
        await db.kv_set(k, v)
    return await db.kv_get_all()


@router.get("/credits")
async def credits():
    """Credit + tài khoản đang đăng nhập.

    Webapp poll endpoint này sẵn rồi, nên nó cũng là chỗ rẻ nhất để báo "đang là ai" và để
    agent cập nhật bảng `account` — không cần thêm một vòng poll riêng."""
    client = _require_extension()
    result = await client.get_credits()
    data = result.get("data", result)
    if isinstance(data, dict):
        acc = await accounts.current()
        data = {**data, "account": _account_public(acc)}
        if acc and data.get("userPaygateTier") and acc.get("paygate_tier") != data["userPaygateTier"]:
            await db.update("account", acc["id"], {"paygate_tier": data["userPaygateTier"]})
            accounts.invalidate()
    return data


def _account_public(acc: Optional[dict]) -> Optional[dict]:
    if not acc:
        return None
    return {k: acc.get(k) for k in ("id", "email", "name", "picture", "paygate_tier")}


@router.get("/accounts")
async def list_accounts():
    """Các tài khoản Flow máy này từng thấy + tài khoản hiện tại (cho UI cảnh báo/đối chiếu)."""
    me = await accounts.current()
    rows = await accounts.list_accounts()
    counts = await db.query_all(
        "SELECT account_id, COUNT(*) AS n FROM project GROUP BY account_id")
    by_acc = {r["account_id"]: r["n"] for r in counts}
    return {
        "current": _account_public(me),
        "accounts": [{**_account_public(r), "projects": by_acc.get(r["id"], 0)} for r in rows],
        "unowned_projects": by_acc.get(None, 0),
    }


# ─── Flow projects (live, for import) ───────────────────────

@router.get("/flow-projects")
async def flow_projects():
    """Project trên Google Flow (có thumbnail) để import."""
    client = _require_extension()
    raw = await client.get_projects()
    return {"projects": _flow_projects(raw)}


def _flow_media_items(raw: dict) -> list[dict]:
    """Pull named media out of a getProjectContents envelope.

    Real schema (data.result.data.json.result):
      - `workflows[]`: each generation, with metadata.displayName (the asset name we
        set) + metadata.primaryMediaId (the image/video to reference).
      - `media[]`: raw media items (name = media id, has `image`/`video`) — used to
        tell whether a workflow's primary media is an image or a video.
      - `externalReferenceMedia[]`: uploaded reference media (mediaId, mediaType,
        workflowDisplayName) — we keep the IMAGE ones (skip AUDIO voice presets).
    """
    data = raw.get("data", raw) if isinstance(raw, dict) else {}
    workflows = _deep_find(data, "workflows") or []
    media_list = _deep_find(data, "media") or []
    ext = _deep_find(data, "externalReferenceMedia") or []

    by_name: dict[str, dict] = {}
    for m in media_list:
        if isinstance(m, dict) and m.get("name"):
            by_name[m["name"]] = m

    def kind_of(mid: str) -> str:
        m = by_name.get(mid) or {}
        return "video" if "video" in m else "image"

    out: list[dict] = []
    seen: set[str] = set()

    for w in workflows:
        if not isinstance(w, dict):
            continue
        meta = w.get("metadata") or {}
        mid = meta.get("primaryMediaId")
        if not mid or mid in seen:
            continue
        seen.add(mid)
        out.append({"media_id": mid, "name": str(meta.get("displayName") or "")[:80],
                    "kind": kind_of(mid)})

    for e in ext:
        if not isinstance(e, dict) or str(e.get("mediaType") or "").upper() != "IMAGE":
            continue
        mid = e.get("mediaId")
        if not mid or mid in seen:
            continue
        seen.add(mid)
        out.append({"media_id": mid, "name": str(e.get("workflowDisplayName") or "")[:80],
                    "kind": "image"})

    return out


def _flow_existing_media_ids(raw: dict) -> set[str]:
    """Every media id that still lives in a Flow project — raw media[] names, each
    workflow's primaryMediaId, and uploaded references. Used to detect deletions: a
    local media id absent from this set was removed on Flow. Includes videos (unlike
    `_flow_media_items`, which is image-only) so video sync works too."""
    data = raw.get("data", raw) if isinstance(raw, dict) else {}
    ids: set[str] = set()
    for m in (_deep_find(data, "media") or []):
        if isinstance(m, dict) and m.get("name"):
            ids.add(m["name"])
    for w in (_deep_find(data, "workflows") or []):
        if isinstance(w, dict):
            mid = (w.get("metadata") or {}).get("primaryMediaId")
            if mid:
                ids.add(mid)
    for e in (_deep_find(data, "externalReferenceMedia") or []):
        if isinstance(e, dict) and e.get("mediaId"):
            ids.add(e["mediaId"])
    return ids


@router.get("/flow-projects/{flow_id}/media")
async def flow_project_media(flow_id: str, images_only: bool = True):
    """Media (ảnh) bên trong một project Flow — để tham chiếu/đồng bộ làm asset."""
    client = _require_extension()
    raw = await client.get_project(flow_id)
    items = _flow_media_items(raw)
    if images_only:
        items = [m for m in items if m["kind"] == "image"]
    return {"media": items}


@router.get("/library/all-media")
async def all_flow_media(images_only: bool = True):
    """Tất cả ảnh trong MỌI project Flow (gắn kèm tên project) — gallery 'All image'."""
    client = _require_extension()
    projects = _flow_projects(await client.get_projects())
    out = []
    for p in projects:
        fid = p.get("flow_project_id")
        if not fid:
            continue
        try:
            items = _flow_media_items(await client.get_project(fid))
        except Exception as e:
            logger.warning("all-media: project %s lỗi: %s", fid, e)
            continue
        for m in items:
            if images_only and m["kind"] != "image":
                continue
            out.append({**m, "project_title": p.get("title") or "", "flow_project_id": fid})
    return {"media": out, "projects": len(projects)}


# ─── Studio projects (DB) ───────────────────────────────────

@router.get("/projects")
async def list_projects():
    """Chỉ dự án của tài khoản Flow đang đăng nhập (+ dự án chưa có chủ).

    Chưa xác định được tài khoản → trả hết kèm `account: null` để webapp hiện cảnh báo, thay
    vì để người dùng nhìn danh sách trống khi extension rớt."""
    me = await accounts.current_id()
    if me and await accounts.multi_account():
        rows = await db.query_all(
            "SELECT * FROM project WHERE account_id IS NULL OR account_id=? "
            "ORDER BY updated_at DESC", (me,))
    else:
        rows = await db.query_all("SELECT * FROM project ORDER BY updated_at DESC")
    return {"projects": rows, "account": me}


@router.post("/projects")
async def create_project(body: CreateProjectRequest):
    client = _require_extension()

    flow_id = body.import_flow_project_id
    thumb = body.import_thumb_media_key
    if not flow_id:
        # Tạo project mới trên Flow
        result = await client.create_project(body.title)
        data = result.get("data", result)
        flow_id = _deep_find(data, "projectId")
        if not flow_id:
            raise HTTPException(502, "Không tạo được project trên Flow")

    pid = db.new_id()
    ts = db.now()
    # Global defaults (Settings §2.7A): used for fields the create form doesn't ask about,
    # so a new project inherits the studio-wide preferences. Order: per-project (form) →
    # global (kv) → hard default.
    kv = await db.kv_get_all()
    row = {
        "id": pid, "title": body.title, "flow_project_id": flow_id,
        "style": (body.style or kv.get("style") or "Realistic"),
        "aspect_ratio": (body.aspect_ratio or kv.get("aspect_ratio")
                         or "VIDEO_ASPECT_RATIO_LANDSCAPE"),
        "paygate_tier": await _current_tier(),   # từ /api/flow/credits, không do user chọn
        # Chủ sở hữu = tài khoản Flow vừa tạo project bên Flow; NULL khi chưa nhận diện được
        # (extension cũ / chưa đăng nhập) — dự án sẽ được nhận về ở lần nhận diện đầu tiên.
        "account_id": await accounts.current_id(),
        "storytelling": 1 if body.storytelling else 0,
        "script_lang": (body.script_lang or "Vietnamese").strip() or "Vietnamese",
        "image_text_lang": (body.image_text_lang or "Vietnamese").strip() or "Vietnamese",
        "thumb_media_key": thumb,
        "status": "draft", "created_at": ts, "updated_at": ts,
        # Prompt ngầm: chép nguyên văn bản mặc định vào dự án mới để ô thiết lập có sẵn text
        # mà sửa, thay vì ô trống chỉ hiện chữ mờ.
        **brain.default_tpl_row(),
    }
    if kv.get("image_model"):
        row["image_model"] = kv["image_model"]
    if kv.get("video_model"):
        row["video_model"] = kv["video_model"]
    for key, cast in (("shot_duration", int), ("voice_id", int), ("tts_speed", float)):
        if kv.get(key) not in (None, ""):
            try:
                row[key] = cast(kv[key])
            except (TypeError, ValueError):
                pass
    await db.insert("project", row)
    return await db.query_one("SELECT * FROM project WHERE id=?", (pid,))


@router.get("/projects/{pid}")
async def get_project(pid: str):
    return await _project_or_404(pid)


@router.patch("/projects/{pid}")
async def update_project(pid: str, body: UpdateProjectRequest):
    await _project_or_404(pid)
    data = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if "storytelling" in data:
        data["storytelling"] = 1 if data["storytelling"] else 0
    if "auto_hires" in data:
        data["auto_hires"] = 1 if data["auto_hires"] else 0
    if "auto_upscale_video" in data:
        data["auto_upscale_video"] = 1 if data["auto_upscale_video"] else 0
    if "bgm_duck" in data:
        data["bgm_duck"] = 1 if data["bgm_duck"] else 0
    if "seed" in data and (data["seed"] is None or data["seed"] <= 0):
        data["seed"] = None   # ≤0 / trống = bỏ khoá seed (ngẫu nhiên)
    if "location_frames" in data:
        data["location_frames"] = 1 if data["location_frames"] == 1 else 4
    if "character_one" in data:
        data["character_one"] = 1 if data["character_one"] else 0
    if "shot_continuity" in data:
        data["shot_continuity"] = 1 if data["shot_continuity"] else 0
    data["updated_at"] = db.now()
    await db.update("project", pid, data)
    return await db.query_one("SELECT * FROM project WHERE id=?", (pid,))


@router.put("/projects/{pid}/cover")
async def set_project_cover(pid: str, body: SetMediaRequest):
    """Đặt ảnh đại diện project. Cập nhật thumb của studio (luôn) + thử set trên Flow (best-effort)."""
    p = await _project_or_404(pid)
    flow_ok = False
    try:
        res = await get_flow_client().change_project_cover(p["flow_project_id"], body.media_id)
        flow_ok = not (isinstance(res, dict) and res.get("error"))
    except Exception as e:
        logger.warning("set cover (flow) failed: %s", e)
    await db.update("project", pid, {"thumb_media_key": body.media_id, "updated_at": db.now()})
    return {"project": await db.query_one("SELECT * FROM project WHERE id=?", (pid,)),
            "flow_updated": flow_ok}


@router.delete("/projects/{pid}")
async def delete_project(pid: str):
    """Xoá dự án kèm TOÀN BỘ dòng con của nó.

    SQLite ở đây không bật khoá ngoại và schema cũng không khai báo ON DELETE CASCADE, nên
    xoá mỗi dòng `project` sẽ để lại scene/shot/entity/history mồ côi — vô hình trong giao
    diện (mọi truy vấn đều join qua project/scene) nhưng vẫn nằm trong DB mãi mãi."""
    await _project_or_404(pid)
    # shot nối với dự án qua scene → phải xoá theo scene_id, không có cột project_id
    await db.execute(
        "DELETE FROM shot WHERE scene_id IN (SELECT id FROM scene WHERE project_id=?)", (pid,))
    for table in ("scene", "entity", "media_history", "asset", "job", "music_track"):
        await db.execute(f"DELETE FROM {table} WHERE project_id=?", (pid,))
    await db.delete("project", pid)
    # dọn media local của project
    folder = media_store.MEDIA_DIR / pid
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    out_folder = assembler.STUDIO_MEDIA_DIR / pid
    if out_folder.exists():
        shutil.rmtree(out_folder, ignore_errors=True)
    return {"ok": True}


@router.post("/maintenance/purge-orphans")
async def purge_orphans(dry_run: bool = True):
    """Dọn các dòng mồ côi do những lần xoá/lưu kịch bản TRƯỚC khi hai lỗi trên được sửa:
    shot không còn scene, và scene/entity/history không còn project. `dry_run=true` (mặc
    định) chỉ đếm, không xoá."""
    counts = {
        "shots": (await db.query_one(
            "SELECT COUNT(*) n FROM shot WHERE scene_id NOT IN (SELECT id FROM scene)"))["n"],
    }
    for table in ("scene", "entity", "media_history", "asset", "job", "music_track"):
        counts[table] = (await db.query_one(
            f"SELECT COUNT(*) n FROM {table} "
            "WHERE project_id IS NULL OR project_id NOT IN (SELECT id FROM project)"))["n"]
    if dry_run:
        return {"dry_run": True, "orphans": counts}
    await db.execute("DELETE FROM shot WHERE scene_id NOT IN (SELECT id FROM scene)")
    for table in ("scene", "entity", "media_history", "asset", "job", "music_track"):
        await db.execute(f"DELETE FROM {table} WHERE project_id IS NULL "
                         f"OR project_id NOT IN (SELECT id FROM project)")
    return {"dry_run": False, "removed": counts}


# ─── Script + scenes ────────────────────────────────────────

async def _project_or_404(pid: str) -> dict:
    row = await db.query_one("SELECT * FROM project WHERE id=?", (pid,))
    if not row:
        raise HTTPException(404, "Project không tồn tại")
    await _assert_owner(row)
    return await _sync_project_tier(row)


async def _sync_project_tier(project: dict) -> dict:
    """Cập nhật `project.paygate_tier` khi tài khoản đã đổi gói.

    Cột này được ghi MỘT LẦN lúc tạo dự án, nên nâng lên Gemini Ultra xong thì mọi dự án cũ
    vẫn mang TIER_ONE — mà chính cột đó quyết định engine video mặc định (Veo Lite 0 credit
    chỉ mở cho TIER_TWO) và được gửi lên Flow làm `userPaygateTier`. Không đồng bộ thì người
    dùng nâng gói mà app vẫn render bằng model tính tiền, không hiểu vì sao.

    `_current_tier()` cache 60s nên đây gần như luôn là một phép so sánh trong bộ nhớ. Chỉ
    đồng bộ khi dự án thuộc tài khoản ĐANG đăng nhập — tier của người khác không suy ra được
    từ phiên hiện tại."""
    tier = await _current_tier()
    # `_current_tier` trả TIER_ONE khi KHÔNG đọc được (extension rớt) — ghi giá trị đoán đó
    # đè lên dự án là hạ cấp nhầm một tài khoản Ultra. Chỉ tin khi đã đọc thật ít nhất một lần.
    if not _tier_cache["value"] or project.get("paygate_tier") == tier:
        return project
    owner = project.get("account_id")
    if owner and owner != await accounts.current_id():
        return project
    await db.update("project", project["id"], {"paygate_tier": tier})
    logger.info("Dự án %s: tier %s → %s", project["id"][:8],
                project.get("paygate_tier"), tier)
    return {**project, "paygate_tier": tier}


async def _purge_shots_of_scene(scene_id: str) -> int:
    """Xoá shot của một scene kèm file media của chúng. Trả về số shot đã xoá."""
    rows = await db.query_all("SELECT * FROM shot WHERE scene_id=?", (scene_id,))
    for sh in rows:
        for p in (sh.get("image_path"), sh.get("image_hires_path"),
                  sh.get("video_path"), sh.get("upscale_path")):
            f = _media_abs(p)
            if f and f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass
        await db.delete("shot", sh["id"])
    return len(rows)


async def _save_scenes(pid: str, script: str) -> tuple[list[dict], dict]:
    """Re-parse script → RECONCILE the project's scenes in place. Returns (rows, summary).

    Trước đây hàm này DELETE sạch scene rồi tạo lại với id mới. Vì `shot.scene_id` trỏ tới id
    cũ (SQLite ở đây không bật khoá ngoại), mọi shot trở thành MỒ CÔI: storyboard trống trơn
    trong khi shot + ảnh vẫn nằm lại trong DB, vô hình và không xoá được qua giao diện. Nên chỉ
    cần sửa một chữ trong kịch bản là mất toàn bộ storyboard.

    Giờ scene được ĐỐI CHIẾU và cập nhật tại chỗ (giữ nguyên id → shot sống sót):
      1. khớp theo heading đã chuẩn hoá;
      2. phần còn lại khớp theo THỨ TỰ, để đổi lời một heading không làm mất shot của nó.
    Scene thật sự biến mất khỏi kịch bản mới bị xoá, kèm shot + file media (nếu không lại đẻ
    ra mồ côi mới).
    """
    parsed = brain.parse_scenes(script)
    old = await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))

    def key(h: str) -> str:
        return re.sub(r"\s+", " ", (h or "").strip()).casefold()

    # ── pass 1: khớp heading giống hệt (ưu tiên scene gần vị trí cũ nhất)
    by_head: dict[str, list[dict]] = {}
    for o in old:
        by_head.setdefault(key(o["heading"]), []).append(o)
    match: dict[int, dict] = {}          # idx scene mới → row scene cũ
    used: set[str] = set()
    for s in parsed:
        cands = [o for o in by_head.get(key(s["heading"]), []) if o["id"] not in used]
        if cands:
            best = min(cands, key=lambda o: abs((o["idx"] or 0) - s["idx"]))
            match[s["idx"]] = best
            used.add(best["id"])

    # ── pass 2: phần dư khớp theo thứ tự (heading bị sửa lời vẫn giữ được shot)
    left_old = [o for o in old if o["id"] not in used]
    left_new = [s for s in parsed if s["idx"] not in match]
    for s, o in zip(left_new, left_old):
        match[s["idx"]] = o
        used.add(o["id"])

    ts = db.now()
    summary = {"kept": 0, "added": 0, "removed": 0, "shots_removed": 0,
               "body_changed": []}
    for s in parsed:
        o = match.get(s["idx"])
        body = s["body"].strip()
        if o:
            if (o.get("action") or "").strip() != body:
                summary["body_changed"].append(s["heading"])
            await db.update("scene", o["id"], {
                "idx": s["idx"], "heading": s["heading"], "slug": s["slug"],
                "action": body})
            summary["kept"] += 1
        else:
            await db.insert("scene", {
                "id": db.new_id(), "project_id": pid, "idx": s["idx"],
                "heading": s["heading"], "slug": s["slug"],
                "action": body, "dialog": None,
                "location_entity_id": None, "source_segment": None,
                "source_start": None, "source_end": None, "created_at": ts,
            })
            summary["added"] += 1

    for o in old:
        if o["id"] not in used:
            summary["shots_removed"] += await _purge_shots_of_scene(o["id"])
            await db.delete("scene", o["id"])
            summary["removed"] += 1

    rows = await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))
    return rows, summary


@router.get("/projects/{pid}/scenes")
async def list_scenes(pid: str):
    await _project_or_404(pid)
    return {"scenes": await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))}


@router.post("/projects/{pid}/script/generate")
async def generate_script(pid: str, body: GenerateScriptRequest):
    p = await _project_or_404(pid)
    result = await brain.run_json(brain.script_from_idea_prompt(
        body.idea, body.target_duration, bool(p["storytelling"]),
        p["style"], p["shot_duration"] or 8, p.get("script_lang") or "Vietnamese"))
    script = result.get("script", "")
    if not script:
        raise HTTPException(502, "AI không trả về script")
    fields = {"idea": body.idea, "target_duration": body.target_duration,
              "script_raw": script, "updated_at": db.now()}
    # culture_hint is auto-detected from the content; don't clobber a user override.
    ch = (result.get("culture_hint") or "").strip()
    if ch and not (p.get("culture_hint") or "").strip():
        fields["culture_hint"] = ch
    await db.update("project", pid, fields)
    scenes, changes = await _save_scenes(pid, script)
    return {"script": script, "scenes": scenes, "changes": changes,
            "estimated_duration": result.get("estimated_duration"),
            "culture_hint": fields.get("culture_hint") or p.get("culture_hint")}


@router.put("/projects/{pid}/script")
async def save_script(pid: str, body: SaveScriptRequest):
    await _project_or_404(pid)
    await db.update("project", pid, {"script_raw": body.script, "updated_at": db.now()})
    scenes, changes = await _save_scenes(pid, body.script)
    return {"script": body.script, "scenes": scenes, "changes": changes}


@router.post("/projects/{pid}/script/chat")
async def script_chat(pid: str, body: ScriptChatRequest):
    p = await _project_or_404(pid)
    result = await brain.run_json(brain.edit_script_prompt(
        p["script_raw"] or "", body.instruction, p["style"],
        p.get("script_lang") or "Vietnamese"))
    script = result.get("script", "")
    if not script:
        raise HTTPException(502, "AI không trả về script")
    await db.update("project", pid, {"script_raw": script, "updated_at": db.now()})
    scenes, changes = await _save_scenes(pid, script)
    return {"script": script, "scenes": scenes, "changes": changes}


# ─── Assets (entities) ──────────────────────────────────────

def _entity_aspect(entity_type: str, project: dict) -> str:
    """Tỉ lệ khung cho ẢNH THAM CHIẾU của một entity — khác tỉ lệ của dự án.

    Người và đồ vật CAO hơn rộng, nên khung ngang phí gần một nửa ảnh vào nền trắng hai bên
    và bóp nhân vật lại nhỏ hơn hẳn. Ít điểm ảnh trên khuôn mặt kéo theo một lỗi khác: model
    bỏ bớt nét, mắt to kiểu anime trôi dần về mắt nhỏ tả thực — đúng thứ nhìn thấy khi đem ref
    đi vẽ storyboard. Khung DỌC cho cùng một lượt sinh nhiều điểm ảnh hơn trên đúng phần cần.

    Bối cảnh thì ngược lại: nó là con phố, phải rộng, và còn phải ăn khớp với khung hình của
    video nên giữ NGANG. Entity kiểu khác thì theo tỉ lệ dự án."""
    if entity_type in ("character", "prop"):
        return "IMAGE_ASPECT_RATIO_PORTRAIT"
    if entity_type == "location":
        return "IMAGE_ASPECT_RATIO_LANDSCAPE"
    return _to_image_aspect(project["aspect_ratio"])


def _to_image_aspect(video_aspect: str) -> str:
    return (video_aspect or "").replace("VIDEO_ASPECT_RATIO_", "IMAGE_ASPECT_RATIO_") \
        or "IMAGE_ASPECT_RATIO_LANDSCAPE"


async def _resolve_image_model(project: dict) -> Optional[str]:
    name = project.get("image_model") or (await db.kv_get_all()).get("image_model")
    if not name:
        return None  # flow_client default (NANO_BANANA_PRO)
    return IMAGE_MODELS.get(name, name)  # name → key, or already a key


def _extract_image_result(payload: dict) -> dict:
    items = payload.get("media") or []
    # An edit echoes the source image back in `media`, so pick the LAST item that actually has
    # a generatedImage (the result comes after any echoed inputs); fall back to the first item.
    media = next((m for m in reversed(items)
                  if isinstance(m, dict) and (m.get("image") or {}).get("generatedImage", {}).get("mediaId")),
                 items[0] if items else {})
    gen = media.get("image", {}).get("generatedImage", {})
    wf = (payload.get("workflows") or [{}])[0]
    return {
        "media_id": gen.get("mediaId") or media.get("name"),
        "workflow_id": wf.get("name"),
        "primary_media_id": wf.get("metadata", {}).get("primaryMediaId"),
        # the gen response already carries the result's direct URL → download it without a
        # separate rate-limited resolve (search only THIS generated item, not the whole payload).
        "url": media_store.direct_url_in(media),
    }


def _image_block_reason(payload: dict) -> Optional[str]:
    """Detect a content-policy / RAI filter in an image response (no media produced)."""
    for key in ("raiFilteredReason", "filteredReason", "raiFilterReason", "blockReason"):
        v = _deep_find(payload, key)
        if v:
            return str(v)
    return None


async def _generate_image_verified(gen_call, store_call, label_for_err: str) -> dict:
    """Run an image generation, VERIFY a media was actually produced + downloaded, and
    retry on Google content-policy blocks / transient failures (video-app spec).

    `gen_call()` → raw Flow response; `store_call(info)` → persisted row (with image_path).
    Raises HTTPException(502) only after all retries fail.
    """
    last = ""
    attempt = 0
    max_attempts = IMAGE_GEN_RETRIES
    while attempt < max_attempts:
        attempt += 1
        res = await gen_call()
        blocked = _is_abuse_block(res)
        if res.get("error"):
            last = str(res["error"])
        else:
            payload = res.get("data", res)
            info = _extract_image_result(payload)
            if info.get("media_id"):
                # The image EXISTS on Flow now. store_call downloads it (with its own retries).
                # Do NOT loop back to gen_call on a download miss — regenerating just spawns
                # duplicate Flow media (the 's04_33 created ×3' bug). Fail hard instead; the
                # media_id is persisted so it can be re-fetched later.
                row = await store_call(info)
                if row.get("image_path"):       # ảnh tạo + tải về OK
                    return row
                raise HTTPException(
                    502, f"Ảnh đã tạo (media {info['media_id'][:8]}) nhưng tải về lỗi "
                         f"({label_for_err}) — thử 'Gen nhanh' lại, không tạo ảnh trùng.")
            last = _image_block_reason(payload) or "Flow không trả media (có thể bị chặn)"
        # No media produced (error / block / filter) → retrying gen is the right move. A block
        # backs off long + earns a few extra tries (retrying fast extends the block).
        if blocked and max_attempts < IMAGE_GEN_RETRIES + ABUSE_EXTRA_RETRIES:
            max_attempts += 1
        logger.warning("%s: tạo ảnh hỏng (lần %d/%d%s): %s", label_for_err, attempt, max_attempts,
                       " · BLOCK, chờ lâu" if blocked else "", last)
        if attempt < max_attempts:
            await asyncio.sleep(random.uniform(*(ABUSE_BLOCK_BACKOFF if blocked else (2, 5))))
    raise HTTPException(502, f"Tạo ảnh thất bại sau {attempt} lần ({label_for_err}): {last}")


async def _gen_candidates(gen_call, project: dict, n: int) -> list[dict]:
    """Generate N candidate images WITHOUT committing them to any record (§13#2 — pick the
    best of several). Each is downloaded to local so the UI can preview it; the chosen one is
    committed later via apply-media. Calls are spaced out and serialized by the single-flight
    lock. Returns [{media_id, primary_media_id, workflow_id, web}]."""
    out: list[dict] = []
    for i in range(n):
        res = await gen_call()
        if res.get("error"):
            logger.warning("candidate %d/%d lỗi: %s", i + 1, n, res["error"])
        else:
            info = _extract_image_result(res.get("data", res))
            mid = info.get("media_id")
            if mid:
                web = await media_store.ensure_local(mid, project["id"])
                if web:
                    out.append({"media_id": mid,
                                "primary_media_id": info.get("primary_media_id") or mid,
                                "workflow_id": info.get("workflow_id"), "web": web})
        if i < n - 1:
            await asyncio.sleep(random.uniform(2, 5))
    if not out:
        raise HTTPException(502, "Không tạo được ảnh ứng viên nào (có thể bị chặn nội dung)")
    return out


async def _entity_or_404(eid: str) -> dict:
    row = await db.query_one("SELECT * FROM entity WHERE id=?", (eid,))
    if not row:
        raise HTTPException(404, "Entity không tồn tại")
    await _assert_owner_of(row.get("project_id"))
    return row


async def _maybe_set_cover(project_id: str, flow_project_id: str, media_id: str):
    """Set the Flow project cover (thumbnail) from the first generated image."""
    if not (media_id and flow_project_id):
        return
    row = await db.query_one("SELECT thumb_media_key FROM project WHERE id=?", (project_id,))
    if row and row.get("thumb_media_key"):
        return
    try:
        await get_flow_client().change_project_cover(flow_project_id, media_id)
    except Exception as e:
        logger.warning("set project cover failed: %s", e)
    await db.update("project", project_id, {"thumb_media_key": media_id})


async def _record_media_history(project_id: str, owner_kind: str, owner_id: str,
                                slot: str, media_id, primary_id, path) -> None:
    """Append a media-history row (§13#8) so an overwritten image/video can be restored.
    Skips a no-op repeat of the current latest entry for this owner+slot."""
    if not (media_id and path):
        return
    last = await db.query_one(
        "SELECT media_id FROM media_history WHERE owner_id=? AND slot=? "
        "ORDER BY created_at DESC LIMIT 1", (owner_id, slot))
    if last and last.get("media_id") == media_id:
        return
    await db.insert("media_history", {
        "id": db.new_id(), "project_id": project_id, "owner_kind": owner_kind,
        "owner_id": owner_id, "slot": slot, "media_id": media_id,
        "primary_media_id": primary_id, "path": path, "created_at": db.now()})


async def _store_media_on_entity(entity: dict, project: dict, info: dict, label: str):
    """Rename on Flow + download local + persist media fields onto the entity."""
    client = get_flow_client()
    if info.get("workflow_id") and project.get("flow_project_id"):
        try:
            await client.change_display_name(
                info["workflow_id"], project["flow_project_id"], label[:60])
        except Exception:
            pass
    web = await media_store.save_media(info.get("media_id"), project["id"], "png", info.get("url"))
    await db.update("entity", entity["id"], {
        "media_id": info.get("media_id"),
        "primary_media_id": info.get("primary_media_id"),
        "workflow_id": info.get("workflow_id"),
        "image_path": web, "updated_at": db.now(),
    })
    await _record_media_history(project["id"], "entity", entity["id"], "image",
                               info.get("media_id"), info.get("primary_media_id"), web)
    await _maybe_set_cover(project["id"], project.get("flow_project_id"), info.get("media_id"))
    return await _entity_or_404(entity["id"])


async def _gen_via_graph(kind: str, row: dict, project: dict, goal: str = "image",
                         batch_id: str | None = None) -> dict | None:
    """⚡ tạo nhanh chạy chính ĐỒ THỊ của shot/entity, thay vì tự dựng một prompt riêng.

    Trước đây hai đường dựng prompt độc lập nhau nên kết quả lệch (node editor có
    header/footer + text người dùng sửa, ⚡ thì không). Nay ⚡ gọi thẳng `run_graph`.

    Chạy ĐÚNG node sinh nối vào Output (`only_node`), không chạy cả đồ thị: các node phía
    trên giữ nguyên kết quả đã có, nên ảnh trung gian người dùng đã ưng không bị roll lại.

    None = shot/entity chưa có đồ thị dùng được → người gọi rơi về đường dựng prompt trực
    tiếp, vốn tương đương đồ thị MẶC ĐỊNH.
    """
    col = "video_graph_json" if (kind == "shot" and goal == "video") else "graph_json"
    raw = row.get(col)
    if not raw:
        return None
    try:
        g = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("graph_json hỏng trên %s %s — dùng đường tạo nhanh cũ", kind, row["id"])
        return None
    node_id = graph_mod.output_gen_node(g)
    if not node_id:
        return None
    try:
        out = await graph_mod.run_graph(
            g, row, {**project, "paygate_tier": await _current_tier()}, kind,
            only_node=node_id, batch_id=batch_id)
    except graph_mod.GraphError as e:
        raise HTTPException(400, f"Chạy đồ thị lỗi: {e}")
    await _save_node_outputs(kind, row["id"], col, g, out.get("node_outputs") or {})
    return out


async def _save_node_outputs(kind: str, row_id: str, col: str,
                             graph: dict, node_outputs: dict) -> None:
    """Ghi `result_*` của lượt vừa chạy vào data từng node rồi lưu lại đồ thị — đúng việc mà
    Node Editor làm sau mỗi lần chạy (applyOutputs).

    Thiếu bước này, ⚡ chạy từ thẻ shot để lại `result_media_id` CŨ trong graph_json: mở lại
    Node Editor thì node bị khoá — hoặc bất kỳ node phía dưới nào — sẽ tái dùng đúng tấm ảnh
    cũ đó thay vì bản ⚡ vừa tạo."""
    if not node_outputs:
        return
    touched = False
    for n in (graph.get("nodes") or []):
        v = node_outputs.get(n.get("id")) if isinstance(n, dict) else None
        if not v or not v.get("web"):
            continue
        n.setdefault("data", {}).update({
            "result_media_id": v.get("media_id"),
            "result_web": v.get("web"),
            "result_ext": v.get("ext", "png"),
        })
        touched = True
    if not touched:
        return
    table = "shot" if kind == "shot" else "entity"
    await db.update(table, row_id, {col: json.dumps(graph)})


async def _generate_entity_image(entity: dict, project: dict, batch_id: str = None) -> dict:
    """Sinh ảnh tham chiếu cho MỘT asset.

    `batch_id` giống hệt `_generate_frame_image`: có nó thì lượt gọi nhập vào batch Flow
    chung và đi KHÔNG qua khoá single-flight (serialize=False), nhờ vậy một nhóm asset bắn
    cùng lúc mới thật sự chồng lên nhau. Bỏ trống = một mình một lượt như cũ.
    """
    out = await _gen_via_graph("entity", entity, project, batch_id=batch_id)
    if out:
        return await _commit_entity_media(entity, project, out["media_id"], out.get("path"))
    client = _require_extension()
    body = brain.ref_image_prompt(
        entity["type"], entity["name"],
        entity.get("description") or entity.get("ref_prompt") or "", project)
    prompt = brain.compose_prompt(project, body,
                                  **graph_mod.prompt_wrap(entity.get("graph_json"), project))
    aspect = _entity_aspect(entity["type"], project)
    model = await _resolve_image_model(project)
    tier = await _current_tier()
    row = await _generate_image_verified(
        gen_call=lambda: client.generate_images(
            prompt=prompt, project_id=project["flow_project_id"], aspect_ratio=aspect,
            user_paygate_tier=tier, image_model=model, seed=project.get("seed"),
            batch_id=batch_id, serialize=batch_id is None),
        store_call=lambda info: _store_media_on_entity(
            entity, project, info, f"{entity['type']}_{entity['name']}"),
        label_for_err=f"asset {entity['name']}")
    # A location's reference image is ONE 2x2 grid of four angles. Overlay the position
    # labels on the quadrants for management (display only; the underlying media stays clean).
    # Ở chế độ một ảnh (location_frames == 1) không có ô nào để dán nhãn.
    if (entity["type"] == "location" and row.get("media_id")
            and brain.location_frames(project) == 4):
        try:
            await _label_location_grid(row, project)
            row = await _entity_or_404(entity["id"])
        except Exception as ex:  # noqa: BLE001
            logger.warning("location grid labelling failed for %s: %s", entity["name"], ex)
    return row


async def _label_location_grid(entity: dict, project: dict) -> None:
    """Overlay the four position labels (Toàn cảnh / Góc ngược / Trên cao / Cận cảnh) on the
    location's 2x2 grid quadrants → a labeled DISPLAY copy set as image_path. The original
    grid (media_id) stays unlabeled and is what shots reference."""
    web = entity.get("image_path")
    if not web:
        return
    src = media_store.MEDIA_DIR / web.replace("/media/", "", 1)
    if not src.exists():
        return
    # Include the media_id in the labeled filename so a REGENERATED grid gets a NEW url. A fixed
    # name (loc_<eid>_labeled.png) kept the same url across regenerations, so the browser served
    # the CACHED old image while history (media_id-named) showed the fresh one.
    mid = entity.get("media_id") or "x"
    out_dir = media_store.MEDIA_DIR / project["id"]
    for old in out_dir.glob(f"loc_{entity['id']}_*labeled.png"):   # clean prior labeled copies
        try:
            old.unlink()
        except OSError:
            pass
    out_rel = f"{project['id']}/loc_{entity['id']}_{mid}_labeled.png"
    out_abs = media_store.MEDIA_DIR / out_rel
    ok = await asyncio.to_thread(
        assembler.label_quadrants, src, out_abs, brain.LOCATION_GRID_LABELS,
        assembler._caption_font())
    if ok:
        await db.update("entity", entity["id"],
                        {"image_path": f"/media/{out_rel}", "updated_at": db.now()})


@router.get("/projects/{pid}/entities")
async def list_entities(pid: str):
    await _project_or_404(pid)
    return {"entities": await db.query_all(
        "SELECT * FROM entity WHERE project_id=? ORDER BY type, created_at", (pid,))}


@router.get("/library/entities")
async def library_entities(exclude_project: Optional[str] = None):
    """Mọi asset (đã có ảnh) trên TẤT CẢ dự án — để dùng chung asset giữa các project.

    Một dự án có thể đóng vai 'thư viện' chứa nhân vật/bối cảnh/đạo cụ; dự án khác chỉ
    việc import lại entity có sẵn (không phải gen lại).

    Chỉ lấy asset của dự án thuộc tài khoản đang đăng nhập: import một entity của account
    khác sẽ kéo theo `media_id` mà token hiện tại không resolve nổi.
    """
    me = await accounts.current_id()
    scope = "AND (p.account_id IS NULL OR p.account_id = ?) " if me and await accounts.multi_account() else ""
    params: tuple = ()
    if exclude_project:
        params += (exclude_project,)
    if scope:
        params += (me,)
    rows = await db.query_all(
        "SELECT e.*, p.title AS project_title FROM entity e "
        "JOIN project p ON e.project_id = p.id "
        "WHERE e.media_id IS NOT NULL "
        + ("AND e.project_id != ? " if exclude_project else "")
        + scope
        # Newer projects first: later videos tend to reference the most recent work, so surface
        # the freshest project's assets at the top. NULL created_at (legacy rows) sinks to the end.
        + "ORDER BY (p.created_at IS NULL), p.created_at DESC, p.title, e.type, e.name",
        params)
    return {"entities": rows}


@router.post("/projects/{pid}/entities/import")
async def import_entity(pid: str, body: ImportEntityRequest):
    """Sao chép một entity từ dự án khác vào dự án này, GIỮ ảnh sẵn có (không gen lại)."""
    await _project_or_404(pid)
    src = await db.query_one("SELECT * FROM entity WHERE id=?", (body.source_entity_id,))
    if not src:
        raise HTTPException(404, "Entity nguồn không tồn tại")
    # tải ảnh về thư mục project hiện tại (an toàn nếu dự án nguồn bị xoá); fallback path cũ
    web = None
    if src.get("media_id"):
        try:
            web = await media_store.ensure_local(src["media_id"], pid)
        except Exception:
            web = None
    web = web or src.get("image_path")
    eid = db.new_id()
    ts = db.now()
    await db.insert("entity", {
        "id": eid, "project_id": pid, "type": src.get("type", "character"),
        "name": src.get("name", ""), "description": src.get("description", ""),
        "ref_prompt": src.get("ref_prompt", ""),
        "media_id": src.get("media_id"), "primary_media_id": src.get("primary_media_id"),
        "workflow_id": src.get("workflow_id"), "image_path": web,
        "created_at": ts, "updated_at": ts})
    return await _entity_or_404(eid)


@router.post("/projects/{pid}/entities/import-media")
async def import_flow_media(pid: str, body: ImportMediaRequest):
    """Tạo entity mới từ một media_id Flow bất kỳ (đồng bộ asset từ project trên Flow)."""
    await _project_or_404(pid)
    web = await media_store.ensure_local(body.media_id, pid)
    if not web:
        raise HTTPException(404, "media_id không hợp lệ hoặc không tồn tại trên Flow")
    eid = db.new_id()
    ts = db.now()
    await db.insert("entity", {
        "id": eid, "project_id": pid, "type": body.type or "character",
        "name": (body.name or "Flow asset")[:80], "description": body.description,
        "ref_prompt": "", "media_id": body.media_id, "primary_media_id": body.media_id,
        "image_path": web, "created_at": ts, "updated_at": ts})
    return await _entity_or_404(eid)


@router.post("/projects/{pid}/entities/extract")
async def extract_entities(pid: str, replace: bool = False):
    """Trích entity từ kịch bản. `replace=true` → XOÁ toàn bộ entity hiện tại (kèm ảnh)
    rồi trích lại từ đầu; mặc định chỉ thêm entity mới (bỏ qua tên đã có)."""
    p = await _project_or_404(pid)
    if not p.get("script_raw"):
        raise HTTPException(400, "Chưa có kịch bản để trích entity")
    items = await brain.run_json(brain.entity_extract_prompt(p["script_raw"]))
    if not isinstance(items, list):
        raise HTTPException(502, "AI không trả về danh sách entity")
    if replace:
        for r in await db.query_all(
                "SELECT id, image_path FROM entity WHERE project_id=?", (pid,)):
            await db.delete("entity", r["id"])
            if r.get("image_path"):
                f = media_store.MEDIA_DIR / r["image_path"].replace("/media/", "", 1)
                f.unlink(missing_ok=True)
    # tránh trùng tên (đã có)
    existing = {r["name"].lower() for r in await db.query_all(
        "SELECT name FROM entity WHERE project_id=?", (pid,))}
    ts = db.now()
    added = 0
    for it in items:
        name = (it.get("name") or "").strip()
        if not name or name.lower() in existing:
            continue
        await db.insert("entity", {
            "id": db.new_id(), "project_id": pid,
            "type": it.get("type", "character"), "name": name,
            "description": it.get("description", ""),
            "ref_prompt": it.get("ref_prompt", ""),
            "created_at": ts, "updated_at": ts})
        existing.add(name.lower())
        added += 1

    # Every scene heading names a LOCATION (heading minus the INT./EXT. prefix minus the
    # trailing time-of-day). The AI extractor often misses some of these, so harvest them
    # deterministically: any heading-location not already an entity becomes a location entity.
    headings = [r["heading"] for r in await db.query_all(
        "SELECT heading FROM scene WHERE project_id=? ORDER BY idx", (pid,))]
    if not headings:                                  # scenes not parsed yet → read the script
        headings = [s["heading"] for s in brain.parse_scenes(p["script_raw"])]
    seen_loc: set[str] = set()
    for h in headings:
        loc = _location_from_heading(h)
        key = _norm(loc)
        if not loc or key in seen_loc or loc.lower() in existing:
            continue
        seen_loc.add(key)
        await db.insert("entity", {
            "id": db.new_id(), "project_id": pid,
            "type": "location", "name": loc,
            "description": "", "ref_prompt": "",
            "created_at": ts, "updated_at": ts})
        existing.add(loc.lower())
        added += 1
    return {"added": added, "entities": await db.query_all(
        "SELECT * FROM entity WHERE project_id=? ORDER BY type, created_at", (pid,))}


@router.post("/projects/{pid}/entities")
async def add_entity(pid: str, body: AddEntityRequest):
    await _project_or_404(pid)
    ts = db.now()
    eid = db.new_id()
    await db.insert("entity", {
        "id": eid, "project_id": pid, "type": body.type, "name": body.name,
        "description": body.description, "ref_prompt": body.ref_prompt,
        "created_at": ts, "updated_at": ts})
    return await _entity_or_404(eid)


@router.patch("/entities/{eid}")
async def update_entity(eid: str, body: UpdateEntityRequest):
    await _entity_or_404(eid)
    data = body.model_dump(exclude_none=True)
    data["updated_at"] = db.now()
    await db.update("entity", eid, data)
    return await _entity_or_404(eid)


@router.delete("/entities/{eid}")
async def delete_entity(eid: str):
    row = await _entity_or_404(eid)
    await db.delete("entity", eid)
    if row.get("image_path"):
        f = media_store.MEDIA_DIR / row["image_path"].replace("/media/", "", 1)
        if f.exists():
            f.unlink(missing_ok=True)
    return {"ok": True}


@router.post("/entities/{eid}/link")
async def link_entity_media(eid: str, body: LinkEntityRequest):
    """Trỏ ảnh/media_id của một asset (dự án bất kỳ) vào entity NÀY, giữ nguyên tên.

    Dùng khi entity hiện tại (vd 'anh A', prompt đều dùng {anh A}) thực ra là cùng
    nhân vật với 'Nguyễn Văn A' ở dự án khác — chỉ mượn ảnh + media_id, không đổi tên,
    nên các prompt cũ vẫn bind đúng.
    """
    entity = await _entity_or_404(eid)
    project = await _project_or_404(entity["project_id"])
    src = await db.query_one("SELECT * FROM entity WHERE id=?", (body.source_entity_id,))
    if not src or not src.get("media_id"):
        raise HTTPException(404, "Asset nguồn không hợp lệ (chưa có ảnh)")
    web = None
    try:
        web = await media_store.ensure_local(src["media_id"], project["id"])
    except Exception:
        web = None
    web = web or src.get("image_path")
    await db.update("entity", eid, {
        "media_id": src["media_id"],
        "primary_media_id": src.get("primary_media_id") or src["media_id"],
        "workflow_id": src.get("workflow_id"),
        "image_path": web, "updated_at": db.now()})
    return await _entity_or_404(eid)


@router.post("/entities/{eid}/generate")
async def generate_entity(eid: str):
    entity = await _entity_or_404(eid)
    project = await _project_or_404(entity["project_id"])
    return await _generate_entity_image(entity, project)


@router.put("/entities/{eid}/image")
async def set_entity_image(eid: str, body: SetMediaRequest):
    """Gán ảnh chính từ media_id có sẵn (xác thực tồn tại trên Flow → tải local)."""
    entity = await _entity_or_404(eid)
    project = await _project_or_404(entity["project_id"])
    web = await media_store.ensure_local(body.media_id, project["id"])
    if not web:
        raise HTTPException(404, "media_id không hợp lệ hoặc không tồn tại trên Flow")
    await db.update("entity", eid, {
        "media_id": body.media_id, "primary_media_id": body.media_id,
        "image_path": web, "updated_at": db.now()})
    return await _entity_or_404(eid)


@router.post("/projects/{pid}/assets/generate-all")
async def generate_all_assets(pid: str, force: bool = False):
    """✦ Auto gen ảnh cho asset CHƯA có ảnh → job nền (§9). Trả job_id ngay.

    Chạy theo BATCH y như storyboard: mỗi nhóm IMAGE_BATCH_SIZE asset bắn song song trong
    một batch id của Flow, giãn nhau bằng stagger rồi nghỉ cooldown giữa các nhóm. Trước
    đây job này đi tuần tự kèm 2-6s chờ giữa mỗi asset, nên 20 asset mất hàng chục phút
    trong khi ảnh storyboard cùng cỡ đã xong từ lâu — cùng một loại việc, không có lý do
    để hai bên chạy hai tốc độ.
    """
    project = await _project_or_404(pid)
    rows = await db.query_all("SELECT * FROM entity WHERE project_id=?", (pid,))
    todo = [e for e in rows if force or not e.get("image_path")]

    async def _worker(e, batch_id):
        await _generate_entity_image(e, project, batch_id=batch_id)

    job = get_job_manager().start(
        project_id=pid, type_="assets", items=todo, worker=_worker,
        label=f"Sinh ảnh asset ({len(todo)})",
        throttle=IMAGE_BATCH_COOLDOWN, batch_size=IMAGE_BATCH_SIZE,
        stagger=IMAGE_BATCH_STAGGER,
        item_label=lambda e: e.get("name") or e["id"])
    return {"job_id": job.id, "total": len(todo)}


# ─── Storyboard (shots = frames) ────────────────────────────

class AutofillRequest(BaseModel):
    n_frames: Optional[int] = None


class BuildBeatsRequest(BaseModel):
    language: Optional[str] = None   # None → dùng script_lang của dự án
    # measure=True → TTS each scene now for the real audio length (needs OmniVoice up);
    # False → estimate from word count (no quota), real length fitted later.
    measure: bool = True


# ≈2.5 spoken words/second (video-app.md §5.2) → estimate a narration's length without
# burning TTS quota. Real durations replace this when narration is generated / at assemble.
def _estimate_narration_secs(text: str) -> float:
    """Seconds this text takes to narrate, from the voice's measured words/sec (brain
    .WORDS_PER_SEC). Used to size beats and as the timing fallback when TTS/alignment is off."""
    words = len((text or "").split())
    return max(1.0, round(words / brain.WORDS_PER_SEC, 2))


class UpdateShotRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ref_entity_ids: Optional[list[str]] = None
    visual_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    duration: Optional[int] = None
    video_model: Optional[str] = None


def _merge_short_beats(beats: list[dict]) -> list[dict]:
    """Fold beats whose spoken slice is shorter than ~half the shot minimum into a neighbour.

    The AI sometimes returns a beat that is a single fragment ("của anh.", "chín."), and
    chunk_by_duration can only pack WITHIN a beat — so those became sub-second shots, each
    costing a generated image. Merge them into the PREVIOUS beat (or the next, for the first
    one), keeping that neighbour's framing/refs, unless doing so would make an over-long shot.
    Spoken slices are concatenated in order, so the narration stays verbatim and complete."""
    if len(beats) <= 1:
        return beats
    floor_w = max(2, round(MIN_SHOT_SECS * brain.WORDS_PER_SEC * 0.5))
    ceil_w = round(MAX_SHOT_SECS * brain.WORDS_PER_SEC * 1.4)

    def wc(b: dict) -> int:
        return len((b.get("_say") or "").split())

    out: list[dict] = []
    for b in beats:
        if out and wc(b) < floor_w and wc(out[-1]) + wc(b) <= ceil_w:
            out[-1]["_say"] = f"{out[-1].get('_say') or ''} {b.get('_say') or ''}".strip()
        else:
            out.append(dict(b))
    # the FIRST beat has no previous one to fold into — pull it into the second instead
    if len(out) > 1 and wc(out[0]) < floor_w and wc(out[0]) + wc(out[1]) <= ceil_w:
        out[1]["_say"] = f"{out[0].get('_say') or ''} {out[1].get('_say') or ''}".strip()
        out.pop(0)
    return out


async def _scene_or_404(sid: str) -> dict:
    row = await db.query_one("SELECT * FROM scene WHERE id=?", (sid,))
    if not row:
        raise HTTPException(404, "Scene không tồn tại")
    await _assert_owner_of(row.get("project_id"))
    return row


async def _shot_or_404(sid: str) -> dict:
    row = await db.query_one("SELECT * FROM shot WHERE id=?", (sid,))
    if not row:
        raise HTTPException(404, "Shot không tồn tại")
    await _assert_owner_of_scene(row.get("scene_id"))
    return row


async def _scene_project(scene: dict) -> dict:
    return await _project_or_404(scene["project_id"])


async def _next_shot_idx(scene_id: str) -> int:
    row = await db.query_one(
        "SELECT MAX(idx) AS m FROM shot WHERE scene_id=?", (scene_id,))
    return (row["m"] + 1) if row and row["m"] is not None else 0


async def _build_frame_references(shot: dict, scene: dict) -> list[dict]:
    """Resolve shot ref entities (+ scene location) → references list, location first, capped at
    MAX_FRAME_REFS. Flow rejects a generate request with more than 8 reference images (HTTP 400),
    so we keep the location + the most relevant characters/props and drop the overflow."""
    try:
        ids = json.loads(shot.get("ref_entity_ids") or "[]")
    except (json.JSONDecodeError, TypeError):
        ids = []
    if scene.get("location_entity_id"):
        ids = [scene["location_entity_id"]] + [i for i in ids if i != scene["location_entity_id"]]
    refs = []
    seen = set()
    rows = await db.query_all(
        "SELECT * FROM entity WHERE project_id=?", (scene["project_id"],))
    by_id = {r["id"]: r for r in rows}
    # location-type first
    ordered = sorted(ids, key=lambda i: 0 if by_id.get(i, {}).get("type") == "location" else 1)
    for i in ordered:
        e = by_id.get(i)
        if e and e.get("media_id") and e["media_id"] not in seen:
            refs.append({"handle": e["name"], "media_id": e["media_id"]})
            seen.add(e["media_id"])
        if len(refs) >= MAX_FRAME_REFS:
            break
    return refs


async def _store_media_on_shot(shot: dict, project: dict, info: dict,
                               kind: str, label: str):
    """Rename on Flow + download + persist image_*/video_* on the shot."""
    client = get_flow_client()
    if info.get("workflow_id") and project.get("flow_project_id"):
        try:
            await client.change_display_name(
                info["workflow_id"], project["flow_project_id"], label[:60])
        except Exception:
            pass
    ext = "png" if kind == "image" else "mp4"
    # Prefer the direct URL from the gen response (no rate-limited resolve); fall back to
    # get_direct_media with retries. This stops a concurrent batch from tripping Flow's media
    # rate limit and leaving image_path NULL → regenerate (the 's04_33 created ×3' bug).
    web = await media_store.save_media(info.get("media_id"), project["id"], ext, info.get("url"))
    fields = {
        f"{kind}_media_id": info.get("media_id"),
        f"{kind}_primary_id": info.get("primary_media_id"),
        f"{kind}_workflow_id": info.get("workflow_id"),
        f"{kind}_path": web, "updated_at": db.now(),
    }
    await db.update("shot", shot["id"], fields)
    await _record_media_history(project["id"], "shot", shot["id"], kind,
                               info.get("media_id"), info.get("primary_media_id"), web)
    if kind == "image":
        await _maybe_set_cover(project["id"], project.get("flow_project_id"), info.get("media_id"))
        # Bản HD vừa lưu chỉ đủ để xem trong app. Nếu dự án bật "tự tải ảnh 2K/4K", kéo thêm
        # bản hi-res ngay (best-effort — hỏng thì chỉ ghi log, ảnh HD đã có).
        if web and project.get("auto_hires"):
            await hires.auto_upscale_shot(
                {**shot, "image_media_id": info.get("media_id")}, project,
                await _current_tier_for(project))
    return await _shot_or_404(shot["id"])


async def _generate_frame_image(shot: dict, batch_id: str = None) -> dict:
    """Generate one storyboard frame. When `batch_id` is set the call joins that shared Flow
    batch and is sent WITHOUT the single-flight lock (serialize=False) so a group of ≤4 frames
    fired together actually overlaps — used by the batched generate-all job."""
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    out = await _gen_via_graph("shot", shot, project, "image", batch_id=batch_id)
    if out:
        return await _commit_shot_media(shot, scene, project, out["media_id"], "png",
                                        out.get("path"))
    client = _require_extension()
    refs = await _build_frame_references(shot, scene)
    prompt = brain.compose_prompt(
        project, shot.get("description") or shot.get("title") or "", single_frame=True,
        **graph_mod.prompt_wrap(shot.get("graph_json"), project))
    aspect = _to_image_aspect(project["aspect_ratio"])
    model = await _resolve_image_model(project)
    tier = await _current_tier()
    return await _generate_image_verified(
        gen_call=lambda: client.generate_images(
            prompt=prompt, project_id=project["flow_project_id"], aspect_ratio=aspect,
            user_paygate_tier=tier, references=refs or None, image_model=model,
            # Mô tả shot là chữ NGƯỜI DÙNG viết: gọi lại {Nhân vật} ba bốn lần trong một
            # đoạn là chuyện thường, mà mỗi lần nhắc không dedupe là một reference part
            # trùng → Flow trả 400 INVALID_ARGUMENT (xem CLAUDE.md).
            dedupe_refs=True,
            seed=project.get("seed"), batch_id=batch_id, serialize=batch_id is None),
        store_call=lambda info: _store_media_on_shot(
            shot, project, info, "image", f"s{scene['idx']+1:02d}_{shot['idx']+1:02d}_img"),
        label_for_err=f"frame {shot.get('title') or shot['id'][:6]}")


@router.get("/scenes/{sid}/shots")
async def list_scene_shots(sid: str):
    await _scene_or_404(sid)
    return {"shots": await db.query_all(
        "SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,))}


@router.get("/projects/{pid}/shots")
async def list_project_shots(pid: str):
    await _project_or_404(pid)
    return {"shots": await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? ORDER BY sc.idx, sh.idx", (pid,))}


# ─── Shot reference resolution (location + entities actually in the prompt) ──

_BRACE_RE = re.compile(r"\{([^{}]+)\}")
_HEADING_PREFIX_RE = re.compile(r"^\s*(INT\.?/?EXT\.?|INT\.|EXT\.|NỘI\.|NGOẠI\.|I/E\.)\s*", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _brace_names(text: str) -> set[str]:
    """Entity names the AI actually wrapped in {curly braces} (the binding tokens)."""
    return {m.strip() for m in _BRACE_RE.findall(text or "") if m.strip()}


_ALIAS_RE = re.compile(r"^(.*?)\s*\((.*)\)\s*$")


def _alias_keys(name: str) -> list[str]:
    """Normalized alias lookup keys for a name with a parenthetical, so {short} and {full}
    both resolve to the entity (e.g. 'Hùng (Phạm Trọng Hùng)' → 'hùng', 'phạm trọng hùng')."""
    m = _ALIAS_RE.match((name or "").strip())
    if not m:
        return []
    out = []
    if m.group(1).strip():
        out.append(_norm(m.group(1)))
    if m.group(2).strip():
        out.append(_norm(m.group(2)))
    return out


def _index_by_name(rows: list[dict]) -> dict:
    """Index entities by normalized name AND aliases (parenthetical short/full names). The
    verbatim full name wins; aliases never shadow a real entity name."""
    idx = {_norm(r["name"]): r for r in rows}
    for r in rows:
        for k in _alias_keys(r["name"]):
            idx.setdefault(k, r)
    return idx


# Time-of-day tokens that may trail a scene heading (VN + EN). The LOCATION is the heading
# minus the INT./EXT. prefix minus these trailing time segments — NOT just the first segment
# (a location can itself contain " - ", e.g. 'KHU 4 - LỐI ĐI KỸ THUẬT - NGÀY').
_TIME_TOKENS = {
    "ngày", "đêm", "sáng", "trưa", "chiều", "tối", "khuya", "rạng đông", "rạng sáng",
    "bình minh", "hoàng hôn", "đêm khuya", "sáng sớm", "chạng vạng", "nửa đêm",
    "ngày/đêm", "đêm/ngày", "liên tục", "sau đó", "lát sau", "cùng lúc", "hồi tưởng",
    "day", "night", "morning", "afternoon", "evening", "noon", "dusk", "dawn",
    "midnight", "continuous", "later", "moments later", "sunset", "sunrise",
}


def _location_from_heading(heading: str) -> str:
    """'INT. BẾP CỦA THIÊN ÂN - NGÀY' → 'BẾP CỦA THIÊN ÂN'; 'EXT. KHU 4 - LỐI ĐI KỸ THUẬT -
    NGÀY' → 'KHU 4 - LỐI ĐI KỸ THUẬT'. Strip the INT./EXT. prefix, then drop TRAILING
    time-of-day segments (only the time is removed; an internal ' - ' in the place stays)."""
    h = _HEADING_PREFIX_RE.sub("", (heading or "").strip())
    parts = [p.strip() for p in re.split(r"\s+[-–—]\s+", h) if p.strip()]
    while len(parts) > 1 and _norm(parts[-1]) in _TIME_TOKENS:
        parts.pop()
    return " - ".join(parts).strip()


def _match_location_entity(heading: str, locations: list[dict]) -> Optional[dict]:
    """The location entity named in the scene heading (exact, else containment)."""
    target = _norm(_location_from_heading(heading))
    if not target or not locations:
        return None
    for e in locations:
        if _norm(e["name"]) == target:
            return e
    for e in locations:
        n = _norm(e["name"])
        if n and (n in target or target in n):
            return e
    return None


def _first_location_id(frames: list[dict], by_name: dict) -> Optional[str]:
    """Fallback when the heading matches no location entity: the first location the AI named."""
    for f in frames:
        text = " ".join(filter(None, [f.get("description"), f.get("visual_prompt"), f.get("motion_prompt")]))
        for n in (set(f.get("ref_entity_names") or []) | _brace_names(text)):
            e = by_name.get(_norm(n))
            if e and e["type"] == "location":
                return e["id"]
    return None


def _resolve_shot_refs(text: str, ref_names, by_name: dict, scene_loc_id: Optional[str]) -> list[str]:
    """A shot references EXACTLY one location (the scene's) plus every NON-location entity
    actually named in the prompt ({braces}) or ref_entity_names. Any other location is dropped
    so a shot never mixes places, and an entity mentioned in the prompt is always referenced."""
    names = set(ref_names or []) | _brace_names(text)
    other_ids: list[str] = []
    for n in names:
        e = by_name.get(_norm(n))
        if e and e["type"] != "location" and e["id"] not in other_ids:
            other_ids.append(e["id"])
    return ([scene_loc_id] if scene_loc_id else []) + other_ids


async def _scene_arc(scene: dict, project: dict) -> str:
    """Khối HÌNH DÁNG SCENE + CHUYỂN CẢNH cho scene này, bốc theo VỊ TRÍ của nó trong dự án.

    Ba đường viết shot (autofill storyboard, tách beat, đổi góc máy) đều chạy MỖI SCENE MỘT
    LƯỢT GỌI AI riêng, và lượt đó chỉ nhìn thấy đúng scene của nó. Nên cả hai thứ ở đây đều
    phải bơm từ ngoài vào: model không tự biết 11 scene khác đã dùng công thức nào (→ scene
    nào cũng ra wide→full→medium→close), cũng không biết cảnh trước kết thúc bằng hình gì để
    mà nối tiếp. Xem `brain.scene_arc`.

    Lấy VỊ TRÍ trong danh sách đã sắp xếp chứ không lấy `scene.idx`: idx có thể thủng lỗ sau
    khi xoá scene, mà lối RA của scene k phải trỏ đúng cùng một mục với lối VÀO của scene k+1
    — lệch một nấc là hai nửa của cùng một cú cắt không khớp nhau nữa."""
    if not brain.shot_continuity(project):
        return ""
    rows = await db.query_all(
        "SELECT id, heading FROM scene WHERE project_id=? ORDER BY idx", (project["id"],))
    pos = next((i for i, r in enumerate(rows) if r["id"] == scene["id"]), None)
    if pos is None:
        return ""
    return brain.scene_arc(
        project, pos, len(rows),
        prev_heading=(rows[pos - 1]["heading"] if pos > 0 else None),
        next_heading=(rows[pos + 1]["heading"] if pos + 1 < len(rows) else None),
        prev_tail=(await _edge_shot(rows[pos - 1]["id"], last=True) if pos > 0 else ""),
        next_head=(await _edge_shot(rows[pos + 1]["id"], last=False)
                   if pos + 1 < len(rows) else ""))


async def _edge_shot(scene_id: str, last: bool) -> str:
    """Khung ĐẦU hoặc CUỐI của một scene, dạng chữ, để đưa cho lượt viết scene bên cạnh.

    Cú chuyển cảnh nào dùng được là chuyện HÌNH HỌC — nhân vật đứng đâu, quay hướng nào, máy
    vừa đi thế nào, chỗ đó có gì — mà chỉ đọc khung thật mới biết. Chọn kiểu chuyển thì code
    làm được (để hai scene liền nhau khỏi trùng), còn thẩm định nó có khả thi không thì phải
    là model. Nên khung thật đi kèm vào prompt; xem `brain.scene_arc`.

    Kèm cả `motion_prompt` vì nửa `out` của cú chuyển nằm ở đó: khung tĩnh chỉ cho biết clip
    BẮT ĐẦU ra sao, còn cảnh sau cần biết clip trước KẾT THÚC ra sao."""
    rows = await db.query_all(
        "SELECT description, motion_prompt FROM shot WHERE scene_id=? ORDER BY idx", (scene_id,))
    if not rows:
        return ""
    s = rows[-1] if last else rows[0]
    parts = [(s.get("description") or "").strip()[:600]]
    if s.get("motion_prompt"):
        parts.append("Motion: " + s["motion_prompt"].strip()[:400])
    return "\n".join(p for p in parts if p)


@router.post("/scenes/{sid}/storyboard/autofill")
async def autofill_storyboard(sid: str, body: AutofillRequest):
    scene = await _scene_or_404(sid)
    project = await _project_or_404(scene["project_id"])
    erows = await db.query_all(
        "SELECT id, name, type, description FROM entity WHERE project_id=?", (scene["project_id"],))
    by_name = _index_by_name(erows)
    # The scene's location is fixed by its heading — every shot uses ONLY this place.
    scene_loc = _match_location_entity(scene["heading"], [r for r in erows if r["type"] == "location"])
    scene_loc_id = scene_loc["id"] if scene_loc else None
    frames = await brain.run_json(brain.storyboard_autofill_prompt(
        scene["heading"], scene.get("action") or "", erows, project["style"], body.n_frames,
        location=(scene_loc["name"] if scene_loc else None),
        arc=await _scene_arc(scene, project),
        **_engine_kw(project)))
    if not isinstance(frames, list):
        raise HTTPException(502, "AI không trả về danh sách frame")
    if not scene_loc_id:                      # heading matched no entity → use the AI's pick
        scene_loc_id = _first_location_id(frames, by_name)
    await db.execute("DELETE FROM shot WHERE scene_id=?", (sid,))
    ts = db.now()
    for i, f in enumerate(frames):
        text = " ".join(filter(None, [f.get("description"), f.get("visual_prompt"), f.get("motion_prompt")]))
        ref_ids = _resolve_shot_refs(text, f.get("ref_entity_names"), by_name, scene_loc_id)
        await db.insert("shot", {
            "id": db.new_id(), "scene_id": sid, "idx": i,
            "title": f.get("title", f"Shot {i+1}"),
            "description": f.get("description", ""),
            # visual/motion prompts come from the same autofill pass so the shot image
            # and its video action stay consistent (same entity references).
            "visual_prompt": f.get("visual_prompt") or None,
            "motion_prompt": f.get("motion_prompt") or None,
            "ref_entity_ids": json.dumps(ref_ids),
            "duration": project["shot_duration"] or 8,
            "status": "pending", "created_at": ts, "updated_at": ts})
    if scene_loc_id:
        await db.update("scene", sid, {"location_entity_id": scene_loc_id})
    return {"shots": await db.query_all(
        "SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,))}


@router.post("/projects/{pid}/storyboard/autofill-all")
async def autofill_all_storyboard(pid: str, body: AutofillRequest, force: bool = False):
    """✨ Autofill every scene in the project (skip scenes that already have shots unless force)."""
    await _project_or_404(pid)
    scenes = await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))
    done, errors = 0, []
    for sc in scenes:
        if not force:
            existing = await db.query_one(
                "SELECT COUNT(*) AS n FROM shot WHERE scene_id=?", (sc["id"],))
            if existing and existing["n"]:
                continue
        try:
            await autofill_storyboard(sc["id"], body)
            done += 1
        except Exception as ex:
            errors.append({"scene": sc["id"], "error": str(ex)[:200]})
    return {"requested": len(scenes), "done": done, "errors": errors}


def _strip_word(w: str) -> str:
    return w.lower().strip('.,!?;:"\'’“”…()-')


def _find_subseq(hay: list[str], needle: list[str], start: int) -> int:
    """Index in `hay` where `needle` first occurs at/after `start` (-1 if none)."""
    if not needle:
        return -1
    for i in range(start, len(hay) - len(needle) + 1):
        if all(hay[i + j] == needle[j] for j in range(len(needle))):
            return i
    return -1


def _caption_windows(beat_text: str, key_phrases: list[str],
                     b_start: float, b_dur: float) -> list[dict]:
    """Time each key phrase to roughly when the narration reaches it, by its word position
    within the beat (≈ proportional, since the beat is read at a steady pace)."""
    words = (beat_text or "").split()
    n = len(words) or 1
    low = [_strip_word(w) for w in words]
    caps, search_from = [], 0
    for ph in key_phrases or []:
        pw = [_strip_word(w) for w in (ph or "").split()]
        pw = [w for w in pw if w]
        if not pw:
            continue
        idx = _find_subseq(low, pw, search_from)
        if idx < 0:
            idx = search_from
        start = b_start + (idx / n) * b_dur
        dur = max(1.2, (len(pw) / n) * b_dur)
        caps.append({"text": ph.strip(), "start": round(start, 3),
                     "end": round(min(b_start + b_dur, start + dur), 3)})
        search_from = min(n - 1, idx + len(pw))
    # keep windows from overlapping (one caption on screen at a time)
    for i in range(len(caps) - 1):
        if caps[i]["end"] > caps[i + 1]["start"]:
            caps[i]["end"] = round(caps[i + 1]["start"], 3)
    return [c for c in caps if c["end"] > c["start"]]


# A terminator ends a sentence only when followed by whitespace/end (not when glued to the
# next char — filename "x.zip", decimal, version), so subtitles never split mid-token.
_SENT_RE = re.compile(r".*?(?:[.!?…]+[\"'’”\)\]]*(?=\s|$)|\n|$)", re.S)


def _subtitle_windows(beat_text: str, b_start: float, read_dur: float) -> list[dict]:
    """Subtitle the beat's SPOKEN text, one entry per sentence, each held for its share of the
    read (by word count). Together they tile the whole read — the subtitle is on screen nearly
    the entire time the beat is spoken, changing at sentence boundaries — and stay in sync
    because times come from the measured read duration."""
    clean = vntext.strip_decoration(beat_text or "")
    sents = [s.strip() for s in _SENT_RE.findall(clean) if s.strip()] or [clean.strip()]
    sents = [s for s in sents if s]
    if not sents or read_dur <= 0:
        return []
    wc = [max(1, len(s.split())) for s in sents]
    tot = sum(wc) or 1
    out, t = [], b_start
    for s, w in zip(sents, wc):
        d = read_dur * w / tot
        out.append({"text": s, "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return out


def _concat_wav_bytes(chunks: list[bytes], dest) -> None:
    """Join same-format WAV byte blobs (the per-segment TTS outputs) into one WAV file."""
    import io
    import wave
    params, frames = None, []
    for b in chunks:
        with wave.open(io.BytesIO(b), "rb") as w:
            if params is None:
                params = w.getparams()
            frames.append(w.readframes(w.getnframes()))
    with wave.open(str(dest), "wb") as out:
        out.setparams(params)
        for f in frames:
            out.writeframes(f)


async def _tts_one(text: str, voice_id: int, speed: float = 1.0, want_srt: bool = False):
    """ONE TTS call for the whole text → WAV bytes. A single continuous read keeps the
    narration's emotion (no seams from stitching many short clips).

    With want_srt, ask OmniVoice for a source-text SRT (Whisper-timed, sentence-level) and return
    (wav_bytes, srt_str_or_None). The SRT lets us time shots server-side instead of running local
    WhisperX; None if the server's ASR isn't loaded."""
    import base64
    from agent.api.tts import _proxy
    payload = {"text": text, "voice_id": voice_id, "speed": speed}
    if want_srt:
        payload["srt"] = True
    res = await _proxy("POST", "/api/tts", json=payload, timeout=600.0)
    b64 = res.get("audio") if isinstance(res, dict) else None
    if not b64:
        raise HTTPException(502, "OmniVoice không trả audio")
    audio = base64.b64decode(b64)
    if want_srt:
        return audio, (res.get("srt") or None)
    return audio


async def _tts_segments(text: str, voice_id: int, speed: float = 1.0) -> list[bytes]:
    """Fallback only: split VN text into short sentence-aligned segments and TTS each → WAV
    bytes (re-joined by the caller). Used when a single-shot read fails (e.g. text too long
    for the engine); per-scene narration prefers `_tts_one` to stay emotionally continuous."""
    import base64
    from agent.api.tts import _proxy
    out = []
    for seg in (vntext.split_segments(text) or [text]):
        res = await _proxy("POST", "/api/tts",
                           json={"text": seg, "voice_id": voice_id, "speed": speed},
                           timeout=600.0)
        b64 = res.get("audio") if isinstance(res, dict) else None
        if not b64:
            raise HTTPException(502, "OmniVoice không trả audio")
        out.append(base64.b64decode(b64))
    return out


def _wav_bytes_duration(b: bytes) -> float:
    """Duration (s) of a WAV byte buffer, read straight from its header (no ffprobe)."""
    import io
    import wave
    try:
        with wave.open(io.BytesIO(b), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:  # noqa: BLE001
        return 0.0


def _silence_wav_bytes(template: bytes, seconds: float) -> bytes:
    """A silent WAV blob matching `template`'s format — inserted between beats as a breathing
    pause so the read isn't an exhausting run-on."""
    import io
    import wave
    with wave.open(io.BytesIO(template), "rb") as w:
        params = w.getparams()
    n = max(0, int(round(params.framerate * seconds)))
    silence = b"\x00" * (n * params.sampwidth * params.nchannels)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setparams(params)
        out.writeframes(silence)
    return buf.getvalue()


async def _tts_beats(texts: list[str], voice_id: int, pid: str, scene_id: str,
                     speed: float = 1.0, gap: float = 0.0,
                     sentence_gap: float = 0.0,
                     edge_pad: float = 0.0) -> tuple[str, list[float], float]:
    """TTS each beat SENTENCE-BY-SENTENCE, then concat into one scene WAV with two levels of
    breathing silence: `sentence_gap` between sentences WITHIN a beat, and the larger `gap`
    between beats. Reading per sentence forces a real pause at every '.'/'!'/'?' (the engine
    otherwise runs sentences together, which is exhausting to listen to).

    `edge_pad` seconds of silence are prepended AND appended to the whole scene WAV so an
    editor's cross-dissolve has silent handles at both ends (it otherwise eats the first/last
    spoken words). The leading pad shifts every beat's start by `edge_pad`, so it is returned
    for the caller to offset timing.

    Returns (web_path, [per-beat READ durations], lead) where lead == the applied leading
    edge_pad (0 if no audio template). Each read is the full spoken span of a beat incl. its
    internal sentence gaps, EXCLUDING the trailing inter-beat gap. So images + subtitles land
    on the narration.

    Fault-tolerant: a sentence whose TTS fails becomes a silence of its estimated length (the
    rest of the scene's real audio is still saved + stays aligned). Raises only if EVERY
    sentence failed (caller then falls back to a word-count estimate for the whole scene)."""
    # 1) synthesize every sentence of every beat (grouped per beat), tolerating failures.
    beat_pieces: list[list[tuple[bytes | None, float]]] = []  # per beat: [(audio|None, secs)]
    template: bytes | None = None                             # a real WAV → silence params
    for txt in texts:
        # normalize strips decoration; do NOT fall back to the raw text when it empties out
        # (a beat that is only a decoration glyph like "◆"/"—" must become silence, not be
        # read literally). Also drop word-less sentences (pure punctuation) so TTS never
        # speaks a stray symbol as gibberish.
        norm = (vntext.normalize(txt) or "").strip()
        sents = [s for s in vntext.sentences(norm) if re.search(r"\w", s)] if norm else []
        if not sents:                                         # empty/decoration-only → silence
            beat_pieces.append([(None, 0.8)])
            continue
        sent_pieces: list[tuple[bytes | None, float]] = []
        for s in sents:
            try:
                audio = await _tts_one(s, voice_id, speed)
            except Exception as e:  # noqa: BLE001 — one bad sentence must not sink the scene
                logger.warning("câu TTS lỗi, ước lượng câu này: %s", e)
                audio = None
            if audio:
                template = template or audio
                sent_pieces.append((audio, round(_wav_bytes_duration(audio), 3)))
            else:
                sent_pieces.append((None, max(0.6, round(_estimate_narration_secs(s), 3))))
        beat_pieces.append(sent_pieces)
    if template is None:
        raise HTTPException(502, "Không tạo được audio cho câu nào")
    # 2) assemble. Within a beat: sentence audio + sentence_gap between sentences. Between
    #    beats: the larger gap (not after the last beat). A beat's READ = sum of its sentence
    #    durations + its internal sentence gaps.
    out: list[bytes] = []
    reads: list[float] = []
    n = len(beat_pieces)
    lead = round(edge_pad, 3) if edge_pad > 0 else 0.0
    if lead > 0:                                          # silent handle at the very start
        out.append(_silence_wav_bytes(template, lead))
    for bi, sent_pieces in enumerate(beat_pieces):
        read = 0.0
        for si, (audio, dur) in enumerate(sent_pieces):
            out.append(audio if audio is not None else _silence_wav_bytes(template, dur))
            read += dur
            if sentence_gap > 0 and si < len(sent_pieces) - 1:
                out.append(_silence_wav_bytes(template, sentence_gap))
                read += sentence_gap
        reads.append(round(read, 3))
        if gap > 0 and bi < n - 1:
            out.append(_silence_wav_bytes(template, gap))
    if lead > 0:                                          # silent handle at the very end
        out.append(_silence_wav_bytes(template, lead))
    rel = f"{pid}/narr_scene_{scene_id}.wav"
    dest = media_store.MEDIA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(_concat_wav_bytes, out, dest)
    return f"/media/{rel}", reads, lead


# ─── Continuous narration (storytelling v2): read whole paragraphs, align back ──────────
# Old builds read each beat SENTENCE-BY-SENTENCE and stitched them with big gaps, which chopped
# the audio mid-sentence and sounded fragmented. Now we read the scene as CONTINUOUS paragraphs
# (one OmniVoice call each, natural prosody), then use WhisperX (agent.studio.align) to recover
# each shot's real time span. Image cuts / subtitles fall on the aligned times; a small pause is
# spliced only AFTER a shot that ends a sentence (never mid-sentence).

_PARA_MAX_CHARS = int(os.environ.get("FLOWKIT_TTS_PARA_MAX_CHARS", "800"))
_TERM_PUNCT = ".!?…;:—–"
# Ask OmniVoice for source-text SRT and time shots from it (GPU, server-side) instead of running
# local WhisperX. Safe to leave on: if the server's ASR isn't loaded it returns no SRT and we
# fall back to WhisperX. Set FLOWKIT_TTS_SRT=0 to always use local WhisperX.
_TTS_SRT = os.environ.get("FLOWKIT_TTS_SRT", "1").strip().lower() not in ("0", "false", "no")


def _paragraphs(text: str) -> list[str]:
    """Split verbatim narration into continuous-read paragraphs: on blank lines first, then cap
    any paragraph over the engine budget by packing WHOLE sentences (never mid-sentence)."""
    text = (text or "").strip()
    if not text:
        return []
    raw = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()] or [text]
    out: list[str] = []
    for p in raw:
        p = " ".join(p.split())
        if len(p) <= _PARA_MAX_CHARS:
            out.append(p)
            continue
        cur, cur_len = [], 0
        for s in vntext.sentences(p):
            if cur and cur_len + len(s) + 1 > _PARA_MAX_CHARS:
                out.append(" ".join(cur))
                cur, cur_len = [], 0
            cur.append(s)
            cur_len += len(s) + 1
        if cur:
            out.append(" ".join(cur))
    return out or [" ".join(text.split())]


def _concat_wav_to_bytes(chunks: list[bytes]) -> bytes:
    """Join same-format WAV byte blobs → one WAV byte blob (in-memory _concat_wav_bytes)."""
    import io
    import wave
    params, frames = None, []
    for b in chunks:
        with wave.open(io.BytesIO(b), "rb") as w:
            if params is None:
                params = w.getparams()
            frames.append(w.readframes(w.getnframes()))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setparams(params)
        for f in frames:
            out.writeframes(f)
    return buf.getvalue()


async def _tts_continuous(text: str, voice_id: int, speed: float, para_gap: float,
                          want_srt: bool = False) -> tuple[bytes, list[tuple[float, float, str]] | None]:
    """Read `text` as continuous paragraphs (ONE OmniVoice call per paragraph) and concat with
    `para_gap` silence between paragraphs. No per-sentence stitching → the read stays natural.

    Returns (wav_bytes, cues). With want_srt, `cues` is the scene's SRT cues [(start, end, text)]
    with each paragraph's times offset by where its audio sits in the concatenated take — so the
    caller can time shots from them. `cues` is None if SRT was off or ANY paragraph lacked it
    (mixing real + estimated timing would drift), so the caller falls back to WhisperX."""
    audios: list[bytes] = []
    srts: list[str | None] = []
    for p in _paragraphs(text):
        norm = (vntext.normalize(p) or "").strip()
        if not re.search(r"\w", norm):
            continue
        if want_srt:
            a, s = await _tts_one(norm, voice_id, speed, want_srt=True)
            audios.append(a)
            srts.append(s)
        else:
            audios.append(await _tts_one(norm, voice_id, speed))
    if not audios:
        raise HTTPException(502, "Không tạo được audio cho scene")
    template = audios[0]
    parts: list[bytes] = []
    cues: list[tuple[float, float, str]] | None = [] if want_srt else None
    offset = 0.0
    for i, a in enumerate(audios):
        if i > 0 and para_gap > 0:
            parts.append(_silence_wav_bytes(template, para_gap))
            offset += para_gap
        if cues is not None:
            if not srts[i]:
                cues = None                       # a paragraph missing SRT → drop the whole set
            else:
                cues.extend((s + offset, e + offset, txt)
                            for (s, e, txt) in align.parse_srt(srts[i]))
        offset += _wav_bytes_duration(a)
        parts.append(a)
    return _concat_wav_to_bytes(parts), cues


_SNAP_WIN = 0.12          # ± window (s) to snap a boundary onto the natural gap
_FADE = 0.006             # fade (s) around inserted silence, kills the click/pop
_QUIET = 350              # |int16| below this ≈ silence; a pause is only spliced into real gaps


def _fade_edge(seg, fade_n: int, ch: int, fade_in: bool) -> None:
    """Linear-fade the first (fade_in) or last (fade_out) `fade_n` frames of `seg` in place, so
    joining it to silence has no abrupt step → no click."""
    fn = len(seg) // ch
    f = min(fade_n, fn)
    if f <= 0:
        return
    for k in range(f):
        g = (k + 1) / (f + 1) if fade_in else (f - k) / (f + 1)
        base = (k if fade_in else fn - f + k) * ch
        for c in range(ch):
            seg[base + c] = int(seg[base + c] * g)


def _assemble_continuous_wav(raw: bytes, starts: list[float], pause_after: list[bool],
                             pause: float, edge_pad: float
                             ) -> tuple[bytes, list[tuple[float, float]], list[float], float]:
    """Slice the raw continuous WAV at the aligned shot `starts`, re-join with `pause` silence
    after shots that end a sentence, and add `edge_pad` silent handles at both ends.

    A raw pause spliced exactly at the aligned timestamp can land MID-WORD (alignment is only
    ~frame-accurate, and ':'/'—' shots have no real gap), chopping the word into a stutter
    ("vấp"). So each internal boundary is snapped to the quietest frame within ±_SNAP_WIN, the
    pause is inserted ONLY where the audio is actually silent there (else skipped, never cutting
    speech), and a short fade wraps every inserted silence to avoid clicks.

    Returns (wav_bytes, [(start,end)] per shot on the FINAL timeline, [spoken read] per shot,
    lead). Shot end = next shot's start (tiles incl. the pause); read = the spoken span only."""
    import array
    import io
    import wave
    with wave.open(io.BytesIO(raw), "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    fr = params.framerate
    ch = params.nchannels
    n = len(starts)
    lead_f = int(round(max(0.0, edge_pad) * fr))
    pause_f = int(round(max(0.0, pause) * fr))

    if params.sampwidth != 2:                    # non-16-bit: plain contiguous splice (no fades)
        bpf = params.sampwidth * ch
        total = len(frames) // bpf
        bidx = [max(0, min(total, int(round(s * fr)))) for s in starts] + [total]
        for i in range(1, len(bidx)):
            bidx[i] = max(bidx[i], bidx[i - 1])
        out = bytearray(b"\x00" * (lead_f * bpf))
        starts_f, reads, t = [], [], edge_pad
        for i in range(n):
            out += frames[bidx[i] * bpf: bidx[i + 1] * bpf]
            read = (bidx[i + 1] - bidx[i]) / fr
            starts_f.append(round(t, 3)); reads.append(round(read, 3)); t += read
            if pause_f and i < n - 1 and pause_after[i]:
                out += b"\x00" * (pause_f * bpf); t += pause
        out += b"\x00" * (lead_f * bpf)
        times = [(starts_f[i], starts_f[i + 1] if i + 1 < n else round(t, 3)) for i in range(n)]
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setparams(params); w.writeframes(bytes(out))
        return buf.getvalue(), times, reads, round(max(0.0, edge_pad), 3)

    samples = array.array("h")
    samples.frombytes(frames)
    total = len(samples) // ch
    ewin = max(1, int(0.003 * fr))               # ±3ms window for the peak-amplitude probe

    def amp(f: int) -> int:                       # peak |amplitude| on ch0 around frame f
        lo = max(0, f - ewin) * ch
        hi = min(total, f + ewin) * ch
        m = 0
        for k in range(lo, hi, ch):
            v = samples[k]
            v = -v if v < 0 else v
            if v > m:
                m = v
        return m

    win = int(_SNAP_WIN * fr)
    step = max(1, int(0.002 * fr))
    bnd = [0]
    quiet = [True]                                # was boundary i snapped onto a real gap?
    for i in range(1, n):
        b0 = min(max(int(round(starts[i] * fr)), 0), total)
        lo = max(bnd[-1] + 1, b0 - win)
        hi = min(total - 1, b0 + win)
        best, bestv = b0, amp(b0)
        f = lo
        while f <= hi:
            v = amp(f)
            if v < bestv:
                bestv, best = v, f
            f += step
        bnd.append(max(best, bnd[-1] + 1))
        quiet.append(bestv <= _QUIET)
    bnd.append(total)

    fade_n = int(_FADE * fr)
    out = array.array("h", bytes(0))
    out.extend([0] * (lead_f * ch))
    starts_f, reads, t = [], [], edge_pad
    fade_in_next = False
    for i in range(n):
        seg = samples[bnd[i] * ch: bnd[i + 1] * ch]          # array slice = a copy
        if fade_in_next:
            _fade_edge(seg, fade_n, ch, True)
            fade_in_next = False
        do_pause = bool(pause_f and i < n - 1 and pause_after[i] and quiet[i + 1])
        if do_pause:
            _fade_edge(seg, fade_n, ch, False)
        out.extend(seg)
        read = (bnd[i + 1] - bnd[i]) / fr
        starts_f.append(round(t, 3)); reads.append(round(read, 3)); t += read
        if do_pause:
            out.extend([0] * (pause_f * ch)); t += pause
            fade_in_next = True
    out.extend([0] * (lead_f * ch))
    times = [(starts_f[i], starts_f[i + 1] if i + 1 < n else round(t, 3)) for i in range(n)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setparams(params)
        w.writeframes(out.tobytes())
    return buf.getvalue(), times, reads, round(max(0.0, edge_pad), 3)


def _ends_sentence(text: str) -> bool:
    """True if `text`'s last visible char is sentence/clause-ending punctuation — so a pause may
    be spliced after it without landing mid-sentence."""
    t = vntext.strip_decoration(text or "").rstrip()
    return bool(t) and t[-1] in _TERM_PUNCT


async def _make_scene_narration(voiceover: str, shot_texts: list[str], voice_id: int,
                                pid: str, sid: str, speed: float, para_gap: float,
                                sentence_pause: float, edge_pad: float
                                ) -> tuple[str, list[tuple[float, float]], list[float], float, float]:
    """Build a scene's narration as ONE continuous read, then align the shots' spoken slices to
    it. Returns (web_path, [(start,end)] per shot, [read] per shot, lead, scene_duration).

    Raises HTTPException(502) if TTS produced nothing (caller keeps any existing audio)."""
    raw, cues = await _tts_continuous(voiceover, voice_id, speed, para_gap, want_srt=_TTS_SRT)
    rel = f"{pid}/narr_scene_{sid}.wav"
    dest = media_store.MEDIA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(dest.write_bytes, raw)      # raw take for alignment
    dur = _wav_bytes_duration(raw)
    # Prefer OmniVoice's server-side SRT timing (GPU, no local WhisperX). Fall back to local
    # WhisperX forced-alignment, which itself falls back to word-count timing.
    spans = align.align_with_cues(shot_texts, cues, dur) if cues else None
    if spans is None:
        spans = await asyncio.to_thread(align.align_sentences, str(dest), shot_texts)
    starts = [s for s, _ in spans] if spans else [0.0]
    pause_after = [_ends_sentence(t) for t in shot_texts]
    final, times, reads, lead = await asyncio.to_thread(
        _assemble_continuous_wav, raw, starts, pause_after, sentence_pause, edge_pad)
    await asyncio.to_thread(dest.write_bytes, final)
    scene_dur = round((times[-1][1] if times else 0.0) + lead, 3)
    return f"/media/{rel}", times, reads, lead, scene_dur


async def _ensure_source_segments(pid: str, force: bool = False) -> None:
    """Populate scene.source_segment by CONTENT-aligning the project's source prose (idea) to
    its scenes (once; or re-run when force=True). This replaces the naive equal-length split so
    each scene reads the part of the source that matches ITS location — content about another
    place no longer bleeds into the wrong scene. No-op if there's no source or all are set."""
    project = await db.query_one("SELECT idea FROM project WHERE id=?", (pid,))
    source = ((project or {}).get("idea") or "").strip()
    if not source:
        return
    scenes = await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))
    if not scenes:
        return
    if not force and all((s.get("source_segment") or "").strip() for s in scenes):
        return
    segments = await brain.align_source_to_scenes(source, scenes)
    for sc, seg in zip(scenes, segments):
        await db.update("scene", sc["id"], {"source_segment": seg})


@router.post("/projects/{pid}/align-source")
async def align_source(pid: str):
    """Re-run content alignment of the source prose → scenes (force). Use when scene order or
    the source changed and the narration is landing in the wrong scene."""
    await _project_or_404(pid)
    await _ensure_source_segments(pid, force=True)
    return {"scenes": await db.query_all(
        "SELECT id, idx, heading, source_segment FROM scene WHERE project_id=? ORDER BY idx",
        (pid,))}


@router.post("/scenes/{sid}/beats")
async def build_scene_beats(sid: str, body: BuildBeatsRequest):
    """Storytelling (§2.6, audio-first): the scene reads a VERBATIM contiguous chunk of the
    user's original input. We segment it into visual beats, then TTS each beat as its own
    continuous read and measure its REAL duration, so image changes land exactly on the
    narration (the cuts fall on beat = image-change boundaries). Key phrases get timed caption
    windows. If TTS is off/unreachable, beat durations fall back to a word-count estimate."""
    scene = await _scene_or_404(sid)
    project = await _project_or_404(scene["project_id"])
    erows = await db.query_all(
        "SELECT id, name, type, description FROM entity WHERE project_id=?", (scene["project_id"],))
    by_name = _index_by_name(erows)
    # The scene's location is fixed. Prefer a location_entity_id already stored on the scene
    # (e.g. inherited by a split sub-scene, or set by a previous build) so the place is STABLE
    # and never re-guessed onto the wrong location; else match it from the heading.
    scene_loc = None
    if scene.get("location_entity_id"):
        scene_loc = next((r for r in erows if r["id"] == scene["location_entity_id"]
                          and r["type"] == "location"), None)
    if not scene_loc:
        scene_loc = _match_location_entity(scene["heading"], [r for r in erows if r["type"] == "location"])
    scene_loc_id = scene_loc["id"] if scene_loc else None

    # 1) the scene's narration = its VERBATIM slice of the user's ORIGINAL input
    #    (project.idea), read in full — NOT an AI rewrite of the screenplay. Storytelling
    #    must speak the source text the user gave, complete and unaltered. We partition the
    #    original across the project's scenes (in order) so the union covers the whole text.
    source = (project.get("idea") or "").strip()
    if source:
        # The scene reads the part of the source that matches ITS location (content-aligned),
        # cached in source_segment. Align the whole project once if not done yet.
        voiceover = (scene.get("source_segment") or "").strip()
        if not voiceover:
            await _ensure_source_segments(scene["project_id"])
            scene = await _scene_or_404(sid)
            voiceover = (scene.get("source_segment") or "").strip()
        if not voiceover:                              # alignment unavailable → equal-length split
            order = [r["id"] for r in await db.query_all(
                "SELECT id FROM scene WHERE project_id=? ORDER BY idx", (scene["project_id"],))]
            pos = order.index(sid) if sid in order else 0
            parts = brain.partition_text(source, len(order) or 1)
            voiceover = (parts[pos] if pos < len(parts) else "").strip()
        if not voiceover:
            raise HTTPException(
                400, "Scene này không còn nội dung gốc để đọc — số scene đang nhiều hơn "
                "số câu trong nội dung nguồn. Giảm bớt scene hoặc bổ sung nội dung gốc.")
    else:
        # no original input stored → fall back to the scene's own script text, verbatim
        voiceover = (scene.get("action") or "").strip()
        if not voiceover:
            raise HTTPException(400, "Chưa có nội dung gốc (idea) để đọc cho scene này.")

    # 2) segment the verbatim narration into visual beats (AI = visual structure + key
    #    phrases). The SPOKEN text per beat is re-derived verbatim from the narration so the
    #    audio always covers the whole scene in order — no AI drift, no dropped sentences.
    # ~SHOT_TARGET_SECS of narration per beat → an image change every ~9s: fresh enough that the
    # video doesn't go stale on one still, long enough that a chapter doesn't cost a swarm of
    # images. Target count drives the AI; partition_text caps it at sentence count.
    target_beats = max(1, round(_estimate_narration_secs(voiceover) / SHOT_TARGET_SECS))
    loc_name = scene_loc["name"] if scene_loc else None
    # First understand the WHOLE scene (who's present, blocking, coverage) so the beats form a
    # coherent scene instead of a random string of solo shots. Best-effort — segmentation still
    # runs without it.
    plan = None
    try:
        plan = await brain.run_json_valid(
            brain.scene_plan_prompt(voiceover, erows, project["style"], location=loc_name),
            lambda d: isinstance(d, dict) and isinstance(d.get("blocking") or d.get("coverage"), str),
            label=f"Kế hoạch scene ({scene.get('heading') or sid})", attempts=2)
    except Exception as e:  # noqa: BLE001 — plan is optional
        logger.warning("scene plan unavailable (%s) — dùng tách beat không kế hoạch", e)
    try:
        beats = await brain.run_json_valid(
            brain.scene_segment_prompt(
                voiceover, erows, project["style"],
                location=loc_name, target_beats=target_beats, plan=plan,
                arc=await _scene_arc(scene, project),
                **_engine_kw(project)),
            lambda d: isinstance(d, list) and len(d) > 0 and all(isinstance(x, dict) for x in d),
            label=f"Tách beat ({scene.get('heading') or sid})")
    except HTTPException as e:
        # Retries exhausted: rather than collapse the scene into ONE giant shot (which forced
        # the user to redo it by hand), fall back to a DETERMINISTIC split into ~8s beats so the
        # scene still gets proper shots + audio timing. Generic framing — refine via "Đa dạng góc máy".
        logger.warning("scene %s beat-segment fell back to deterministic split: %s", sid, e.detail)
        slices = brain.partition_text(voiceover, target_beats)
        loc_ref = [loc_name] if loc_name else []
        beats = [{"text": s, "description": (f"{loc_name}, " if loc_name else "") + "cinematic shot",
                  "ref_entity_names": loc_ref, "key_phrases": []} for s in slices]
    if not scene_loc_id:                      # heading matched no entity → use the AI's pick
        scene_loc_id = _first_location_id(beats, by_name)
    say = brain.partition_text(voiceover, len(beats))   # verbatim contiguous slices, complete
    if len(say) < len(beats):                            # fewer sentences than beats → trim
        beats = beats[:len(say)]
    for i, b in enumerate(beats):
        # strip decoration glyphs from the stored/spoken slice so narrator_text, the shot title
        # and the burned caption never show a '◆' the narration won't read (audio already drops
        # it via normalize; this keeps the TEXT in sync).
        b["_say"] = vntext.strip_decoration(say[i] if i < len(say) else (b.get("text") or "")).strip()

    # Re-cut every beat to the ~8–10s shot band regardless of what the AI returned (LLMs cap their
    # output, so a long scene came back as a handful of 40–60s beats). Sub-shots split at
    # sentence/clause boundaries and PACK to fill the band, so we never emit a swarm of 3–5s
    # shots; each sub-shot keeps the parent beat's visual context, the narration just advances.
    expanded: list[dict] = []
    for b in beats:
        subs = brain.chunk_by_duration(b.get("_say") or "", MAX_SHOT_SECS, MIN_SHOT_SECS)
        if len(subs) <= 1:
            expanded.append(b)
            continue
        for j, sub in enumerate(subs):
            nb = dict(b)
            nb["_say"] = sub
            # sub-shots share the beat's coherent moment, but must NOT render as the same still —
            # rotate the framing so consecutive sub-shots differ in size/angle.
            if j > 0 and nb.get("description"):
                ang = _SUBSHOT_ANGLES[j % len(_SUBSHOT_ANGLES)]
                nb["description"] = (f"{nb['description']} Camera for THIS moment: {ang}, "
                                     "a distinctly different angle from the previous shot.")
            expanded.append(nb)
    beats = expanded

    # chunk_by_duration only packs WITHIN a beat, so an AI beat that is itself tiny ("của anh.",
    # "chín.") still became a sub-second shot — and a whole image. Merge any beat under the floor
    # into its neighbour (keeping the neighbour's framing), as long as the result stays a
    # reasonable shot. Verbatim: the spoken slices are concatenated in order, nothing is dropped.
    beats = _merge_short_beats(beats)

    # 3) Narration = ONE continuous read of the whole scene (natural prosody), then align the
    #    shots' spoken slices back to it (WhisperX) for real per-shot timing. A small pause is
    #    spliced only after a shot that ends a sentence. Falls back to a word-count estimate if
    #    TTS is off/unreachable. (tts_gap = pause BETWEEN paragraphs, tts_sentence_gap = extra
    #    pause after a sentence, tts_edge_pad = silent handles at both ends.)
    voice_id = project.get("voice_id") or 0
    speed = float(project.get("tts_speed") or 1.0)
    para_gap = min(max(float(project.get("tts_gap") if project.get("tts_gap") is not None else 0.4), 0.0), 2.0)
    sentence_pause = min(max(
        float(project.get("tts_sentence_gap") if project.get("tts_sentence_gap") is not None else 0.3),
        0.0), 1.5)
    edge_pad = min(max(
        float(project.get("tts_edge_pad") if project.get("tts_edge_pad") is not None else 0.5),
        0.0), 3.0)
    shot_texts = [b.get("_say") or "" for b in beats]
    narr_web, times, reads, lead, scene_dur = None, None, None, 0.0, 0.0
    if body.measure and any(s.strip() for s in shot_texts):
        try:
            narr_web, times, reads, lead, scene_dur = await _make_scene_narration(
                voiceover, shot_texts, voice_id, project["id"], sid,
                speed, para_gap, sentence_pause, edge_pad)
        except HTTPException as e:
            logger.warning("scene TTS unavailable (%s) — dùng ước lượng theo số từ", e.detail)
        except Exception as e:  # noqa: BLE001
            logger.warning("scene TTS failed: %s — dùng ước lượng theo số từ", e)
    if times is None or len(times) != len(beats):        # TTS off/failed → word-count estimate
        wc = [max(1, len(s.split())) for s in shot_texts]
        total_wc = sum(wc) or 1
        scene_est = _estimate_narration_secs(voiceover)
        reads = [max(0.8, round(scene_est * w / total_wc, 3)) for w in wc]
        times, acc = [], 0.0
        for r in reads:
            times.append((round(acc, 3), round(acc + r, 3)))
            acc += r
        lead, scene_dur, narr_web = 0.0, round(acc, 3), None

    await db.execute("DELETE FROM shot WHERE scene_id=?", (sid,))
    await db.update("scene", sid, {
        "narration_text": voiceover, "narration_path": narr_web,
        "narration_duration": scene_dur, "location_entity_id": scene_loc_id})
    ts = db.now()
    for i, b in enumerate(beats):
        start_t, end_t = times[i]
        b_dur = round(end_t - start_t, 3)          # timeline share (incl. any trailing pause)
        # subtitle spans the SPOKEN read (nearly the whole shot), not the trailing pause
        caps = _subtitle_windows(b.get("_say") or "", start_t, reads[i])
        text = " ".join(filter(None, [b.get("description"), b.get("visual_prompt"), b.get("motion_prompt")]))
        ref_ids = _resolve_shot_refs(text, b.get("ref_entity_names"), by_name, scene_loc_id)
        await db.insert("shot", {
            "id": db.new_id(), "scene_id": sid, "idx": i,
            "beat_id": db.new_id(), "part_idx": 0, "is_chained": 0,
            "title": (b.get("_say") or "")[:40] or f"Beat {i+1}",
            "description": b.get("description", ""),
            "visual_prompt": b.get("visual_prompt") or None,
            "motion_prompt": b.get("motion_prompt") or None,
            "beat_action": b.get("beat_action") or None,
            # narrator_text = this beat's VERBATIM spoken slice; its audio is the aligned segment
            # of the one continuous scene WAV.
            "narrator_text": b.get("_say") or None,
            "narration_duration": b_dur,          # this beat's real share of the timeline
            "start_time": start_t,                # scene-local offset (aligned)
            "captions": json.dumps(caps, ensure_ascii=False),
            "ref_entity_ids": json.dumps(ref_ids),
            "duration": max(1, int(round(b_dur))),
            "status": "pending", "created_at": ts, "updated_at": ts})

    return {"shots": await db.query_all(
        "SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,)),
        "scene_duration": scene_dur, "narration_path": narr_web,
        "measured": narr_web is not None}


@router.post("/scenes/{sid}/rebuild-audio")
async def rebuild_scene_audio(sid: str):
    """Re-synthesize ONLY the narration audio for a scene from its EXISTING shots' narrator_text,
    then re-time the shots + captions to the new audio. Images, prompts, refs and node graphs are
    left untouched — so you can apply changed TTS settings (speed / gap / edge-pad) or a fixed
    normalizer to a scene you already generated images for, WITHOUT the long image re-gen.

    Errors (502) if TTS produced nothing, leaving the existing audio/timing intact (so a down
    OmniVoice never wipes a good take)."""
    scene = await _scene_or_404(sid)
    project = await _project_or_404(scene["project_id"])
    shots = await db.query_all("SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,))
    if not shots:
        raise HTTPException(400, "Scene chưa có shot nào để dựng lại audio")
    # strip decoration from existing narration (old builds kept a '◆' prefix) so the re-TTS
    # and re-tiled captions are clean.
    say = [vntext.strip_decoration(s.get("narrator_text") or "").strip() for s in shots]
    if not any(say):
        raise HTTPException(400, "Các shot chưa có lời đọc (narrator_text) để tạo audio")

    # The whole scene is read CONTINUOUSLY (the shots' spoken slices joined, in order); each
    # existing shot is then re-timed by aligning its slice back to that one take. Images are not
    # touched. So even shots whose text was split mid-sentence by an old build now sit under
    # smooth, un-chopped audio — only the image change lands mid-sentence, which is fine.
    voiceover = " ".join(s for s in say if s)
    voice_id = project.get("voice_id") or 0
    speed = float(project.get("tts_speed") or 1.0)
    para_gap = min(max(float(project.get("tts_gap") if project.get("tts_gap") is not None else 0.4), 0.0), 2.0)
    sentence_pause = min(max(
        float(project.get("tts_sentence_gap") if project.get("tts_sentence_gap") is not None else 0.3),
        0.0), 1.5)
    edge_pad = min(max(
        float(project.get("tts_edge_pad") if project.get("tts_edge_pad") is not None else 0.5),
        0.0), 3.0)

    try:
        narr_web, times, reads, lead, scene_dur = await _make_scene_narration(
            voiceover, say, voice_id, project["id"], sid,
            speed, para_gap, sentence_pause, edge_pad)
    except HTTPException as e:
        raise HTTPException(502, f"Không tạo được audio ({e.detail}). Kiểm tra OmniVoice URL "
                                 f"trong ⚙ Settings rồi thử lại — audio cũ được giữ nguyên.")
    if len(times) != len(shots):                      # one aligned span per shot → must line up 1:1
        raise HTTPException(500, "Số đoạn audio không khớp số shot")

    await db.update("scene", sid, {
        "narration_path": narr_web, "narration_duration": scene_dur,
        "narration_text": voiceover})
    ts = db.now()
    for i, s in enumerate(shots):
        start_t, end_t = times[i]
        b_dur = round(end_t - start_t, 3)
        # captions re-tiled over the new aligned timing (spoken read only, not the trailing pause)
        caps = _subtitle_windows(say[i], start_t, reads[i])
        update = {
            "narration_duration": b_dur,
            "start_time": start_t,
            "captions": json.dumps(caps, ensure_ascii=False),
            "duration": max(1, int(round(b_dur))),
            "updated_at": ts}
        if say[i] and say[i] != (s.get("narrator_text") or "").strip():
            update["narrator_text"] = say[i]    # persist the decoration-stripped narration
        await db.update("shot", s["id"], update)

    return {"shots": await db.query_all(
        "SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,)),
        "scene_duration": scene_dur, "narration_path": narr_web, "measured": True}


async def _revary_scene(sid: str) -> int:
    """Rewrite EXISTING shots' camera (description/visual/motion) for varied angles AND fix the
    location/refs — without touching narration text, timing or audio. The fast way to repair a
    scene (monotonous framing, wrong location, missing/extra entity refs) without re-TTS."""
    scene = await _scene_or_404(sid)
    project = await _project_or_404(scene["project_id"])
    shots = await db.query_all("SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,))
    if not shots:
        return 0
    erows = await db.query_all(
        "SELECT id, name, type, description FROM entity WHERE project_id=?", (scene["project_id"],))
    by_name = _index_by_name(erows)
    scene_loc = _match_location_entity(scene["heading"], [r for r in erows if r["type"] == "location"])
    scene_loc_id = scene_loc["id"] if scene_loc else None
    # Retry the AI step until we get a usable list (covers agent errors, bad JSON AND a
    # valid-but-wrong-shape reply, which run_json's own retry doesn't catch).
    out = None
    arc = await _scene_arc(scene, project)
    for attempt in range(3):
        try:
            cand = await brain.run_json(brain.revary_shots_prompt(
                shots, erows, project["style"],
                location=(scene_loc["name"] if scene_loc else None), arc=arc,
                **_engine_kw(project)))
            if isinstance(cand, list) and cand:
                out = cand
                break
            logger.warning("revary scene %s attempt %d: AI trả về sai định dạng", sid, attempt)
        except Exception as ex:  # noqa: BLE001
            logger.warning("revary scene %s attempt %d failed: %s", sid, attempt, ex)
        await asyncio.sleep(1.0 + attempt)
    if not out:
        raise HTTPException(502, "AI không trả về danh sách góc máy (đã thử lại nhiều lần)")
    if not scene_loc_id:                       # heading matched no entity → keep AI's pick
        scene_loc_id = _first_location_id(out, by_name)
    mapped: dict[int, dict] = {}
    for pos, o in enumerate(out):
        if not isinstance(o, dict):
            continue
        k = o.get("idx")
        idx = int(k) if isinstance(k, (int, float)) or (isinstance(k, str) and k.isdigit()) else pos
        mapped[idx] = o
    n = 0
    for i, s in enumerate(shots):
        o = mapped.get(i)
        if not o:
            continue
        upd = {f: o[f] for f in ("description", "visual_prompt", "motion_prompt") if o.get(f)}
        if upd:
            # Re-resolve refs from the new prompt's {braces}: one location (the scene's) +
            # every non-location entity actually named.
            text = " ".join(filter(None, [o.get("description"), o.get("visual_prompt"), o.get("motion_prompt")]))
            upd["ref_entity_ids"] = json.dumps(_resolve_shot_refs(text, None, by_name, scene_loc_id))
            upd["updated_at"] = db.now()
            await db.update("shot", s["id"], upd)
            n += 1
    if scene_loc_id:
        await db.update("scene", sid, {"location_entity_id": scene_loc_id})
    return n


@router.post("/scenes/{sid}/revary-job")
async def revary_scene_job(sid: str):
    """Đa dạng góc máy cho 1 scene (giữ lời đọc/thời lượng) → job nền (§9)."""
    scene = await _scene_or_404(sid)

    async def _worker(_):
        await _revary_scene(sid)

    job = get_job_manager().start(
        project_id=scene["project_id"], type_="revary", items=[scene], worker=_worker,
        label=f"Góc máy: {scene.get('heading') or 'scene'}", throttle=(0, 0),
        item_label=lambda s: s.get("heading") or sid)
    return {"job_id": job.id, "total": 1}


@router.post("/projects/{pid}/revary")
async def revary_project(pid: str):
    """Đa dạng góc máy cho MỌI scene (chỉ viết lại mô tả/visual/motion, KHÔNG đụng audio/TTS)
    → job nền (§9). Nhanh hơn nhiều so với dựng lại shots; sau đó chỉ cần Auto gen lại ảnh."""
    await _project_or_404(pid)
    scenes = await db.query_all("SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))
    if not scenes:
        raise HTTPException(400, "Chưa có scene — tạo kịch bản (Script) trước.")

    async def _worker(sc):
        await _revary_scene(sc["id"])

    job = get_job_manager().start(
        project_id=pid, type_="revary", items=scenes, worker=_worker,
        label=f"Đa dạng góc máy ({len(scenes)} scene)", throttle=(0.3, 1.0),
        item_label=lambda sc: sc.get("heading") or sc["id"])
    return {"job_id": job.id, "total": len(scenes)}


@router.post("/scenes/{sid}/beats-job")
async def build_scene_beats_job(sid: str, body: BuildBeatsRequest):
    """Per-scene 'Dựng theo lời đọc' as a background job (§9): TTS is slow, so kick it off
    and report state in the banner instead of blocking the request (which made the UI look
    hung). One scene = one job step; shots are deleted + rebuilt when it completes."""
    scene = await _scene_or_404(sid)
    await _ensure_source_segments(scene["project_id"])   # content-align source once if needed

    async def _worker(_):
        await build_scene_beats(sid, body)

    job = get_job_manager().start(
        project_id=scene["project_id"], type_="beats", items=[scene], worker=_worker,
        label=f"Lời đọc: {scene.get('heading') or 'scene'}", throttle=(0, 0),
        item_label=lambda s: s.get("heading") or sid)
    return {"job_id": job.id, "total": 1}


@router.post("/projects/{pid}/voiceover")
async def build_project_beats(pid: str, body: BuildBeatsRequest):
    """Storytelling (§2.6): per-scene whole-read TTS + beat mapping for EVERY scene → job
    nền (§9). Mỗi scene là 1 bước (xoá shot cũ + TTS + dựng beat) nên tiến độ hiện theo
    từng scene; sau cùng stitch project.voiceover_raw từ các narration. Trả job_id ngay —
    quá trình TTS rất chậm nên KHÔNG block request, tránh tưởng treo."""
    await _project_or_404(pid)
    scenes = await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))
    if not scenes:
        raise HTTPException(400, "Chưa có scene — tạo kịch bản (Script) trước.")
    await _ensure_source_segments(pid)                   # content-align source once if needed

    async def _worker(sc):
        await build_scene_beats(sc["id"], body)

    async def _finalize():
        rows = await db.query_all(
            "SELECT narration_text FROM scene WHERE project_id=? ORDER BY idx", (pid,))
        vo = [s["narration_text"] for s in rows if s.get("narration_text")]
        await db.update("project", pid, {
            "voiceover_raw": "\n\n".join(vo), "storytelling": 1, "updated_at": db.now()})

    job = get_job_manager().start(
        project_id=pid, type_="beats", items=scenes, worker=_worker,
        label=f"Dựng lời đọc + beats ({len(scenes)} scene)",
        throttle=(0.5, 1.5),  # TTS itself is the slow part; keep inter-scene gap small
        item_label=lambda sc: sc.get("heading") or sc["id"],
        finalize=_finalize)
    return {"job_id": job.id, "total": len(scenes)}


@router.post("/projects/{pid}/rebuild-audio")
async def rebuild_project_audio(pid: str):
    """Re-synthesize narration for EVERY scene that has shots (continuous read + WhisperX
    re-timing) while KEEPING all generated images — the bulk version of a scene's '🔊 Tạo lại
    audio'. Background job (§9): TTS + alignment are slow, so report progress per scene. Only
    scenes whose shots carry narrator_text are included (others have nothing to re-read)."""
    await _project_or_404(pid)
    scenes = await db.query_all(
        "SELECT s.* FROM scene s WHERE s.project_id=? AND EXISTS "
        "(SELECT 1 FROM shot sh WHERE sh.scene_id=s.id AND sh.narrator_text IS NOT NULL) "
        "ORDER BY s.idx", (pid,))
    if not scenes:
        raise HTTPException(400, "Chưa scene nào có lời đọc (narrator_text) để tạo lại audio.")

    async def _worker(sc):
        await rebuild_scene_audio(sc["id"])

    job = get_job_manager().start(
        project_id=pid, type_="audio", items=scenes, worker=_worker,
        label=f"Tạo lại audio ({len(scenes)} scene)",
        throttle=(0.3, 1.0),  # alignment serializes on its own lock; keep the gap small
        item_label=lambda sc: sc.get("heading") or sc["id"])
    return {"job_id": job.id, "total": len(scenes)}


class AddSceneRequest(BaseModel):
    heading: Optional[str] = None
    # Tạo luôn N shot rỗng trong scene mới. Dự án chưa có kịch bản thì việc người dùng muốn
    # là "cho tôi một khung để làm", không phải "cho tôi một scene rỗng rồi bấm tiếp".
    shots: int = 0


@router.post("/projects/{pid}/scenes")
async def add_scene(pid: str, body: AddSceneRequest = None):
    """Thêm MỘT scene rỗng vào cuối dự án (+ tuỳ chọn vài shot rỗng trong đó).

    Đường làm việc KHÔNG qua kịch bản: dự án mới chưa trích được scene nào thì storyboard và
    shots không có chỗ nào để treo shot vào — mọi thứ nằm dưới `shot.scene_id`. Scene tạo tay
    để trống mọi trường văn bản; các đường sinh ảnh/video đều đọc `description` của shot chứ
    không bắt scene phải có `action`/`dialog`.
    """
    await _project_or_404(pid)
    body = body or AddSceneRequest()
    ts = db.now()
    row = await db.query_one("SELECT MAX(idx) AS m FROM scene WHERE project_id=?", (pid,))
    idx = (row["m"] + 1) if row and row["m"] is not None else 0
    scene_id = db.new_id()
    await db.insert("scene", {
        "id": scene_id, "project_id": pid, "idx": idx,
        "heading": (body.heading or "").strip() or f"SCENE {idx + 1}",
        "slug": "", "action": "", "dialog": "",
        "created_at": ts})
    for _ in range(max(0, min(body.shots, 20))):
        await add_shot(scene_id)
    return await _scene_or_404(scene_id)


class UpdateSceneRequest(BaseModel):
    """Sửa phần văn bản của scene. `heading` = tên scene hiện trên đầu mỗi dải shot."""
    heading: Optional[str] = None
    action: Optional[str] = None


@router.patch("/scenes/{sid}")
async def update_scene(sid: str, body: UpdateSceneRequest):
    """Đổi tên (heading) / sửa action của MỘT scene.

    Không đụng `source_segment`: nó là lát cắt văn bản gốc do khâu align sinh ra, đổi tên
    scene không làm nó sai."""
    await _scene_or_404(sid)
    data = body.model_dump(exclude_none=True)
    if "heading" in data:
        # Tên rỗng làm dải shot mất mốc nhận biết, mà người dùng xoá trắng ô rồi rời chuột là
        # chuyện thường — giữ lại tên cũ thay vì lưu chuỗi rỗng.
        data["heading"] = data["heading"].strip()
        if not data["heading"]:
            del data["heading"]
    if data:
        await db.execute("UPDATE scene SET " + ", ".join(f"{k}=?" for k in data) +
                         " WHERE id=?", (*data.values(), sid))
    return await _scene_or_404(sid)


@router.delete("/scenes/{sid}")
async def delete_scene(sid: str):
    """Xoá scene + toàn bộ shot của nó (file media giữ nguyên trong thư mục dự án)."""
    scene = await _scene_or_404(sid)
    await db.execute("DELETE FROM shot WHERE scene_id=?", (sid,))
    await db.execute("DELETE FROM scene WHERE id=?", (sid,))
    # Dồn idx cho liền lại, nếu không thứ tự hiển thị vẫn đúng nhưng số scene nhảy cóc.
    rows = await db.query_all(
        "SELECT id FROM scene WHERE project_id=? ORDER BY idx", (scene["project_id"],))
    for i, r in enumerate(rows):
        await db.execute("UPDATE scene SET idx=? WHERE id=?", (i, r["id"]))
    return {"ok": True}


@router.post("/scenes/{sid}/shots")
async def add_shot(sid: str):
    await _scene_or_404(sid)
    ts = db.now()
    sidx = await _next_shot_idx(sid)
    shot_id = db.new_id()
    await db.insert("shot", {
        "id": shot_id, "scene_id": sid, "idx": sidx, "title": f"Shot {sidx+1}",
        "description": "", "ref_entity_ids": "[]", "duration": 8,
        "status": "pending", "created_at": ts, "updated_at": ts})
    return await _shot_or_404(shot_id)


class BulkShotsRequest(BaseModel):
    """Văn bản nhiều dòng — MỖI DÒNG một prompt, mỗi prompt một shot."""
    text: str
    # Prompt đi vào cột nào: `description` = mô tả khung hình (tab Storyboard, dựng ẢNH),
    # `motion_prompt` = chuyển động (tab Shots, dựng VIDEO). Hai tab hai cột khác nhau nên
    # tham số này bắt buộc phải khớp với chỗ gọi, đừng mặc định "cột nào cũng được".
    field: str = "description"


# Đầu dòng kiểu danh sách — dán từ ChatGPT/Word/Docs thì gần như luôn có. Giữ nguyên thì
# "1." lọt vào prompt gửi lên model.
_LIST_MARK = re.compile(r"^\s*(?:[-*•–—]|\(?\d{1,3}[.)]|\d{1,3}\s*[-–])\s+")
BULK_SHOTS_MAX = 300


def split_bulk_prompts(text: str) -> list[str]:
    """Tách văn bản nhiều dòng thành danh sách prompt — MỘT DÒNG một prompt.

    Dòng trống bị bỏ (dán từ Word/Docs hay lẫn dòng trống giữa các mục), và đầu dòng kiểu
    danh sách ("1.", "-", "•"…) bị cắt. KHÔNG gộp đoạn: xuống dòng là sang shot mới, kể cả
    khi hai dòng liền nhau — người dùng gõ Enter là có ý sang shot khác."""
    out = []
    for line in (text or "").splitlines():
        line = _LIST_MARK.sub("", line).strip()
        if line:
            out.append(line)
    return out


@router.post("/scenes/{sid}/shots/bulk")
async def add_shots_bulk(sid: str, body: BulkShotsRequest):
    """Thêm NHIỀU shot vào cuối scene, mỗi dòng của `text` là một prompt.

    Tiêu đề lấy theo đầu prompt chứ không phải "Shot 7": thẻ trên lưới hiện `title`, mà một
    lưới 20 thẻ đánh số thì chẳng nói lên gì — chỗ duy nhất phân biệt được chúng là prompt."""
    await _scene_or_404(sid)
    if body.field not in {"description", "motion_prompt"}:
        raise HTTPException(400, f"field phải là description hoặc motion_prompt, "
                                 f"không phải {body.field!r}")
    prompts = split_bulk_prompts(body.text)
    if not prompts:
        raise HTTPException(400, "Không có dòng nào để thêm")
    if len(prompts) > BULK_SHOTS_MAX:
        raise HTTPException(400, f"{len(prompts)} dòng là quá nhiều "
                                 f"(tối đa {BULK_SHOTS_MAX} shot một lượt)")

    ts = db.now()
    start = await _next_shot_idx(sid)
    ids = []
    for i, prompt in enumerate(prompts):
        shot_id = db.new_id()
        ids.append(shot_id)
        await db.insert("shot", {
            "id": shot_id, "scene_id": sid, "idx": start + i,
            "title": _short_title(prompt) or f"Shot {start + i + 1}",
            "description": "", "ref_entity_ids": "[]", "duration": 8,
            "status": "pending", "created_at": ts, "updated_at": ts,
            body.field: prompt})
    return {"added": len(ids), "ids": ids,
            "shots": await db.query_all(
                "SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,))}


def _short_title(prompt: str) -> str:
    """Tiêu đề thẻ từ prompt: cắt ở ranh giới TỪ, không cắt giữa chữ."""
    p = " ".join((prompt or "").split())
    if len(p) <= 42:
        return p
    cut = p[:42]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > 20 else cut) + "…"


@router.post("/shots/{sid}/insert")
async def insert_shot(sid: str):
    cur = await _shot_or_404(sid)
    ts = db.now()
    # đẩy idx các shot sau lên 1
    await db.execute("UPDATE shot SET idx = idx + 1 WHERE scene_id=? AND idx > ?",
                     (cur["scene_id"], cur["idx"]))
    shot_id = db.new_id()
    await db.insert("shot", {
        "id": shot_id, "scene_id": cur["scene_id"], "idx": cur["idx"] + 1,
        "title": "Shot", "description": "", "ref_entity_ids": "[]", "duration": 8,
        "status": "pending", "created_at": ts, "updated_at": ts})
    return await _shot_or_404(shot_id)


class ReorderRequest(BaseModel):
    order: list[str]   # ids in the desired order


@router.post("/scenes/{sid}/shots/reorder")
async def reorder_shots(sid: str, body: ReorderRequest):
    """Đặt lại thứ tự shot trong scene theo danh sách id (idx = vị trí)."""
    await _scene_or_404(sid)
    ts = db.now()
    for i, shot_id in enumerate(body.order):
        await db.execute("UPDATE shot SET idx=?, updated_at=? WHERE id=? AND scene_id=?",
                         (i, ts, shot_id, sid))
    return {"shots": await db.query_all(
        "SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,))}


@router.post("/projects/{pid}/scenes/reorder")
async def reorder_scenes(pid: str, body: ReorderRequest):
    """Đặt lại thứ tự scene trong dự án theo danh sách id (idx = vị trí)."""
    await _project_or_404(pid)
    for i, scene_id in enumerate(body.order):
        await db.execute("UPDATE scene SET idx=? WHERE id=? AND project_id=?",
                         (i, scene_id, pid))
    # the source→scene alignment is order-dependent → stale after a reorder; clear so the next
    # build re-aligns the narration to the new scene order.
    await db.execute("UPDATE scene SET source_segment=NULL WHERE project_id=?", (pid,))
    return {"scenes": await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))}


@router.post("/scenes/{sid}/split")
async def split_scene(sid: str, target_secs: float = TARGET_SCENE_SECS):
    """Split ONE over-long scene into several shorter sub-scenes (~target_secs each) BY TIME, so
    a whole-chapter-in-one-scene becomes manageable and each part gets its own coherent shot plan.

    Sub-scenes INHERIT the parent's EXACT location — same heading location text AND
    location_entity_id — so a split never re-guesses the place and can't land on the wrong
    location. The scene's existing shots are cleared (rebuild via 'Dựng theo lời đọc')."""
    scene = await _scene_or_404(sid)
    pid = scene["project_id"]
    voiceover = (scene.get("source_segment") or "").strip()
    if not voiceover:
        await _ensure_source_segments(pid)
        scene = await _scene_or_404(sid)
        voiceover = (scene.get("source_segment") or scene.get("action") or "").strip()
    if not voiceover:
        raise HTTPException(400, "Scene chưa có nội dung để tách.")

    est = _estimate_narration_secs(voiceover)
    n = max(1, round(est / max(20.0, target_secs)))
    if n < 2:
        raise HTTPException(
            400, f"Scene chỉ ~{int(est)}s — chưa cần tách (ngưỡng ~{int(target_secs)}s/scene).")
    chunks = [c.strip() for c in brain.partition_text(voiceover, n) if c.strip()]
    if len(chunks) < 2:
        raise HTTPException(400, "Không tách được (quá ít câu trong scene).")
    n = len(chunks)

    base_idx = scene["idx"]
    ts = db.now()
    # make room for n-1 new scenes right after this one
    await db.execute("UPDATE scene SET idx = idx + ? WHERE project_id=? AND idx > ?",
                     (n - 1, pid, base_idx))
    # the parent keeps its location + heading (part 1/n), takes the first slice; its shots are
    # now stale (the narration it covered is spread across the parts)
    await db.execute("DELETE FROM shot WHERE scene_id=?", (sid,))
    await db.update("scene", sid, {
        "heading": _part_heading(scene["heading"], 1, n),
        "source_segment": chunks[0], "action": chunks[0],
        "narration_text": None, "narration_path": None, "narration_duration": None})
    for i in range(1, n):
        await db.insert("scene", {
            "id": db.new_id(), "project_id": pid, "idx": base_idx + i,
            "heading": _part_heading(scene["heading"], i + 1, n),
            "slug": scene.get("slug"), "action": chunks[i], "dialog": None,
            "location_entity_id": scene.get("location_entity_id"),   # SAME place as the parent
            "source_segment": chunks[i], "source_start": None, "source_end": None,
            "created_at": ts})
    return {"scenes": await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,)), "split_into": n}


# ─── Project backup: export / import as .zip (§13#5) ──────────

@router.get("/projects/{pid}/export-zip")
async def export_project_zip(pid: str):
    """Đóng gói dự án (rows DB + media local) thành .zip để sao lưu / chuyển máy."""
    project = await _project_or_404(pid)
    scenes = await db.query_all("SELECT * FROM scene WHERE project_id=? ORDER BY idx", (pid,))
    shots: list[dict] = []
    for sc in scenes:
        shots += await db.query_all(
            "SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sc["id"],))
    entities = await db.query_all("SELECT * FROM entity WHERE project_id=?", (pid,))
    manifest = {"version": 1, "project": project, "scenes": scenes,
                "shots": shots, "entities": entities}

    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        media_dir = media_store.MEDIA_DIR / pid
        if media_dir.exists():
            for f in media_dir.iterdir():
                if f.is_file():
                    zf.write(f, f"media/{f.name}")
        bgm = (project.get("bgm_path") or "").strip()
        if bgm and Path(bgm).exists():
            zf.write(bgm, f"bgm/{Path(bgm).name}")

    safe = "".join(c if (c.isalnum() or c in "-_.") else "_"
                   for c in (project.get("title") or "project"))[:50] or "project"
    return Response(
        content=buf.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe}.zip"'})


@router.post("/projects/import-zip")
async def import_project_zip(file: UploadFile = File(...)):
    """Nhập dự án từ .zip đã export: tạo project MỚI (id mới), khôi phục media local +
    rows DB. Giữ flow_project_id cũ (có thể cần re-link Flow), media hiển thị từ file local."""
    import io
    import zipfile
    data = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(zf.read("manifest.json"))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"File .zip không hợp lệ: {e}")

    old_proj = manifest.get("project") or {}
    old_pid = old_proj.get("id")
    if not old_pid:
        raise HTTPException(400, "manifest thiếu thông tin project")
    new_pid = db.new_id()
    ts = db.now()

    # khôi phục media → ./media/<new_pid>/
    dest = media_store.MEDIA_DIR / new_pid
    dest.mkdir(parents=True, exist_ok=True)
    for name in zf.namelist():
        if name.startswith("media/") and not name.endswith("/"):
            (dest / Path(name).name).write_bytes(zf.read(name))
    new_bgm = None
    for name in zf.namelist():
        if name.startswith("bgm/") and not name.endswith("/"):
            bdir = assembler.STUDIO_MEDIA_DIR / new_pid
            bdir.mkdir(parents=True, exist_ok=True)
            bp = bdir / Path(name).name
            bp.write_bytes(zf.read(name))
            new_bgm = str(bp)

    def remap(v):
        if isinstance(v, str) and f"/media/{old_pid}/" in v:
            return v.replace(f"/media/{old_pid}/", f"/media/{new_pid}/")
        return v

    # entities first (ref_entity_ids + location_entity_id reference these ids)
    ent_map: dict[str, str] = {}
    for e in manifest.get("entities", []):
        nid = db.new_id()
        ent_map[e["id"]] = nid
        row = {k: remap(v) for k, v in e.items()}
        row.update({"id": nid, "project_id": new_pid, "created_at": ts, "updated_at": ts})
        await db.insert("entity", row)

    proj = {k: remap(v) for k, v in old_proj.items()}
    proj.update({"id": new_pid, "bgm_path": new_bgm,
                 "title": (old_proj.get("title") or "Imported") + " (nhập)",
                 # Chủ sở hữu là người ĐANG nhập, không phải account ghi trong file zip.
                 "account_id": await accounts.current_id(),
                 "created_at": ts, "updated_at": ts})
    await db.insert("project", proj)

    sc_map: dict[str, str] = {}
    for sc in manifest.get("scenes", []):
        nid = db.new_id()
        sc_map[sc["id"]] = nid
        row = {k: remap(v) for k, v in sc.items()}
        row.update({"id": nid, "project_id": new_pid})
        if row.get("location_entity_id"):
            row["location_entity_id"] = ent_map.get(row["location_entity_id"])
        await db.insert("scene", row)

    for sh in manifest.get("shots", []):
        nsid = sc_map.get(sh.get("scene_id"))
        if not nsid:
            continue
        row = {k: remap(v) for k, v in sh.items()}
        row.update({"id": db.new_id(), "scene_id": nsid})
        try:
            ids = json.loads(row.get("ref_entity_ids") or "[]")
            row["ref_entity_ids"] = json.dumps([ent_map.get(i, i) for i in ids])
        except (json.JSONDecodeError, TypeError):
            pass
        await db.insert("shot", row)

    return await db.query_one("SELECT * FROM project WHERE id=?", (new_pid,))


@router.patch("/shots/{sid}")
async def update_shot(sid: str, body: UpdateShotRequest):
    await _shot_or_404(sid)
    data = body.model_dump(exclude_none=True)
    if "ref_entity_ids" in data:
        data["ref_entity_ids"] = json.dumps(data["ref_entity_ids"])
    data["updated_at"] = db.now()
    await db.update("shot", sid, data)
    return await _shot_or_404(sid)


@router.delete("/shots/{sid}")
async def delete_shot(sid: str):
    row = await _shot_or_404(sid)
    await db.delete("shot", sid)
    for p in (row.get("image_path"), row.get("image_hires_path"),
              row.get("video_path"), row.get("upscale_path")):
        if p:
            f = media_store.MEDIA_DIR / p.replace("/media/", "", 1)
            if f.exists():
                f.unlink(missing_ok=True)
    return {"ok": True}


@router.post("/shots/{sid}/image")
async def generate_shot_image(sid: str):
    shot = await _shot_or_404(sid)
    return await _generate_frame_image(shot)


@router.put("/shots/{sid}/image-from-media")
async def set_shot_image(sid: str, body: SetMediaRequest):
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    web = await media_store.ensure_local(body.media_id, scene["project_id"])
    if not web:
        raise HTTPException(404, "media_id không hợp lệ hoặc không tồn tại trên Flow")
    await db.update("shot", sid, {
        "image_media_id": body.media_id, "image_primary_id": body.media_id,
        "image_path": web, "updated_at": db.now()})
    return await _shot_or_404(sid)


@router.post("/scenes/{sid}/storyboard/generate-all")
async def generate_scene_images(sid: str, force: bool = False):
    scene = await _scene_or_404(sid)
    shots = await db.query_all("SELECT * FROM shot WHERE scene_id=? ORDER BY idx", (sid,))
    return _start_image_job(scene["project_id"], shots, force, "storyboard")


def _slug(s: str) -> str:
    """Filename-safe slug (keeps Vietnamese diacritics, spaces → '-')."""
    import re as _re
    s = (s or "").strip().lower()
    s = _re.sub(r"\s+", "-", s)
    s = _re.sub(r'[\\/:*?"<>|\r\n\t]+', "", s)
    s = _re.sub(r"-{2,}", "-", s).strip("-")
    return s[:60] or "shot"


@router.get("/shots/{sid}/image/download")
async def download_shot_image(sid: str, hires_first: bool = True):
    """Tải ảnh của MỘT shot ở độ phân giải cao nhất tài khoản cho phép.

    Bản `image_path` mà app hiển thị chỉ là HD — đủ để xem, thiếu hẳn chi tiết khi đem ra
    ngoài. Nút ⬇ trước đây trả đúng bản HD đó, nên tài khoản Ultra tải về vẫn là ảnh nhỏ
    trong khi Flow sẵn sàng phát bản 4K miễn phí. Endpoint này lo nốt phần còn thiếu: chưa
    có bản hi-res (hoặc bản cũ thuộc về ảnh đã bị regen) thì xin Flow ngay rồi mới trả file.

    Upsample ảnh KHÔNG trừ credit nên không cần hỏi trước, và hỏng thì vẫn trả bản HD — nút
    tải về không được phép chết chỉ vì Flow bận."""
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    if not shot.get("image_path"):
        raise HTTPException(404, "Shot chưa có ảnh")

    if hires_first and hires.is_stale(shot) and get_flow_client().connected:
        try:
            await hires.upscale_shot(shot, project, await _current_tier_for(project))
            shot = await _shot_or_404(sid)
        except RuntimeError as e:
            logger.warning("Tải ảnh hi-res cho shot %s hỏng, trả bản HD: %s", sid[:8], e)

    path = hires.path_for(shot) or shot["image_path"]
    f = _media_abs(path)
    if not f or not f.exists():
        raise HTTPException(404, "Không tìm thấy file ảnh")
    res = shot.get("image_hires_res") if path == shot.get("image_hires_path") else None
    suffix = f"-{hires.res_label(res)}" if res else ""
    desc = _slug(shot.get("description") or shot.get("title") or "")
    name = f"sc{scene['idx']+1:03d}-s{shot['idx']+1:03d}-{desc}{suffix}{f.suffix or '.png'}"
    return FileResponse(f, filename=name)


@router.get("/projects/{pid}/storyboard/export")
async def export_storyboard_images(pid: str):
    """Đóng gói toàn bộ ảnh storyboard thành .zip, đặt tên scXXX-sXXX-mô-tả.png."""
    project = await _project_or_404(pid)
    shots = await db.query_all(
        "SELECT sh.*, sc.idx AS scene_idx FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? AND sh.image_path IS NOT NULL ORDER BY sc.idx, sh.idx", (pid,))
    if not shots:
        raise HTTPException(400, "Chưa có ảnh storyboard nào để export")

    out_dir = assembler.STUDIO_MEDIA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "storyboard_images.zip"

    def _build():
        import zipfile
        used: set[str] = set()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for sh in shots:
                # Bản 2K/4K nếu có (đây là đường tải ảnh ra ngoài), không thì bản HD.
                src = assembler.shot_image_path(sh)
                if not src:
                    continue
                ext = src.suffix.lower() or ".png"
                desc = _slug(sh.get("description") or sh.get("title") or "")
                name = f"sc{sh['scene_idx']+1:03d}-s{sh['idx']+1:03d}-{desc}{ext}"
                # tránh trùng tên
                base, i = name, 2
                while name in used:
                    name = base[:-len(ext)] + f"-{i}{ext}"
                    i += 1
                used.add(name)
                zf.write(src, name)
        return len(used)

    n = await asyncio.to_thread(_build)
    if not n:
        raise HTTPException(400, "Không có file ảnh local hợp lệ để export")
    fname = f"{_slug(project['title'])}-storyboard.zip"
    return FileResponse(zip_path, media_type="application/zip", filename=fname)


@router.post("/projects/{pid}/storyboard/generate-all")
async def generate_project_images(pid: str, force: bool = False):
    await _project_or_404(pid)
    shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? ORDER BY sc.idx, sh.idx", (pid,))
    return _start_image_job(pid, shots, force, "storyboard")


def _start_image_job(pid: str, shots: list[dict], force: bool, type_: str) -> dict:
    """Enqueue a background job that generates storyboard frame images (§9). Frames are
    generated in concurrent batches (IMAGE_BATCH_SIZE sharing one Flow batch id) with a cooldown
    between batches, so a 400-frame storyboard finishes ~batch-fold faster than one-at-a-time."""
    todo = [s for s in shots if force or not s.get("image_path")]

    async def _worker(s, batch_id):
        await _generate_frame_image(s, batch_id=batch_id)

    job = get_job_manager().start(
        project_id=pid, type_=type_, items=todo, worker=_worker,
        label=f"Sinh ảnh storyboard ({len(todo)})",
        throttle=IMAGE_BATCH_COOLDOWN, batch_size=IMAGE_BATCH_SIZE,
        stagger=IMAGE_BATCH_STAGGER,
        item_label=lambda s: s.get("title") or s["id"])
    return {"job_id": job.id, "total": len(todo)}


# ─── Ảnh độ phân giải cao (2K/4K) ───────────────────────────
# Flow chỉ phát bản HD qua URL media; bản 2K/4K phải xin riêng qua upsampleImage và trần
# độ phân giải phụ thuộc tier (ONE → 2K, TWO → 4K). Bản hi-res chỉ dùng khi dựng video từ
# ảnh / export DaVinci — app vẫn hiển thị bản HD cho nhẹ.

@router.get("/projects/{pid}/hires/status")
async def hires_status(pid: str):
    """Đếm số ảnh đã/chưa có bản hi-res + độ phân giải tier hiện tại cho phép."""
    project = await _project_or_404(pid)
    shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? AND sh.image_media_id IS NOT NULL", (pid,))
    tier = await _current_tier_for(project)
    resolution = hires.res_for_tier(tier)
    missing = [s for s in shots if hires.is_stale(s)]
    return {
        "tier": tier, "resolution": resolution, "label": hires.res_label(resolution).upper(),
        "total": len(shots), "done": len(shots) - len(missing), "missing": len(missing),
    }


@router.post("/shots/{sid}/hires")
async def generate_shot_hires(sid: str, force: bool = False):
    """Tải bản hi-res cho ảnh của MỘT shot (nút thủ công / tải bù khi tự động hỏng)."""
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    _require_extension()
    if not force and not hires.is_stale(shot):
        return shot
    try:
        await hires.upscale_shot(shot, project, await _current_tier_for(project))
    except RuntimeError as e:
        raise HTTPException(502, f"Tải ảnh 2K/4K thất bại: {e}") from e
    return await _shot_or_404(sid)


@router.post("/projects/{pid}/hires/generate-all")
async def generate_project_hires(pid: str, force: bool = False):
    """Tải bù bản hi-res cho mọi ảnh storyboard còn thiếu (hoặc tất cả khi force)."""
    project = await _project_or_404(pid)
    _require_extension()
    shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? AND sh.image_media_id IS NOT NULL ORDER BY sc.idx, sh.idx", (pid,))
    todo = [s for s in shots if force or hires.is_stale(s)]
    tier = await _current_tier_for(project)
    label = hires.res_label(hires.res_for_tier(tier)).upper()

    async def _worker(s):
        await hires.upscale_shot(s, project, tier)

    # Mỗi lần upsample tốn một captcha và trả về vài MB base64 → chạy tuần tự, giãn như các
    # lệnh sinh ảnh khác để không dính anti-abuse.
    job = get_job_manager().start(
        project_id=pid, type_="hires", items=todo, worker=_worker,
        label=f"Tải ảnh {label} ({len(todo)})", throttle=(3.0, 6.0),
        item_label=lambda s: s.get("title") or s["id"])
    return {"job_id": job.id, "total": len(todo), "resolution": label}


# ─── Shots (video) ──────────────────────────────────────────

def _extract_video_submit(payload: dict) -> dict:
    media = (payload.get("media") or [{}])[0]
    wf = (payload.get("workflows") or [{}])[0]
    return {
        "media_id": media.get("name"),
        "workflow_id": wf.get("name"),
        "primary_media_id": wf.get("metadata", {}).get("primaryMediaId"),
    }


async def _poll_video(client, media_id: str, flow_project_id: str,
                      timeout: float = VIDEO_POLL_TIMEOUT, interval: float = 8):
    """Chờ video render xong → URL, hoặc None khi hết giờ. Raise videopoll.VideoFailed nếu
    Flow báo hỏng hẳn. Chỉ là vỏ mỏng quanh `videopoll.poll_video` — giữ tên cũ vì hires
    nhận hàm này làm callback.

    Thời gian chờ mặc định VIDEO_POLL_TIMEOUT (420s): một clip Omni Flash 10s thường chạy
    quá 4 phút, bỏ cuộc sớm rất đắt vì Flow vẫn render tiếp bản đã tính tiền."""
    return await videopoll.poll_video(client, media_id, flow_project_id, timeout, interval)


CLIP_MAX_S = 8  # one Veo i2v clip ≈ 8s; longer beats are rendered as chained sub-clips

# Engine chạy r2v: ảnh frame đi vào làm REFERENCE chứ không phải start image, nên chúng cần
# thêm entity reference của shot để token `{Tên}` trong motion_prompt bind được.
_R2V_ENGINES = {"omni", "veo_lite"}


def _video_engine(project: dict) -> tuple[str, int]:
    """('omni'|'veo_lite'|'veo', độ dài tối đa MỘT clip) theo ⚙ Cấu hình dự án.

    Luật nằm trong graph.video_engine — node editor cũng đọc từ đó, nên hai đường không bao
    giờ chạy hai engine khác nhau cho cùng một dự án."""
    return graph_mod.video_engine(project)


def _engine_kw(project: dict) -> dict:
    """kwargs {engine, clip_s} cho các hàm sinh prompt của brain — quyết định motion prompt
    được viết dạng MỘT câu (Veo) hay dạng nhiều mốc thời gian `[mm:ss]` (Omni Flash).

    Veo Lite đi cùng nhóm Veo ở đây: nó vẫn là một cú máy liền mạch trong 4-8s, mốc thời gian
    chỉ hợp với clip Omni dài tới 10s."""
    engine, clip_s = _video_engine(project)
    # `project` đi kèm để brain lấy được bản ghi đè của các prompt ngầm (CINEMATOGRAPHY,
    # MOTION, mốc thời gian Omni) — xem brain.PROMPT_DEFAULTS.
    return {"engine": "omni" if engine == "omni" else "veo", "clip_s": clip_s,
            "project": project}


def _video_prompt(project: dict, shot: dict, motion: str) -> str:
    """Prompt cuối cùng gửi cho model video trên đường KHÔNG qua đồ thị.

    Trước đây `motion_prompt` được gửi THÔ, nên video không nhận được style/culture, không
    nhận prompt header/footer, và nhất là không nhận câu về ngôn ngữ chữ — model tự bịa biển
    hiệu tiếng Trung vào mọi cảnh phố. Đi qua compose_prompt(media="video") cho giống hệt
    node "Tạo video" trong Node Editor (xem graph.run_graph)."""
    return brain.compose_prompt(
        project, motion, media="video",
        **graph_mod.prompt_wrap(shot.get("video_graph_json"), project))


def _clip_submit(client, project: dict, shot_id: str, prompt: str,
                 start_media_id: str, engine: str, duration_s: int, tier: str,
                 refs: list[dict] | None = None, batch_id: str | None = None):
    """Callable submit một clip theo engine đã chọn.

    Veo là i2v (ảnh frame làm START image); Omni Flash là r2v (không có start image) nên ảnh
    frame đi vào làm REFERENCE, kèm các entity reference của shot.

    Veo 3.1 Lite [Lower Priority] cũng là r2v ("inference") — cùng lý do như Omni: nó bind
    được token entity, thứ Veo i2v không làm được. Đổi lại nó xếp hàng ưu tiên thấp nên clip
    lâu hơn, bù lại KHÔNG trừ credit.

    `refs` QUAN TRỌNG với Omni: motion_prompt chứa token `{Tên entity}`, và chỉ khi truyền
    references thì chúng mới được bind thành reference part; không có nó thì dấu ngoặc nhọn
    lọt thẳng vào structuredPrompt dưới dạng text thô."""
    # Ảnh frame đứng đầu (mỏ neo thị giác của shot), rồi tới entity refs để bind token.
    # `start_media_id` RỖNG là hợp lệ với hai engine r2v: shot chưa có frame (vd thêm hàng
    # loạt từ text) vẫn render được bằng đường text-to-video, miễn là đừng nhét một reference
    # media_id=None vào request. Veo i2v thì không — nó bắt buộc có start image, xem
    # `_shot_video_blocker`.
    frame_ref = [{"handle": "frame", "media_id": start_media_id}] if start_media_id else []
    r2v_refs = frame_ref + [
        r for r in (refs or []) if r.get("media_id") != start_media_id]
    start_ids = [start_media_id] if start_media_id else []
    if engine == "omni":
        return lambda: client.generate_video_omni(
            prompt=prompt, project_id=project["flow_project_id"],
            reference_media_ids=start_ids, duration_s=duration_s,
            aspect_ratio=project["aspect_ratio"], user_paygate_tier=tier,
            references=r2v_refs or None, batch_id=batch_id)
    if engine == "veo_lite":
        return lambda: client.generate_video_veo_lite(
            prompt=prompt, project_id=project["flow_project_id"], scene_id=shot_id,
            reference_media_ids=start_ids, duration_s=duration_s,
            aspect_ratio=project["aspect_ratio"], user_paygate_tier=tier,
            references=r2v_refs or None, batch_id=batch_id)
    return lambda: client.generate_video(
        start_image_media_id=start_media_id, prompt=prompt,
        project_id=project["flow_project_id"], scene_id=shot_id,
        aspect_ratio=project["aspect_ratio"], user_paygate_tier=tier, batch_id=batch_id)


def _engine_model_key(engine: str, clip_s: int, tier: str, aspect: str) -> str | None:
    """Model key ĐÃ DÙNG THẬT, để ghi vào `shot.video_model`.

    Không có nó thì "đặt Veo Lite mà ra Veo trả tiền" chỉ phát hiện được bằng cách mở Flow lên
    xem — mà đó đúng là thứ tốn credit."""
    if engine == "omni":
        return OMNI_FLASH_MODELS.get(str(clip_s))
    if engine == "veo_lite":
        return VEO_LITE_MODELS.get("reference_frame_2_video")
    return VIDEO_MODELS.get(tier, {}).get("frame_2_video", {}).get(aspect)


async def _render_clip(client, project: dict, shot_id: str, submit, name: str) -> dict:
    """Submit one clip via `submit()`, poll, download to media/<pid>/<media_id>.mp4. Retries
    on block/transient. Returns {media_id, primary_media_id, workflow_id, web, local}."""
    last = ""
    attempt = 0
    max_attempts = VIDEO_GEN_RETRIES
    while attempt < max_attempts:
        attempt += 1
        res = await submit()
        blocked = _is_abuse_block(res)
        if res.get("error"):
            last = str(res["error"])
        else:
            info = _extract_video_submit(res.get("data", res))
            if not info.get("media_id"):
                last = _image_block_reason(res.get("data", res)) or "Flow không trả media"
            else:
                try:
                    url = await _poll_video(client, info["media_id"],
                                            project.get("flow_project_id") or "")
                except videopoll.VideoFailed as ex:
                    # Flow báo hỏng HẲN (lọc nội dung…) — chờ thêm vô ích. Vẫn cho thử lại
                    # như một lượt bị chặn: seed khác đôi khi qua được.
                    last, blocked = f"Flow báo hỏng: {ex}", True
                else:
                    if not url:
                        # KHÔNG re-submit: hết giờ chờ nghĩa là Flow VẪN ĐANG render bản đã
                        # tính tiền, không phải nó hỏng. Submit lại chỉ tốn thêm credit cho
                        # một bản thứ hai rồi lại bỏ rơi cả hai. Ghi operation để hồi phục.
                        await db.update("shot", shot_id, {
                            "operation_json": json.dumps({**info, "name": name,
                                                          "submitted_at": db.now()}),
                            "updated_at": db.now()})
                        raise HTTPException(
                            504, f"Video vẫn đang render trên Flow (quá "
                                 f"{VIDEO_POLL_TIMEOUT:.0f}s chờ). KHÔNG tạo lại (tránh tốn "
                                 f"credit lần nữa) — bấm 'Lấy lại video' để lấy bản đang "
                                 f"render về.")
                    if info.get("workflow_id"):
                        try:
                            await client.change_display_name(
                                info["workflow_id"], project["flow_project_id"], name)
                        except Exception:
                            pass
                    web = await media_store.save_from_url(
                        info["media_id"], project["id"], "mp4", url)
                    if web:
                        return {**info, "web": web, "local": assembler._local(web)}
                    last = "tải video về lỗi"
        # A block gets a long backoff + a few extra tries (so it doesn't burn the normal budget).
        if blocked and max_attempts < VIDEO_GEN_RETRIES + ABUSE_EXTRA_RETRIES:
            max_attempts += 1
        logger.warning("clip %s hỏng (lần %d/%d%s): %s", shot_id[:6], attempt, max_attempts,
                       " · BLOCK, chờ lâu" if blocked else "", last)
        if attempt < max_attempts:
            await asyncio.sleep(random.uniform(*(ABUSE_BLOCK_BACKOFF if blocked else (5, 10))))
    raise HTTPException(502, f"Tạo clip thất bại sau {attempt} lần: {last}")


async def _chained_video(shot: dict, scene: dict, project: dict, client, n: int,
                         engine: str = "veo", clip_max: int = CLIP_MAX_S,
                         batch_id: str | None = None) -> dict:
    """Storytelling beat > one clip: render `n` chained sub-clips (each continues from the
    previous clip's last frame, motion flows on) and concat them into the shot's video."""
    tier = await _current_tier()
    motion = shot.get("motion_prompt") or shot.get("visual_prompt") or shot.get("description") or ""
    motions = [motion]
    try:
        pp = await brain.run_json(brain.beat_parts_prompt(
            shot.get("beat_action") or motion, motion, n, clip_max, engine, project))
        parts = pp.get("parts") if isinstance(pp, dict) else None
        if parts:
            motions = [p.get("motion_prompt") or motion
                       for p in sorted(parts, key=lambda x: x.get("part_idx", 0))]
    except Exception as ex:  # noqa: BLE001
        logger.warning("beat_parts failed: %s", ex)
    while len(motions) < n:
        motions.append(motion)

    out_dir = assembler.STUDIO_MEDIA_DIR / project["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    start_media = shot["image_media_id"]
    refs = await _build_frame_references(shot, scene) if engine in _R2V_ENGINES else None
    clips, first = [], None
    for k in range(n):
        name = f"s{scene['idx']+1:02d}_{shot['idx']+1:02d}_p{k+1}_vid"
        submit = _clip_submit(client, project, shot["id"],
                              _video_prompt(project, shot, motions[k]), start_media,
                              engine, clip_max, tier, refs, batch_id)
        info = await _render_clip(client, project, shot["id"], submit, name)
        first = first or info
        clips.append(info["local"])
        if k < n - 1:  # chain: last frame of this clip → uploaded start image for the next
            frame = out_dir / f"chain_{shot['id']}_{k}.jpg"
            if await assembler.extract_last_frame(info["local"], frame):
                import base64
                up = await client.upload_image(
                    base64.b64encode(frame.read_bytes()).decode(), "image/jpeg",
                    project["flow_project_id"], frame.name)
                if up.get("_mediaId"):
                    start_media = up["_mediaId"]
                else:
                    logger.warning("upload_image cho chain thất bại — dùng lại frame gốc")

    final = out_dir / f"shot_{shot['id']}_chain.mp4"
    await assembler.concat_videos(clips, final)
    web = f"/studio-media/{project['id']}/{final.name}"
    await db.update("shot", shot["id"], {
        "video_media_id": first["media_id"], "video_primary_id": first.get("primary_media_id"),
        "video_workflow_id": first.get("workflow_id"), "video_path": web,
        "video_model": _engine_model_key(engine, clip_max, tier, project["aspect_ratio"]),
        "status": "done", "updated_at": db.now()})
    return await _shot_or_404(shot["id"])


def _shot_video_blocker(shot: dict, engine: str, clip_max: int) -> str | None:
    """Lý do shot này KHÔNG render video được, hoặc None nếu render được.

    Shot chưa có ảnh frame KHÔNG còn là lỗi ở mọi engine: Omni Flash và Veo Lite đều có
    đường text-to-video (endpoint + model key riêng, xem flow_client). Chỉ hai chỗ thật sự
    cần ảnh:
      • Veo trả tiền — i2v, `startImage` là bắt buộc;
      • beat dài hơn MỘT clip — nối clip nghĩa là lấy khung cuối clip trước làm ảnh đầu clip
        sau, không có ảnh mở màn thì chuỗi ấy không bắt đầu được.
    Một chỗ duy nhất giữ luật này để ⚡ từng shot và ✦ sinh hàng loạt không lệch nhau: bên
    lọc trước, bên báo lỗi, mà lệch thì batch lẳng lặng bỏ qua đúng những shot ⚡ vẫn chạy."""
    if shot.get("image_media_id"):
        return None
    dur = float(shot.get("duration") or 0)
    if dur > clip_max:
        n = math.ceil(dur / clip_max)
        return (f"Shot dài {dur:g}s phải cắt thành {n} clip nối nhau, mà mối nối lấy khung "
                f"cuối clip trước làm ảnh đầu clip sau — cần ảnh frame. Tạo ảnh ở Storyboard "
                f"trước, hoặc hạ thời lượng shot xuống ≤ {clip_max}s.")
    if engine == "veo":
        return ("Veo i2v cần ảnh frame — tạo ảnh ở Storyboard trước, hoặc đổi engine video "
                "sang Veo 3.1 Lite / Omni Flash trong ⚙ Cấu hình dự án để render chỉ từ "
                "prompt (text-to-video).")
    return None


async def _generate_shot_video(shot: dict, batch_id: str | None = None) -> dict:
    """`batch_id`: khi job ✦ chạy theo lô, cả lô dùng CHUNG một `mediaGenerationContext
    .batchId` — đúng như Flow UI làm khi bấm tạo nhiều video một lượt."""
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    client = _require_extension()
    # Engine + độ dài tối đa một clip do Cấu hình dự án quyết định (Veo i2v 8s mặc định, hoặc
    # Omni Flash 4/6/8/10s). Beat dài hơn một clip → chained sub-clips phủ hết beat; với Omni
    # 10s thì một beat 10s chỉ cần MỘT clip thay vì hai clip Veo nối nhau.
    engine, clip_max = _video_engine(project)
    blocked = _shot_video_blocker(shot, engine, clip_max)
    if blocked:
        raise HTTPException(400, blocked)
    await db.update("shot", shot["id"], {"status": "running", "updated_at": db.now()})

    dur = float(shot.get("duration") or 0)
    n = max(1, math.ceil(dur / clip_max)) if dur > clip_max else 1
    tier = await _current_tier()
    try:
        if n > 1:
            # Beat dài hơn một clip: phải cắt thành nhiều sub-clip rồi nối — đồ thị chỉ mô tả
            # MỘT clip nên nhánh này không đi qua graph được.
            return await _chained_video(shot, scene, project, client, n, engine, clip_max,
                                        batch_id)
        out = await _gen_via_graph("shot", shot, project, "video", batch_id=batch_id)
        if out:
            row = await _commit_shot_media(shot, scene, project, out["media_id"], "mp4",
                                           out.get("path"))
            if out.get("video_model"):
                await db.update("shot", shot["id"], {"video_model": out["video_model"]})
                row = await _shot_or_404(shot["id"])
            return row
        motion = shot.get("motion_prompt") or shot.get("visual_prompt") or shot.get("description") or ""
        refs = await _build_frame_references(shot, scene) if engine in _R2V_ENGINES else None
        submit = _clip_submit(client, project, shot["id"],
                              _video_prompt(project, shot, motion),
                              shot.get("image_media_id") or "",
                              engine, clip_max, tier, refs, batch_id)
        info = await _render_clip(
            client, project, shot["id"], submit,
            f"s{scene['idx']+1:02d}_{shot['idx']+1:02d}_vid")
        await db.update("shot", shot["id"], {
            "video_media_id": info["media_id"], "video_primary_id": info.get("primary_media_id"),
            "video_workflow_id": info.get("workflow_id"), "video_path": info["web"],
            "video_model": _engine_model_key(engine, clip_max, tier, project["aspect_ratio"]),
            # Lượt treo (nếu có) đã bị thay bằng clip mới này → tắt nút "Lấy lại video".
            "operation_json": None,
            "status": "done", "updated_at": db.now()})
        # Video vừa render chỉ là bản HD. Nếu dự án bật "tự upscale video", kéo bản
        # 1080p/4K ngay (best-effort — hỏng chỉ ghi log, video HD đã có). Chỉ áp dụng cho
        # clip đơn: nhánh chained ở trên không upscale được.
        await _maybe_auto_upscale_video(shot["id"], project)
        return await _shot_or_404(shot["id"])
    except HTTPException:
        await db.update("shot", shot["id"], {"status": "error", "updated_at": db.now()})
        raise


async def _maybe_auto_upscale_video(sid: str, project: dict) -> None:
    """Kéo bản 1080p/4K ngay sau khi shot nhận video MỚI, khi dự án bật 'tự upscale video'.

    Hook này trước đây chỉ nằm trong `_generate_shot_video` (tab Shots), nên video tạo từ
    Node Editor — hoặc gán bằng apply-media / chọn từ ứng viên — không bao giờ được upscale
    dù ô đó đã tích. Best-effort: `hires.auto_upscale_video` tự nuốt lỗi, bản HD đã lưu xong.
    """
    if not project.get("auto_upscale_video"):
        return
    await hires.auto_upscale_video(
        await _shot_or_404(sid), project, await _current_tier_for(project), _poll_video)


@router.post("/shots/{sid}/prompts")
async def gen_shot_prompts(sid: str):
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    out = await brain.run_json(brain.shot_prompts_prompt(
        shot.get("description") or shot.get("title") or "", project["style"],
        **_engine_kw(project)))
    await db.update("shot", sid, {
        "visual_prompt": out.get("visual_prompt"),
        "motion_prompt": out.get("motion_prompt"), "updated_at": db.now()})
    return await _shot_or_404(sid)


@router.post("/shots/{sid}/video")
async def generate_shot_video(sid: str):
    shot = await _shot_or_404(sid)
    return await _generate_shot_video(shot)


@router.post("/shots/{sid}/video/resume")
async def resume_shot_video(sid: str):
    """Lấy về video của một lượt render ĐÃ SUBMIT nhưng hết giờ chờ (operation_json).

    Không submit gì mới — chỉ poll lại operation cũ, nên không tốn thêm credit. Dùng khi
    'Tạo video' báo 504 vì Flow render lâu hơn thời gian chờ."""
    shot = await _shot_or_404(sid)
    try:
        op_info = json.loads(shot.get("operation_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        op_info = {}
    media_id = op_info.get("media_id")
    if not media_id:
        raise HTTPException(400, "Shot không có lượt render nào đang chờ")
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    client = _require_extension()

    try:
        url = await _poll_video(client, media_id, project.get("flow_project_id") or "")
    except videopoll.VideoFailed as ex:
        # Hỏng hẳn thì đừng để nút 'Lấy lại video' treo mãi trên thẻ shot.
        await db.update("shot", sid, {"operation_json": None, "status": "error",
                                      "updated_at": db.now()})
        raise HTTPException(502, f"Flow báo lượt render này hỏng: {ex}")
    if not url:
        raise HTTPException(504, "Video vẫn chưa xong — thử 'Lấy lại video' sau ít phút.")
    if op_info.get("workflow_id") and op_info.get("name"):
        try:
            await client.change_display_name(
                op_info["workflow_id"], project["flow_project_id"], op_info["name"])
        except Exception:
            pass
    web = await media_store.save_from_url(media_id, project["id"], "mp4", url)
    if not web:
        raise HTTPException(502, "Tải video về lỗi")
    await db.update("shot", sid, {
        "video_media_id": media_id, "video_primary_id": op_info.get("primary_media_id"),
        "video_workflow_id": op_info.get("workflow_id"), "video_path": web,
        "operation_json": None, "status": "done", "updated_at": db.now()})
    return await _shot_or_404(sid)


@router.post("/shots/{sid}/upscale")
async def upscale_shot(sid: str, resolution: Optional[str] = None, force: bool = False):
    """Upscale video của MỘT shot. Bỏ trống `resolution` → lấy theo tier (ONE → 1080p,
    TWO → 4K); xin 4K trên tier ONE sẽ bị Flow từ chối."""
    shot = await _shot_or_404(sid)
    if not shot.get("video_media_id"):
        raise HTTPException(400, "Shot chưa có video để upscale")
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    _require_extension()
    if not force and not hires.video_is_stale(shot):
        return shot
    try:
        await hires.upscale_video(shot, project, await _current_tier_for(project),
                                  _poll_video, resolution)
    except RuntimeError as e:
        raise HTTPException(502, f"Upscale video thất bại: {e}") from e
    return await _shot_or_404(sid)


@router.get("/projects/{pid}/upscale/status")
async def upscale_video_status(pid: str):
    """Đếm video đã/chưa upscale + độ phân giải sẽ dùng (trần tier ∩ lựa chọn dự án)."""
    project = await _project_or_404(pid)
    rows = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? AND sh.video_media_id IS NOT NULL", (pid,))
    # Shot chained không upscale được → không tính vào tổng, nếu không "còn thiếu" sẽ
    # không bao giờ về 0.
    shots = [s for s in rows if hires.video_upscalable(s)]
    tier = await _current_tier_for(project)
    resolution = hires.video_res_for_tier(tier, project.get("upscale_res"))
    missing = [s for s in shots if hires.video_is_stale(s)]
    return {
        "tier": tier, "resolution": resolution,
        "label": hires.video_res_label(resolution).upper(),
        "total": len(shots), "done": len(shots) - len(missing), "missing": len(missing),
        "skipped_chained": len(rows) - len(shots),
        # Các mức tier này cho phép — tier TWO chọn được 1080p cho nhẹ/rẻ thay vì luôn 4K.
        "choices": [{"value": r, "label": hires.video_res_label(r).upper()}
                    for r in hires.video_res_choices(tier)],
    }


@router.post("/projects/{pid}/upscale/generate-all")
async def upscale_all_videos(pid: str, force: bool = False):
    """Upscale bù mọi video chưa có bản độ phân giải cao (~1 phút/video)."""
    project = await _project_or_404(pid)
    _require_extension()
    shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? AND sh.video_media_id IS NOT NULL ORDER BY sc.idx, sh.idx", (pid,))
    todo = [s for s in shots
            if hires.video_upscalable(s) and (force or hires.video_is_stale(s))]
    tier = await _current_tier_for(project)
    label = hires.video_res_label(
        hires.video_res_for_tier(tier, project.get("upscale_res"))).upper()

    async def _worker(s):
        await hires.upscale_video(s, project, tier, _poll_video)

    # Mỗi upscale là một lượt render thật (submit + poll ~1 phút) → tuần tự, giãn như
    # generate-all video để không dính anti-abuse.
    job = get_job_manager().start(
        project_id=pid, type_="upscale", items=todo, worker=_worker,
        label=f"Upscale video {label} ({len(todo)})", throttle=(15.0, 30.0),
        item_label=lambda s: s.get("title") or s["id"])
    return {"job_id": job.id, "total": len(todo), "resolution": label}


async def _video_batch_plan(pid: str, force: bool) -> dict:
    """Shot nào sẽ được ✦ sinh hàng loạt render, và shot nào không — kèm lý do.

    Client KHÔNG tự lọc: luật phụ thuộc engine của dự án (`_shot_video_blocker`), chép sang
    đó là sớm muộn lệch — đúng thứ vừa xảy ra khi nút ✦ báo "không có shot nào (có ảnh)"
    trong lúc ⚡ từng shot vẫn render được cả loạt shot chưa có ảnh."""
    project = await _project_or_404(pid)
    engine, clip_max = _video_engine(project)
    shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? ORDER BY sc.idx, sh.idx", (pid,))
    todo, skipped, reasons = [], 0, []
    for sh in shots:
        if not (force or not sh.get("video_path")):
            skipped += 1               # đã có video rồi — không phải "bị chặn"
            continue
        why = _shot_video_blocker(sh, engine, clip_max)
        if why:
            reasons.append(why)
            continue
        todo.append(sh)
    # Lý do gộp lại: 40 shot cùng một lý do thì hiện 40 dòng giống nhau chẳng ích gì.
    uniq = list(dict.fromkeys(reasons))
    return {"todo": todo, "total": len(todo), "engine": engine,
            "have_video": skipped, "blocked": len(reasons), "reasons": uniq[:3]}


@router.get("/projects/{pid}/shots/generate-all/preview")
async def preview_all_videos(pid: str, force: bool = False):
    """Đếm trước ✦ sẽ render bao nhiêu shot (để hỏi credit) mà chưa chạy gì cả."""
    plan = await _video_batch_plan(pid, force)
    return {k: v for k, v in plan.items() if k != "todo"}


@router.post("/projects/{pid}/shots/generate-all")
async def generate_all_videos(pid: str, force: bool = False):
    """✦ Auto gen video cho shot CHƯA có video → job nền (§9). Throttle 15–30s.

    Trước đây lọc cứng "phải có ảnh frame". Nhưng Omni Flash và Veo Lite render được chỉ từ
    prompt, nên với hai engine ấy lọc như cũ là lặng lẽ bỏ qua đúng những shot ⚡ vẫn chạy
    được — vd cả loạt shot vừa thêm từ text. Luật ở `_shot_video_blocker`, chung với ⚡."""
    plan = await _video_batch_plan(pid, force)
    todo = plan["todo"]

    async def _worker(s, batch_id):
        await _generate_shot_video(s, batch_id=batch_id)

    # Theo LÔ như storyboard, nhưng lô nhỏ hơn và giãn hơn hẳn — xem VIDEO_BATCH_SIZE.
    job = get_job_manager().start(
        project_id=pid, type_="videos", items=todo, worker=_worker,
        label=f"Sinh video ({len(todo)})",
        throttle=VIDEO_BATCH_COOLDOWN, batch_size=VIDEO_BATCH_SIZE,
        stagger=VIDEO_BATCH_STAGGER, unit="clip",
        item_label=lambda s: s.get("title") or s["id"])
    return {"job_id": job.id, "total": len(todo), "batch_size": VIDEO_BATCH_SIZE}


# ─── Node Editor graphs ─────────────────────────────────────

class SaveGraphRequest(BaseModel):
    graph: dict
    only_node: str | None = None  # run just this node + upstream (per-node "⚡ tạo nhanh")
    propagate: bool = False        # with only_node: also refresh everything downstream (⏬)


# A shot owns two separate graphs: the storyboard IMAGE graph (graph_json) and the
# shots-tab VIDEO graph (video_graph_json). `goal` selects which column to read/write.
def _shot_graph_col(goal: str | None) -> str:
    return "video_graph_json" if goal == "video" else "graph_json"


@router.get("/shots/{sid}/graph")
async def get_shot_graph(sid: str, goal: str | None = None):
    row = await _shot_or_404(sid)
    col = _shot_graph_col(goal)
    return {"graph": json.loads(row[col]) if row.get(col) else None}


@router.put("/shots/{sid}/graph")
async def put_shot_graph(sid: str, body: SaveGraphRequest, goal: str | None = None):
    await _shot_or_404(sid)
    col = _shot_graph_col(goal)
    await db.update("shot", sid, {col: json.dumps(body.graph), "updated_at": db.now()})
    return {"ok": True}


@router.post("/shots/{sid}/graph/run")
async def run_shot_graph(sid: str, body: SaveGraphRequest, goal: str | None = None):
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    await db.update("shot", sid, {_shot_graph_col(goal): json.dumps(body.graph)})
    project = {**project, "paygate_tier": await _current_tier()}
    try:
        out = await graph_mod.run_graph(body.graph, shot, project, "shot",
                                        only_node=body.only_node, propagate=body.propagate)
    except graph_mod.GraphError as e:
        raise HTTPException(400, str(e))
    # Chỉ lượt chạy đầy đủ mới ghi media lên shot; `only_node` chỉ trả kết quả node, việc
    # gán đi qua apply-media (đã có hook riêng ở đó). Chạy nốt phần hậu kỳ CHUNG với ⚡ tạo
    # nhanh — đổi tên trên Flow, lịch sử phiên bản, auto hi-res/upscale — để hai đường kết
    # thúc giống hệt nhau chứ không chỉ giống nhau ở prompt.
    if not body.only_node and out.get("media_id"):
        await _commit_shot_media(shot, scene, project, out["media_id"],
                                 out.get("ext", "png"), out.get("path"))
    return {**out, "shot": await _shot_or_404(sid)}


@router.get("/entities/{eid}/graph")
async def get_entity_graph(eid: str):
    row = await _entity_or_404(eid)
    return {"graph": json.loads(row["graph_json"]) if row.get("graph_json") else None}


@router.put("/entities/{eid}/graph")
async def put_entity_graph(eid: str, body: SaveGraphRequest):
    await _entity_or_404(eid)
    await db.update("entity", eid, {"graph_json": json.dumps(body.graph), "updated_at": db.now()})
    return {"ok": True}


@router.post("/entities/{eid}/graph/run")
async def run_entity_graph(eid: str, body: SaveGraphRequest):
    entity = await _entity_or_404(eid)
    project = await _project_or_404(entity["project_id"])
    await db.update("entity", eid, {"graph_json": json.dumps(body.graph)})
    project = {**project, "paygate_tier": await _current_tier()}
    try:
        out = await graph_mod.run_graph(body.graph, entity, project, "entity",
                                        only_node=body.only_node, propagate=body.propagate)
    except graph_mod.GraphError as e:
        raise HTTPException(400, str(e))
    # Hậu kỳ chung với ⚡ tạo nhanh (đổi tên trên Flow, lịch sử phiên bản, dán nhãn ô lưới
    # cho location) — run_graph tự làm phần dán nhãn nhưng không làm hai phần kia.
    if not body.only_node and out.get("media_id"):
        await _commit_entity_media(entity, project, out["media_id"], out.get("path"))
    return {**out, "entity": await _entity_or_404(eid)}


@router.get("/projects/{pid}/images")
async def project_images(pid: str):
    """Mọi ẢNH trong project Flow của dự án — cho node 'Nguồn ảnh' tham chiếu toàn bộ ảnh
    (không chỉ asset/storyboard). Trả [{media_id, name, kind}]."""
    project = await _project_or_404(pid)
    if not project.get("flow_project_id"):
        return {"media": []}
    client = _require_extension()
    raw = await client.get_project(project["flow_project_id"])
    return {"media": [m for m in _flow_media_items(raw) if m["kind"] == "image"]}


@router.post("/projects/{pid}/upload-image")
async def upload_image(pid: str, file: UploadFile = File(...)):
    """Tải ảnh từ máy lên Flow (lấy media_id) + lưu local — để dùng làm Nguồn ảnh trong Node
    Editor. Upload lên Flow để ảnh có media_id thật, dùng được làm tham chiếu/edit/video."""
    project = await _project_or_404(pid)
    client = _require_extension()
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "File rỗng")
    import base64
    mime = (file.content_type or "image/png").lower()
    res = await client.upload_image(
        base64.b64encode(raw).decode(), mime_type=mime,
        project_id=project["flow_project_id"], file_name=file.filename or "upload.png")
    if isinstance(res, dict) and res.get("error"):
        raise HTTPException(502, f"Upload lên Flow lỗi: {res['error']}")
    mid = res.get("_mediaId") if isinstance(res, dict) else None
    if not mid:
        raise HTTPException(502, "Flow không trả media_id cho ảnh tải lên")
    ext = "jpg" if ("jpeg" in mime or "jpg" in mime) else "webp" if "webp" in mime else "png"
    rel = f"{pid}/{mid}.{ext}"
    dest = media_store.MEDIA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(dest.write_bytes, raw)
    return {"media_id": mid, "web": f"/media/{rel}", "name": file.filename or mid}


class SaveTemplateRequest(BaseModel):
    name: str
    goal: Optional[str] = None
    graph: dict


@router.get("/graph-templates")
async def list_graph_templates():
    """Các preset (template) sơ đồ node đã lưu — tái dùng nhanh giữa các shot/asset."""
    return {"templates": await db.kv_get("graph_templates", []) or []}


@router.post("/graph-templates")
async def save_graph_template(body: SaveTemplateRequest):
    """Lưu sơ đồ node hiện tại thành preset (ghi đè nếu trùng tên)."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Thiếu tên preset")
    templates = await db.kv_get("graph_templates", []) or []
    templates = [t for t in templates if t.get("name") != name]
    templates.append({"id": db.new_id(), "name": name, "goal": body.goal,
                      "graph": body.graph, "created_at": db.now()})
    await db.kv_set("graph_templates", templates)
    return {"templates": templates}


@router.delete("/graph-templates/{tid}")
async def delete_graph_template(tid: str):
    templates = await db.kv_get("graph_templates", []) or []
    templates = [t for t in templates if t.get("id") != tid]
    await db.kv_set("graph_templates", templates)
    return {"templates": templates}


class SaveSettingsPresetRequest(BaseModel):
    name: str
    settings: dict


@router.get("/settings-presets")
async def list_settings_presets():
    """Preset THIẾT LẬP dự án đã lưu (style, prompt header/footer, model, TTS…) — tái dùng nhanh."""
    return {"presets": await db.kv_get("settings_presets", []) or []}


@router.post("/settings-presets")
async def save_settings_preset(body: SaveSettingsPresetRequest):
    """Lưu thiết lập hiện tại thành preset (ghi đè nếu trùng tên)."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Thiếu tên preset")
    presets = await db.kv_get("settings_presets", []) or []
    presets = [p for p in presets if p.get("name") != name]
    presets.append({"id": db.new_id(), "name": name, "settings": body.settings,
                    "created_at": db.now()})
    await db.kv_set("settings_presets", presets)
    return {"presets": presets}


@router.delete("/settings-presets/{tid}")
async def delete_settings_preset(tid: str):
    presets = await db.kv_get("settings_presets", []) or []
    presets = [p for p in presets if p.get("id") != tid]
    await db.kv_set("settings_presets", presets)
    return {"presets": presets}


class ApplyMediaRequest(BaseModel):
    media_id: str
    ext: str = "png"


async def _flow_workflow_name_for_media(flow_project_id: str, media_id: str) -> Optional[str]:
    """Workflow (theo primaryMediaId) chứa media_id → trả `name` để đổi tên hiển thị. Dùng
    cho media gán bằng node/candidate (apply-media) vốn không giữ workflow_id như auto-gen."""
    if not (flow_project_id and media_id):
        return None
    try:
        raw = await get_flow_client().get_project(flow_project_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("rename: đọc project Flow lỗi: %s", e)
        return None
    data = raw.get("data", raw) if isinstance(raw, dict) else {}
    for w in (_deep_find(data, "workflows") or []):
        if isinstance(w, dict) and (w.get("metadata") or {}).get("primaryMediaId") == media_id:
            return w.get("name")
    return None


async def _rename_flow_media(project: dict, media_id: str, label: str) -> None:
    """Đổi tên hiển thị của media trên Flow (để dễ tìm khi chọn ảnh tham chiếu) — giống
    auto-gen. Bỏ qua nếu project chưa gắn Flow / không tìm thấy workflow tương ứng."""
    fpid = project.get("flow_project_id")
    if not (fpid and media_id and label):
        return
    name = await _flow_workflow_name_for_media(fpid, media_id)
    if not name:
        return
    try:
        await get_flow_client().change_display_name(name, fpid, label[:60])
    except Exception as e:  # noqa: BLE001
        logger.warning("đổi tên media trên Flow lỗi: %s", e)


# Commit một media (kết quả node "tạo nhanh", ứng viên đã chọn, hoặc lượt ⚡ chạy qua graph)
# lên shot/entity. MỘT chỗ duy nhất lo phần hậu kỳ — tải về, ghi DB, lịch sử phiên bản, đổi
# tên trên Flow, auto hi-res/upscale — để mọi đường sinh ảnh kết thúc giống hệt nhau.
async def _commit_shot_media(shot: dict, scene: dict, project: dict,
                             media_id: str, ext: str, web: str | None = None) -> dict:
    col = "video" if ext == "mp4" else "image"
    web = web or await media_store.ensure_local(media_id, project["id"], ext)
    await db.update("shot", shot["id"], {
        f"{col}_media_id": media_id, f"{col}_primary_id": media_id,
        f"{col}_path": web, "updated_at": db.now(),
        # Gán video mới ⇒ lượt render treo (nếu có) không còn ý nghĩa.
        **({"operation_json": None, "status": "done"} if col == "video" else {})})
    await _record_media_history(project["id"], "shot", shot["id"], col, media_id, media_id, web)
    # Đổi tên trên Flow giống auto-gen (s01_03_img / _vid) để dễ tìm khi tham chiếu.
    slot = "vid" if col == "video" else "img"
    await _rename_flow_media(project, media_id,
                             f"s{scene['idx']+1:02d}_{shot['idx']+1:02d}_{slot}")
    if col == "video":
        await _maybe_auto_upscale_video(shot["id"],
                                        {**project, "paygate_tier": await _current_tier()})
    else:
        await _maybe_set_cover(project["id"], project.get("flow_project_id"), media_id)
        if web and project.get("auto_hires"):
            await hires.auto_upscale_shot({**shot, "image_media_id": media_id},
                                          project, await _current_tier())
    return await _shot_or_404(shot["id"])


async def _commit_entity_media(entity: dict, project: dict, media_id: str,
                               web: str | None = None) -> dict:
    web = web or await media_store.ensure_local(media_id, project["id"])
    await db.update("entity", entity["id"], {
        "media_id": media_id, "primary_media_id": media_id,
        "image_path": web, "updated_at": db.now()})
    # A location's media is a 2x2 grid → overlay the position labels for display (same as
    # quick-gen), so node "tạo nhanh" and candidate-pick get labels too. Chế độ một ảnh
    # (location_frames == 1) không có ô nào để dán nhãn.
    if (entity.get("type") == "location" and web
            and brain.location_frames(project) == 4):
        try:
            await _label_location_grid(await _entity_or_404(entity["id"]), project)
        except Exception as ex:  # noqa: BLE001
            logger.warning("location grid labelling failed for %s: %s", entity["id"], ex)
    await _record_media_history(project["id"], "entity", entity["id"], "image",
                                media_id, media_id, web)
    # Đổi tên trên Flow giống auto-gen (type_tên) để dễ tìm khi tham chiếu.
    await _rename_flow_media(project, media_id, f"{entity['type']}_{entity['name']}")
    return await _entity_or_404(entity["id"])


@router.post("/shots/{sid}/apply-media")
async def apply_shot_media(sid: str, body: ApplyMediaRequest):
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    row = await _commit_shot_media(shot, scene, project, body.media_id, body.ext)
    return {"ok": True, "path": row.get("video_path" if body.ext == "mp4" else "image_path"),
            "shot": row}


@router.post("/entities/{eid}/apply-media")
async def apply_entity_media(eid: str, body: ApplyMediaRequest):
    entity = await _entity_or_404(eid)
    project = await _project_or_404(entity["project_id"])
    row = await _commit_entity_media(entity, project, body.media_id)
    return {"ok": True, "path": row.get("image_path"), "entity": row}


@router.get("/shots/{sid}/history")
async def shot_history(sid: str, slot: str = "image"):
    """Lịch sử các phiên bản ảnh/video đã gán cho shot (mới nhất trước)."""
    await _shot_or_404(sid)
    return {"history": await db.query_all(
        "SELECT * FROM media_history WHERE owner_id=? AND slot=? ORDER BY created_at DESC",
        (sid, slot))}


@router.get("/entities/{eid}/history")
async def entity_history(eid: str):
    """Lịch sử các phiên bản ảnh đã gán cho entity (mới nhất trước)."""
    await _entity_or_404(eid)
    return {"history": await db.query_all(
        "SELECT * FROM media_history WHERE owner_id=? AND slot='image' ORDER BY created_at DESC",
        (eid,))}


@router.post("/shots/{sid}/history/{hid}/restore")
async def restore_shot_history(sid: str, hid: str):
    """Khôi phục một phiên bản cũ làm media hiện tại của shot."""
    await _shot_or_404(sid)
    h = await db.query_one("SELECT * FROM media_history WHERE id=?", (hid,))
    if not h or h.get("owner_id") != sid:
        raise HTTPException(404, "Không tìm thấy phiên bản")
    kind = h["slot"]
    await db.update("shot", sid, {
        f"{kind}_media_id": h["media_id"], f"{kind}_primary_id": h["primary_media_id"],
        f"{kind}_path": h["path"], "updated_at": db.now()})
    return await _shot_or_404(sid)


@router.post("/entities/{eid}/history/{hid}/restore")
async def restore_entity_history(eid: str, hid: str):
    """Khôi phục một phiên bản ảnh cũ làm ảnh hiện tại của entity."""
    await _entity_or_404(eid)
    h = await db.query_one("SELECT * FROM media_history WHERE id=?", (hid,))
    if not h or h.get("owner_id") != eid:
        raise HTTPException(404, "Không tìm thấy phiên bản")
    await db.update("entity", eid, {
        "media_id": h["media_id"], "primary_media_id": h["primary_media_id"],
        "image_path": h["path"], "updated_at": db.now()})
    return await _entity_or_404(eid)


class CandidatesRequest(BaseModel):
    n: int = 3   # số ảnh ứng viên (2–4)


@router.post("/entities/{eid}/candidates")
async def entity_candidates(eid: str, body: CandidatesRequest):
    """Sinh N ảnh ứng viên cho entity (không commit) → chọn bản đẹp rồi apply-media (§13#2)."""
    entity = await _entity_or_404(eid)
    project = await _project_or_404(entity["project_id"])
    client = _require_extension()
    body_text = brain.ref_image_prompt(
        entity["type"], entity["name"],
        entity.get("description") or entity.get("ref_prompt") or "", project)
    prompt = brain.compose_prompt(project, body_text)
    aspect = _entity_aspect(entity["type"], project)
    model = await _resolve_image_model(project)
    tier = await _current_tier()
    cands = await _gen_candidates(
        lambda: client.generate_images(
            prompt=prompt, project_id=project["flow_project_id"], aspect_ratio=aspect,
            user_paygate_tier=tier, image_model=model),
        project, max(2, min(4, body.n)))
    return {"candidates": cands}


@router.post("/shots/{sid}/candidates")
async def shot_candidates(sid: str, body: CandidatesRequest):
    """Sinh N ảnh frame ứng viên cho shot (không commit) → chọn rồi apply-media (§13#2)."""
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    client = _require_extension()
    refs = await _build_frame_references(shot, scene)
    prompt = brain.compose_prompt(
        project, shot.get("description") or shot.get("title") or "", single_frame=True)
    aspect = _to_image_aspect(project["aspect_ratio"])
    model = await _resolve_image_model(project)
    tier = await _current_tier()
    cands = await _gen_candidates(
        lambda: client.generate_images(
            prompt=prompt, project_id=project["flow_project_id"], aspect_ratio=aspect,
            user_paygate_tier=tier, references=refs or None, image_model=model,
            dedupe_refs=True),
        project, max(2, min(4, body.n)))
    return {"candidates": cands}


# ─── Assemble / narration / export ──────────────────────────

class NarrationRequest(BaseModel):
    language: Optional[str] = None   # None → dùng script_lang của dự án
    text: Optional[str] = None     # nếu None → AI tự sinh


async def _tts_wav(text: str, voice_id: int, project_id: str, shot_id: str,
                   speed: float = 1.0) -> Optional[str]:
    """Normalize VN text → synthesize via OmniVoice (segmented + re-joined), save WAV."""
    chunks = await _tts_segments(vntext.normalize(text) or text, voice_id, speed)
    rel = f"{project_id}/narr_{shot_id}.wav"
    dest = media_store.MEDIA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(_concat_wav_bytes, chunks, dest)
    return f"/media/{rel}"


@router.post("/shots/{sid}/narration")
async def shot_narration(sid: str, body: NarrationRequest):
    shot = await _shot_or_404(sid)
    scene = await _scene_or_404(shot["scene_id"])
    project = await _project_or_404(scene["project_id"])
    text = body.text
    if not text:
        out = await brain.run_json(brain.narrator_prompt(
            shot.get("description") or shot.get("title") or "",
            body.language or project.get("script_lang") or "Vietnamese"))
        text = out.get("narrator_text", "")
    if not text:
        raise HTTPException(502, "Không sinh được narrator text")
    voice_id = project.get("voice_id") or 0
    web = await _tts_wav(text, voice_id, project["id"], sid,
                         float(project.get("tts_speed") or 1.0))
    dur = await assembler.probe_duration(assembler._local(web)) if web else 0.0
    await db.update("shot", sid, {
        "narrator_text": text, "narration_path": web,
        "narration_duration": dur, "updated_at": db.now()})
    return await _shot_or_404(sid)


@router.post("/projects/{pid}/assemble")
async def assemble_project(pid: str):
    await _project_or_404(pid)
    try:
        return await assembler.assemble(pid)
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@router.post("/projects/{pid}/assemble-images")
async def assemble_project_images(pid: str, ken_burns: bool = True,
                                  font: Optional[str] = None):
    """Ghép 1 video dài từ ẢNH các shot (theo scene), narration cả scene + caption từ khoá.
    `font` (hoặc setting `caption_font`) chọn font vẽ chữ; bỏ trống → tự dò theo OS."""
    await _project_or_404(pid)
    caption_font = font or (await db.kv_get_all()).get("caption_font") or None
    try:
        return await assembler.assemble_from_images(
            pid, ken_burns=ken_burns, caption_font=caption_font)
    except RuntimeError as e:
        raise HTTPException(400, str(e))


_BGM_EXT = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav",
            "audio/x-wav": ".wav", "audio/aac": ".aac", "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a", "audio/ogg": ".ogg", "audio/flac": ".flac"}


@router.post("/projects/{pid}/bgm")
async def upload_bgm(pid: str, file: UploadFile = File(...),
                     volume: Optional[float] = Form(None)):
    """Tải nhạc nền cho dự án. Khi ghép video, nhạc sẽ tự được trộn dưới giọng đọc với
    `volume` (mặc định 0.18). Bỏ trống nhạc → không chèn gì."""
    await _project_or_404(pid)
    ext = _BGM_EXT.get((file.content_type or "").lower())
    if not ext:
        ext = os.path.splitext(file.filename or "")[1].lower() or ".mp3"
    out_dir = assembler.STUDIO_MEDIA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    # one bgm per project — remove any previous file with a different extension
    for old in out_dir.glob("bgm.*"):
        old.unlink(missing_ok=True)
    dest = out_dir / f"bgm{ext}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    fields = {"bgm_path": str(dest), "updated_at": db.now()}
    if volume is not None:
        fields["bgm_volume"] = min(max(float(volume), 0.0), 1.0)
    await db.update("project", pid, fields)
    return await db.query_one("SELECT * FROM project WHERE id=?", (pid,))


class CopyBgmRequest(BaseModel):
    source: str                       # đường dẫn file nhạc của một dự án khác
    volume: Optional[float] = None


@router.post("/projects/{pid}/bgm/copy")
async def copy_bgm(pid: str, body: CopyBgmRequest):
    """Chép nhạc nền từ một dự án khác sang dự án này (dùng khi nạp preset thiết lập).

    COPY chứ không trỏ chung đường dẫn: mỗi dự án giữ file `bgm.<ext>` riêng, nếu dùng chung
    thì xoá/gỡ nhạc ở một dự án sẽ làm hỏng những dự án còn lại."""
    await _project_or_404(pid)
    src = Path(body.source)
    # Chỉ cho phép chép từ trong kho media của studio — preset là dữ liệu nhập từ ngoài,
    # không nên biến nó thành đường đọc file tuỳ ý trên máy.
    try:
        src.resolve().relative_to(assembler.STUDIO_MEDIA_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Nguồn nhạc nằm ngoài kho media của studio")
    if not src.is_file():
        raise HTTPException(404, "Không tìm thấy file nhạc nguồn")

    out_dir = assembler.STUDIO_MEDIA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"bgm{src.suffix.lower() or '.mp3'}"
    if src.resolve() != dest.resolve():
        for old in out_dir.glob("bgm.*"):    # một bgm mỗi dự án
            old.unlink(missing_ok=True)
        await asyncio.to_thread(shutil.copyfile, src, dest)
    fields = {"bgm_path": str(dest), "updated_at": db.now()}
    if body.volume is not None:
        fields["bgm_volume"] = min(max(float(body.volume), 0.0), 1.0)
    await db.update("project", pid, fields)
    return await db.query_one("SELECT * FROM project WHERE id=?", (pid,))


@router.delete("/projects/{pid}/bgm")
async def clear_bgm(pid: str):
    """Gỡ nhạc nền khỏi dự án (video ghép sau sẽ không còn nhạc)."""
    p = await _project_or_404(pid)
    old = (p.get("bgm_path") or "").strip()
    if old:
        try:
            os.remove(old)
        except OSError:
            pass
    await db.update("project", pid, {"bgm_path": None, "updated_at": db.now()})
    return await db.query_one("SELECT * FROM project WHERE id=?", (pid,))


_BGM_URL_EXT = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"}


async def _download_bgm_file(pid: str, url: str) -> Path:
    """Tải file nhạc từ 1 URL trực tiếp (Flow Music trả URL tĩnh public, không cần auth) →
    studio_media/{pid}/bgm.<ext>. Dọn file bgm cũ trước — 1 bgm/project, giống upload/copy."""
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in _BGM_URL_EXT:
        ext = ".m4a"
    out_dir = assembler.STUDIO_MEDIA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("bgm.*"):
        old.unlink(missing_ok=True)
    dest = out_dir / f"bgm{ext}"
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        resp = await c.get(url)
    if resp.status_code >= 400:
        raise HTTPException(502, f"Tải nhạc thất bại ({resp.status_code})")
    dest.write_bytes(resp.content)
    return dest


class GenerateBgmRequest(BaseModel):
    prompt: str                              # mô tả nhạc cụ/nhịp/tâm trạng, tiếng Anh khuyến nghị
    conversation_id: Optional[str] = None    # tiếp tục 1 conversation cũ (vd "làm chậm hơn")
    volume: Optional[float] = None
    timeout: Optional[float] = None


class SelectBgmRequest(BaseModel):
    audio_url: str
    volume: Optional[float] = None


@router.post("/projects/{pid}/bgm/generate")
async def generate_bgm(pid: str, body: GenerateBgmRequest):
    """Tạo nhạc nền bằng Google Flow Music (`/api/music/*`) từ mô tả tự nhiên — nhạc cụ,
    nhịp, tâm trạng... (bài mẫu thường dài ~2:30-2:55, đủ để loop-to-fit gần như liền mạch
    với hầu hết video, xem `assembler.apply_bgm`).

    Flow Music tự quyết định sinh 1 hay 2 bản (A/B) cho 1 lượt, không chọn được số lượng:
    - Ra đúng 1 bản → set làm bgm luôn, trả project đã cập nhật.
    - Ra 2 bản → KHÔNG tự chọn hộ (tránh chọn nhầm bản không ưng) — trả cả 2 kèm
      `audio_url` để nghe thử, gọi `POST .../bgm/select` với audio_url đã ưng để áp dụng.
    """
    await _project_or_404(pid)
    music_client = get_music_client()
    if not music_client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await music_client.create_song(
        body.prompt, conversation_id=body.conversation_id, timeout=body.timeout)
    songs = result.get("songs") or []
    if not songs:
        raise HTTPException(502, result.get("error") or "Flow Music không tạo được bài nào")

    if len(songs) > 1:
        return {
            "pending_selection": True,
            "conversation_id": result.get("conversation_id"),
            "songs": songs,
        }

    song = songs[0]
    dest = await _download_bgm_file(pid, song["audio_url"])
    fields = {"bgm_path": str(dest), "updated_at": db.now()}
    if body.volume is not None:
        fields["bgm_volume"] = min(max(float(body.volume), 0.0), 1.0)
    await db.update("project", pid, fields)
    project = await db.query_one("SELECT * FROM project WHERE id=?", (pid,))
    return {**project, "generated": song, "conversation_id": result.get("conversation_id")}


@router.post("/projects/{pid}/bgm/select")
async def select_bgm(pid: str, body: SelectBgmRequest):
    """Áp 1 bài đã biết audio_url làm nhạc nền dự án — dùng sau `bgm/generate` khi Flow
    Music ra 2 bản (A/B), hoặc để gắn bất kỳ bài nào khác trong thư viện flowmusic.app
    (`GET /api/music/conversations/{id}` → lấy audio_url từ 1 clip cũ)."""
    await _project_or_404(pid)
    dest = await _download_bgm_file(pid, body.audio_url)
    fields = {"bgm_path": str(dest), "updated_at": db.now()}
    if body.volume is not None:
        fields["bgm_volume"] = min(max(float(body.volume), 0.0), 1.0)
    await db.update("project", pid, fields)
    return await db.query_one("SELECT * FROM project WHERE id=?", (pid,))


# ─── Playlist nhạc (music video) ────────────────────────────
# Khác bgm ở trên (một bài chìm dưới lời đọc): playlist là NHIỀU bài phát nối tiếp, cách nhau
# `music_gap` giây, và tổng thời lượng của nó quyết định độ dài video. Xem agent/studio/music.py.


class MusicSettingsRequest(BaseModel):
    music_mode: Optional[bool] = None
    gap: Optional[float] = None


class AddTrackRequest(BaseModel):
    audio_url: str
    title: Optional[str] = None


class SaveMusicVideoRequest(BaseModel):
    video_url: str
    title: Optional[str] = None


class ConcatMusicVideoRequest(BaseModel):
    # Đường /media/... của các video ĐÃ lưu về dự án, theo đúng thứ tự muốn nối.
    webs: list[str]
    title: Optional[str] = None


class BuildMusicVideoItem(BaseModel):
    track_id: str       # bài trong playlist (nguồn TIẾNG + độ dài)
    video_web: str      # /media/... music video minh hoạ cho bài đó (nguồn HÌNH)


class BuildMusicVideoRequest(BaseModel):
    items: list[BuildMusicVideoItem]
    title: Optional[str] = None
    # Chỉ dùng cho bản export Resolve: độ dài cross dissolve (khung, 24fps → 24 = 1 giây).
    xfade_frames: int = davinci_xml.XFADE_F


class GenerateTrackRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None
    title: Optional[str] = None
    timeout: Optional[float] = None


class ReorderTracksRequest(BaseModel):
    ids: list[str]


class RenameTrackRequest(BaseModel):
    title: str


async def _track_or_404(tid: str) -> dict:
    row = await db.query_one("SELECT * FROM music_track WHERE id=?", (tid,))
    if not row:
        raise HTTPException(404, "Bài nhạc không tồn tại")
    await _assert_owner_of(row.get("project_id"))
    return row


async def _download_track(pid: str, url: str) -> Path:
    """Tải một bài từ URL (Flow Music trả URL tĩnh public) vào thư mục music của dự án.

    Mỗi bài một file riêng (tên theo id) — playlist giữ nhiều bài cùng lúc nên KHÔNG dọn
    file cũ như bgm."""
    out_dir = music_mod.track_dir(pid)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{db.new_id()}{music_mod.safe_ext(url)}"
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as c:
        resp = await c.get(url)
    if resp.status_code >= 400:
        raise HTTPException(502, f"Tải nhạc thất bại ({resp.status_code})")
    dest.write_bytes(resp.content)
    return dest


@router.get("/projects/{pid}/music")
async def music_status(pid: str):
    """Playlist + đối chiếu thời lượng nhạc với thời lượng hình (`shortfall` = còn thiếu)."""
    project = await _project_or_404(pid)
    return await music_mod.status(project)


@router.patch("/projects/{pid}/music/settings")
async def music_settings(pid: str, body: MusicSettingsRequest):
    await _project_or_404(pid)
    fields: dict = {}
    if body.music_mode is not None:
        fields["music_mode"] = 1 if body.music_mode else 0
    if body.gap is not None:
        fields["music_gap"] = max(0.0, float(body.gap))
    if fields:
        fields["updated_at"] = db.now()
        await db.update("project", pid, fields)
    return await music_mod.status(await _project_or_404(pid))


@router.post("/projects/{pid}/music/upload")
async def upload_track(pid: str, file: UploadFile = File(...), title: str = Form(None)):
    """Thêm một bài nhạc từ file trên máy vào playlist."""
    await _project_or_404(pid)
    ext = music_mod.safe_ext(file.filename or "", default="")
    if not ext:
        raise HTTPException(400, f"Định dạng nhạc không hỗ trợ: {file.filename}")
    out_dir = music_mod.track_dir(pid)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{db.new_id()}{ext}"
    dest.write_bytes(await file.read())
    await music_mod.add_track(
        pid, dest, title=title or Path(file.filename or dest.name).stem, source="upload")
    return await music_status(pid)


@router.post("/projects/{pid}/music-video/save")
async def save_music_video(pid: str, body: SaveMusicVideoRequest):
    """Tải music video của Flow Music về thư mục media của dự án.

    URL của họ là URL tĩnh public (bucket `producer-app-public`), không hết hạn như Flow
    video — nhưng nó nằm trên máy chủ người khác. Lưu về dự án để có bản của mình, dùng
    được khi ghép/xuất và không phụ thuộc bên kia còn giữ file hay không.
    """
    project = await _project_or_404(pid)
    url = body.video_url.strip()
    if not url.startswith("http"):
        raise HTTPException(400, "video_url không hợp lệ")
    out_dir = media_store.MEDIA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"mv_{_slug(body.title or 'music-video')[:40]}_{db.new_id()[:8]}.mp4"
    dest = out_dir / name
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as c:
        resp = await c.get(url)
    if resp.status_code >= 400:
        raise HTTPException(502, f"Tải video thất bại ({resp.status_code})")
    dest.write_bytes(resp.content)
    logger.info("music video lưu về dự án %s: %s (%.1f MB)",
                project["title"], name, len(resp.content) / 1e6)
    return {"web": f"/media/{pid}/{name}", "path": str(dest),
            "size_mb": round(len(resp.content) / 1e6, 1)}


@router.post("/projects/{pid}/music-video/concat")
async def concat_music_videos(pid: str, body: ConcatMusicVideoRequest):
    """Nối nhiều music video ĐÃ lưu về dự án thành MỘT video, theo thứ tự truyền vào.

    Mỗi music video của Flow Music đã mang sẵn tiếng của bài hát đó, nên nối thẳng là ra
    một video nhiều bài — không cần dựng lại dải âm thanh như đường playlist của tab Nhạc.
    Một job của Flow Music chỉ dựng được một đoạn ngắn (60s) của MỘT bài, nên đây là cách
    duy nhất để có video dài / nhiều bài từ đường này.
    """
    await _project_or_404(pid)
    if len(body.webs) < 2:
        raise HTTPException(400, "Cần ít nhất 2 video để nối")
    # Chỉ nhận file NẰM TRONG media của chính dự án — `webs` đến từ client.
    paths = [_media_path_in_project(pid, w) for w in body.webs]

    out_dir = media_store.MEDIA_DIR / pid
    out = out_dir / f"mv_{_slug(body.title or 'noi')[:40]}_{db.new_id()[:8]}.mp4"
    await assembler.concat_videos(paths, out)
    dur = await assembler.probe_duration(out)
    return {"web": f"/media/{pid}/{out.name}", "path": str(out),
            "duration": dur, "parts": len(paths),
            "size_mb": round(out.stat().st_size / 1e6, 1)}


def _media_path_in_project(pid: str, web: str) -> Path:
    """/media/... → đường thật, và CHẶN mọi đường trỏ ra ngoài thư mục media của dự án."""
    p = media_store.MEDIA_DIR / str(web or "").replace("/media/", "", 1)
    try:
        p = p.resolve()
        p.relative_to((media_store.MEDIA_DIR / pid).resolve())
    except (ValueError, OSError):
        raise HTTPException(400, f"Đường dẫn không thuộc dự án: {web}")
    if not p.exists():
        raise HTTPException(404, f"Không thấy file: {web}")
    return p


async def _music_video_pairs(pid: str, items: list[BuildMusicVideoItem]) -> list[tuple[dict, Path]]:
    """[(track_row, đường dẫn music video)] — dùng chung cho đường ghép sẵn và export Resolve."""
    pairs: list[tuple[dict, Path]] = []
    for it in items:
        track = await db.query_one("SELECT * FROM music_track WHERE id=? AND project_id=?",
                                   (it.track_id, pid))
        if not track:
            raise HTTPException(404, f"Không thấy bài {it.track_id} trong dự án")
        if not Path(track["path"]).exists():
            raise HTTPException(404, f"Thiếu file nhạc của bài '{track['title']}'")
        pairs.append((track, _media_path_in_project(pid, it.video_web)))
    return pairs


@router.post("/projects/{pid}/music-video/davinci-xml")
async def export_music_video_davinci(pid: str, body: BuildMusicVideoRequest):
    """Xuất timeline Resolve cho video nhạc — CÓ cross dissolve ở mọi mối nối.

    Khác `/music-video/build` (ffmpeg cắt phựt, xong là ra file MP4): bản này để người dùng
    dựng tiếp trong Resolve, nơi chỗ nối giữa hai vòng lặp hình và chỗ chuyển bài đều là
    một cross dissolve `xfade_frames` khung thay vì cắt cứng.
    """
    await _project_or_404(pid)
    if not body.items:
        raise HTTPException(400, "Chưa chọn bài nào")
    pairs = await _music_video_pairs(pid, body.items)
    try:
        return await davinci_xml.build_music_video(
            pid, pairs, xfade_f=max(0, min(120, int(body.xfade_frames))))
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@router.post("/projects/{pid}/music-video/build")
async def build_music_video(pid: str, body: BuildMusicVideoRequest):
    """Dựng video cho CẢ PLAYLIST: mỗi bài lấy music video của nó, LẶP cho hết bài.

    Đây là cách đúng để có video dài từ Flow Music: họ chỉ dựng ~60s hình cho một bài, mà
    bài thì vài phút — nên hình lặp lại còn TIẾNG là bản đầy đủ của bài (tiếng 60s trong
    file MV bị bỏ). Hết bài thì sang video của bài kế, nên chuyển bài là chuyển hẳn hình.

    Khoảng lặng giữa hai bài lấy theo `project.music_gap` như chế độ music video của tab
    Nhạc — hình vẫn chạy tiếp trong khoảng lặng đó, không đứng khung.
    """
    project = await _project_or_404(pid)
    if not body.items:
        raise HTTPException(400, "Chưa chọn bài nào")
    gap = float(project.get("music_gap") or 0)
    out_dir = media_store.MEDIA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)

    segs: list[Path] = []
    size: tuple[int, int] | None = None
    for i, it in enumerate(body.items):
        track = await db.query_one("SELECT * FROM music_track WHERE id=? AND project_id=?",
                                   (it.track_id, pid))
        if not track:
            raise HTTPException(404, f"Không thấy bài {it.track_id} trong dự án")
        audio = Path(track["path"])
        if not audio.exists():
            raise HTTPException(404, f"Thiếu file nhạc của bài '{track['title']}'")
        video = _media_path_in_project(pid, it.video_web)
        if size is None:
            size = await assembler.probe_size(video)
        seg = out_dir / f"mvseg_{db.new_id()[:8]}.mp4"
        # Bài cuối không nối thêm khoảng lặng — giống total_duration() của playlist.
        dur = await assembler.loop_video_over_audio(
            video, audio, seg, size=size,
            pad_s=gap if i < len(body.items) - 1 else 0.0)
        logger.info("music video: '%s' %.1fs (hình lặp từ %s)", track["title"], dur, video.name)
        segs.append(seg)

    out = out_dir / f"mv_{_slug(body.title or project['title'])[:40]}_{db.new_id()[:8]}.mp4"
    if len(segs) == 1:
        segs[0].replace(out)
    else:
        await assembler.concat_videos(segs, out)
        for s in segs:
            s.unlink(missing_ok=True)
    return {"web": f"/media/{pid}/{out.name}", "path": str(out),
            "duration": await assembler.probe_duration(out), "parts": len(body.items),
            "size_mb": round(out.stat().st_size / 1e6, 1)}


@router.post("/projects/{pid}/music/add")
async def add_track_from_url(pid: str, body: AddTrackRequest):
    """Thêm vào playlist một bài đã biết `audio_url` — bản A/B vừa sinh, hoặc bài cũ trong
    thư viện flowmusic.app (`GET /api/music/conversations/{id}`)."""
    await _project_or_404(pid)
    dest = await _download_track(pid, body.audio_url)
    await music_mod.add_track(pid, dest, title=body.title or dest.stem,
                              source="flowmusic", audio_url=body.audio_url)
    return await music_status(pid)


@router.post("/projects/{pid}/music/generate")
async def generate_track(pid: str, body: GenerateTrackRequest):
    """Sinh một bài bằng Flow Music rồi thêm thẳng vào playlist.

    Flow Music tự quyết định trả 1 hay 2 bản (A/B) và không chọn được số lượng. Ra 2 bản
    thì KHÔNG tự chọn hộ — trả cả hai kèm `audio_url` để nghe thử rồi gọi `.../music/add`."""
    await _project_or_404(pid)
    client = get_music_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.create_song(
        body.prompt, conversation_id=body.conversation_id, timeout=body.timeout)
    songs = result.get("songs") or []
    if not songs:
        raise HTTPException(502, result.get("error") or "Flow Music không tạo được bài nào")
    if len(songs) > 1:
        return {"pending_selection": True,
                "conversation_id": result.get("conversation_id"), "songs": songs}
    song = songs[0]
    dest = await _download_track(pid, song["audio_url"])
    await music_mod.add_track(pid, dest, title=body.title or song.get("title") or dest.stem,
                              source="flowmusic", audio_url=song["audio_url"], meta=song)
    return {**(await music_status(pid)), "generated": song,
            "conversation_id": result.get("conversation_id")}


@router.post("/projects/{pid}/music/reorder")
async def reorder_tracks(pid: str, body: ReorderTracksRequest):
    await _project_or_404(pid)
    await music_mod.reorder(pid, body.ids)
    return await music_status(pid)


@router.patch("/music-tracks/{tid}")
async def rename_track(tid: str, body: RenameTrackRequest):
    row = await _track_or_404(tid)
    await db.update("music_track", tid, {"title": body.title.strip() or row["title"]})
    return await music_status(row["project_id"])


@router.get("/music-tracks/{tid}/download")
async def download_track(tid: str):
    """Tải file nhạc của MỘT bài trong playlist về máy.

    File đã nằm dưới /studio-media nên `<audio>` phát được thẳng; endpoint này chỉ tồn tại vì
    TÊN FILE: trên đĩa mỗi bài là `<id ngẫu nhiên>.m4a`, tải thẳng đường dẫn ấy về thì được
    một thư mục toàn tên vô nghĩa. Ở đây tên file lấy theo tiêu đề bài."""
    row = await _track_or_404(tid)
    f = Path((row.get("path") or "").strip())
    if not f.name or not f.exists():
        raise HTTPException(404, "Không tìm thấy file nhạc")
    name = f"{_slug(row.get('title') or '') or 'track'}{f.suffix or '.m4a'}"
    return FileResponse(f, filename=name)


@router.get("/projects/{pid}/bgm/download")
async def download_bgm(pid: str):
    """Tải file nhạc nền của dự án (MỘT bài chìm dưới lời đọc — khác playlist music video).

    Cùng lý do đặt tên như `download_track`: trên đĩa nó luôn là `bgm.<ext>`, mọi dự án như
    nhau, nên tải về vài bài là không còn phân biệt được bài nào của dự án nào."""
    project = await _project_or_404(pid)
    f = Path((project.get("bgm_path") or "").strip())
    if not f.name or not f.exists():
        raise HTTPException(404, "Dự án chưa có nhạc nền")
    name = f"{_slug(project.get('title') or '') or 'bgm'}-bgm{f.suffix or '.m4a'}"
    return FileResponse(f, filename=name)


@router.delete("/music-tracks/{tid}")
async def delete_track(tid: str):
    row = await _track_or_404(tid)
    await music_mod.delete_track(row)
    return await music_status(row["project_id"])


@router.post("/projects/{pid}/export/davinci-xml")
async def export_davinci(pid: str):
    await _project_or_404(pid)
    try:
        return await davinci_xml.build(pid)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001 — surface a clear message instead of a bare 500
        logger.exception("export DaVinci XML lỗi cho %s", pid)
        raise HTTPException(500, f"Export DaVinci lỗi: {e}")


@router.post("/projects/{pid}/export")
async def export_project(pid: str):
    """Sinh metadata SEO (AI) + SRT từ narration + thumbnail (AI → Flow image)."""
    p = await _project_or_404(pid)
    meta = await brain.run_json(brain.seo_prompt(
        p["title"], p.get("script_raw") or "", p.get("script_lang") or "Vietnamese"))
    # SRT từ narration các shot (theo thứ tự)
    shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? ORDER BY sc.idx, sh.idx", (pid,))
    srt, t = [], 0.0
    for i, sh in enumerate(shots):
        if not sh.get("narrator_text"):
            continue
        dur = sh.get("narration_duration") or sh.get("duration") or 4
        srt.append(f"{i+1}\n{_ts(t)} --> {_ts(t+dur)}\n{sh['narrator_text']}\n")
        t += dur
    srt_text = "\n".join(srt)
    out_dir = assembler.STUDIO_MEDIA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "subtitles.srt").write_text(srt_text, encoding="utf-8")
    # thumbnail
    thumb_web = None
    try:
        client = get_flow_client()
        if client.connected and meta.get("thumbnail_prompt"):
            res = await client.generate_images(
                prompt=brain.compose_prompt(p, meta["thumbnail_prompt"]),
                project_id=p["flow_project_id"],
                aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
                user_paygate_tier=await _current_tier(),
                image_model=await _resolve_image_model(p))
            info = _extract_image_result(res.get("data", res))
            if info.get("media_id"):
                thumb_web = await media_store.ensure_local(info["media_id"], pid)
    except Exception as e:
        logger.warning("thumbnail gen failed: %s", e)
    await db.update("project", pid, {"updated_at": db.now()})
    return {"metadata": meta, "srt": srt_text, "thumbnail": thumb_web}


def _ts(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60)
    s = int(sec % 60); ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ─── Thumbnail / media resolve ──────────────────────────────

@router.get("/thumb/{media_key}")
async def thumb(media_key: str, pid: Optional[str] = None):
    """Trả thumbnail cho ảnh đại diện project/media.

    Ưu tiên file local đã tải (cache theo project) — chỉ gọi Flow khi máy chưa có ảnh.
    `pid` (project_id) giúp tìm đúng thư mục local trước."""
    path = await media_store.ensure_thumb(media_key, pid)
    if not path:
        raise HTTPException(404, "Không lấy được thumbnail (id sai hoặc chưa sẵn sàng)")
    media_type = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return FileResponse(path, media_type=media_type)


@router.post("/media/ensure/{media_id}")
async def ensure_media(media_id: str, project_id: str, ext: str = "png"):
    """Đảm bảo file local tồn tại; trả web path."""
    web = await media_store.ensure_local(media_id, project_id, ext)
    if not web:
        raise HTTPException(404, "Không tải được media")
    return {"path": web}


def _media_abs(path: Optional[str]):
    """Web media path (/media/...) → file trên đĩa, hoặc None nếu rỗng/ngoài kho."""
    if not path or "/media/" not in path:
        return None
    return media_store.MEDIA_DIR / path.replace("/media/", "", 1)


@router.post("/projects/{pid}/sync-media")
async def sync_project_media(pid: str):
    """Đồng bộ ảnh/video với Flow (Flow là nguồn chuẩn).

    Media nào đã bị xoá trên Flow thì chắc chắn không còn → gỡ tham chiếu ở mục tương
    ứng (entity / shot ảnh / shot video / các view phụ / lịch sử media) và xoá file cache
    local. Một media coi là CÒN nếu media_id HOẶC primary_media_id của nó còn trên Flow
    (đối chiếu rộng để tránh xoá nhầm)."""
    project = await _project_or_404(pid)
    flow_id = project.get("flow_project_id")
    if not flow_id:
        raise HTTPException(400, "Project chưa gắn với project trên Flow")

    client = _require_extension()
    raw = await client.get_project(flow_id)
    existing = _flow_existing_media_ids(raw)
    if not existing:
        # Không đọc được media nào → có thể lỗi tạm thời. Không xoá gì (tránh phá dữ liệu).
        raise HTTPException(502, "Không đọc được media từ Flow — thử lại, chưa xoá gì.")

    def present(*ids) -> bool:
        return any(i in existing for i in ids if i)

    def rm_file(path: Optional[str]) -> None:
        f = _media_abs(path)
        if f and f.is_file():
            try:
                f.unlink()
            except OSError:
                pass

    removed: dict = {"entities": [], "shot_images": [], "shot_videos": [],
                     "extra_views": 0, "history": 0}

    # Entities (ảnh chính + các view phụ trong extra_media)
    for e in await db.query_all("SELECT * FROM entity WHERE project_id=?", (pid,)):
        upd: dict = {}
        if (e.get("media_id") or e.get("primary_media_id")) and \
                not present(e.get("media_id"), e.get("primary_media_id")):
            rm_file(e.get("image_path"))
            upd.update(media_id=None, primary_media_id=None, image_path=None, image_url=None)
            removed["entities"].append(e.get("name") or e["id"])
        if e.get("extra_media"):
            try:
                views = json.loads(e["extra_media"]) or []
            except (json.JSONDecodeError, TypeError):
                views = []
            kept = [v for v in views if present(v.get("media_id"), v.get("primary_media_id"))]
            for v in views:
                if v not in kept:
                    rm_file(v.get("path"))
                    removed["extra_views"] += 1
            if len(kept) != len(views):
                upd["extra_media"] = json.dumps(kept) if kept else None
        if upd:
            upd["updated_at"] = db.now()
            await db.update("entity", e["id"], upd)

    # Shots (ảnh + video) trong mọi scene của project
    scenes = await db.query_all("SELECT id FROM scene WHERE project_id=?", (pid,))
    for sc in scenes:
        for sh in await db.query_all("SELECT * FROM shot WHERE scene_id=?", (sc["id"],)):
            upd = {}
            if (sh.get("image_media_id") or sh.get("image_primary_id")) and \
                    not present(sh.get("image_media_id"), sh.get("image_primary_id")):
                rm_file(sh.get("image_path"))
                rm_file(sh.get("image_hires_path"))   # bản 2K/4K thuộc về ảnh vừa mất
                upd.update(image_media_id=None, image_primary_id=None,
                           image_workflow_id=None, image_path=None,
                           image_hires_path=None, image_hires_media_id=None,
                           image_hires_res=None)
                removed["shot_images"].append(sh.get("title") or sh["id"])
            if (sh.get("video_media_id") or sh.get("video_primary_id")) and \
                    not present(sh.get("video_media_id"), sh.get("video_primary_id")):
                rm_file(sh.get("video_path"))
                rm_file(sh.get("upscale_path"))   # bản upscale thuộc về video vừa mất
                upd.update(video_media_id=None, video_primary_id=None,
                           video_workflow_id=None, video_path=None,
                           upscale_path=None, upscale_url=None,
                           upscale_media_id=None, upscale_res=None)
                removed["shot_videos"].append(sh.get("title") or sh["id"])
            if upd:
                upd["updated_at"] = db.now()
                await db.update("shot", sh["id"], upd)

    # Lịch sử media — bỏ các bản đã biến mất khỏi Flow
    for h in await db.query_all("SELECT * FROM media_history WHERE project_id=?", (pid,)):
        if not present(h.get("media_id"), h.get("primary_media_id")):
            rm_file(h.get("path"))
            await db.delete("media_history", h["id"])
            removed["history"] += 1

    total = (len(removed["entities"]) + len(removed["shot_images"]) +
             len(removed["shot_videos"]) + removed["extra_views"] + removed["history"])
    return {"flow_media": len(existing), "removed": removed, "total_removed": total}


# ─── Jobs: realtime batch progress (§9) ─────────────────────

@router.get("/jobs")
async def list_jobs(project_id: Optional[str] = None):
    """Các job đang/ vừa chạy (trong bộ nhớ). Dùng để dựng lại trạng thái khi mở tab."""
    return {"jobs": get_job_manager().active(project_id)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Dừng một batch đang chạy (sau item hiện tại)."""
    ok = get_job_manager().cancel(job_id)
    if not ok:
        raise HTTPException(404, "Job không tồn tại hoặc đã kết thúc")
    return {"ok": True}


@router.websocket("/ws")
async def jobs_ws(ws: WebSocket):
    """Kênh realtime: server đẩy {type:'job', job:{…}} mỗi khi job thay đổi.

    Khi vừa kết nối, gửi snapshot toàn bộ job hiện có để client dựng lại banner.
    """
    await ws.accept()
    mgr = get_job_manager()
    mgr.subscribe(ws)
    try:
        await ws.send_json({"type": "snapshot", "jobs": mgr.active()})
        while True:
            # Không cần dữ liệu từ client; giữ kết nối mở (và phát hiện ngắt).
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        mgr.unsubscribe(ws)
