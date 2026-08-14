"""Configuration constants."""
import json
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────
BASE_DIR = Path(os.environ.get("FLOW_AGENT_DIR", Path(__file__).parent.parent))

# ─── API Server ──────────────────────────────────────────────
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8100"))

# ─── WebSocket Server (extension connects here) ─────────────
WS_HOST = os.environ.get("WS_HOST", "127.0.0.1")
WS_PORT = int(os.environ.get("WS_PORT", "9222"))

# ─── Google Flow API ────────────────────────────────────────
GOOGLE_FLOW_API = "https://aisandbox-pa.googleapis.com"
# Optional — auth tới aisandbox-pa do extension lo bằng Bearer token (ya29.*).
# Để rỗng thì _build_url bỏ hẳn ?key= (đã verify project + ảnh vẫn chạy bình thường).
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV")

# polling timeout for video/upscale status (used by flow_client)
VIDEO_POLL_TIMEOUT = int(os.environ.get("VIDEO_POLL_TIMEOUT", "420"))

# ─── Google Flow Music (flowmusic.app) ──────────────────────
# Kiến trúc khác hẳn Flow video: không có REST tạo nhạc với tham số cấu trúc — server chạy
# 1 AI agent, client chỉ gửi 1 tin nhắn chat tự nhiên vào /__api/conversation, agent tự gọi
# tool audio__create_song/... rồi trả kết quả qua SSE (/__api/messages/{job_id}/stream).
# Bearer là Supabase JWT (không phải ya29 của Google) — bắt qua webRequest trong extension,
# không có reCAPTCHA nào chặn các endpoint đã khảo sát. audio_url/wav_url của clip là URL
# tĩnh public (bucket producer-app-public), không hết hạn — khỏi cần refresh như Flow video.
FLOWMUSIC_WEB_API = "https://www.flowmusic.app"
FLOWMUSIC_SUPABASE_API = "https://sb.flowmusic.app"
# Thời gian chờ tối đa 1 lượt tạo nhạc (submit + đọc hết SSE tới event "final"). Bài mẫu
# khảo sát mất ~30-70s cho 1-2 bản nháp; để dư cho mạng chậm/nhiều bản.
MUSIC_GENERATION_TIMEOUT = float(os.environ.get("MUSIC_GENERATION_TIMEOUT", "180"))
# Poll trạng thái operation qua /__api/audio-create-song-status/{operation_id} (dự phòng khi
# SSE không kịp trả clip_id trong lúc còn generate — theo estimated_time thường ~35s).
MUSIC_STATUS_POLL_INTERVAL = float(os.environ.get("MUSIC_STATUS_POLL_INTERVAL", "3"))
MUSIC_STATUS_POLL_TIMEOUT = float(os.environ.get("MUSIC_STATUS_POLL_TIMEOUT", "120"))

MUSIC_ENDPOINTS = {
    "conversation_send": "/__api/conversation",              # POST — gửi tin nhắn chat
    "conversations_list": "/__api/conversations",             # GET  — danh sách conversation
    "conversation_get": "/__api/conversations/{conversation_id}",   # GET
    "conversation_rename": "/__api/conversations/{conversation_id}",  # PATCH {"title"}
    "conversation_delete": "/__api/conversations/{conversation_id}",  # DELETE
    "message_stream": "/__api/messages/{job_id}/stream",      # GET (SSE) ?last_id=0
    "song_status": "/__api/audio-create-song-status/{operation_id}",  # GET — poll
    "clips_batch": "/__api/clips",                            # POST {"clip_ids": [...]}
    "billing_credits": "/__api/billing/credits",               # GET
    "billing_subscription": "/__api/billing/subscription",     # GET
    "projects_list": "/__api/projects",                        # GET
}

# ─── OmniVoice TTS (hosted on Google Colab) ─────────────────
# Base URL của server OmniVoice trên Colab (ngrok/localtunnel). URL này đổi mỗi
# phiên Colab → có thể đặt qua env hoặc runtime (PUT /api/tts/config).
OMNIVOICE_BASE_URL = os.environ.get("OMNIVOICE_BASE_URL", "http://localhost:8000")
# Timeout (giây) cho call tổng hợp giọng — model inference có thể chậm.
OMNIVOICE_TTS_TIMEOUT = float(os.environ.get("OMNIVOICE_TTS_TIMEOUT", "300"))

# ─── AI Agent CLIs (headless subprocess runners) ────────────
# Chạy các agent CLI (Claude Code, Antigravity, ...) như subprocess headless.
# Timeout (giây) cho mỗi lần chạy — agent có thể chạy lâu.
AGENT_CLI_TIMEOUT = float(os.environ.get("AGENT_CLI_TIMEOUT", "600"))
# Mặc định bypass permission để chạy không cần người xác nhận (automation).
AGENT_SKIP_PERMISSIONS = os.environ.get("AGENT_SKIP_PERMISSIONS", "1") == "1"
# Kích thước PTY giả cho agent dạng TUI (vd Antigravity).
AGENT_PTY_COLS = int(os.environ.get("AGENT_PTY_COLS", "120"))
AGENT_PTY_ROWS = int(os.environ.get("AGENT_PTY_ROWS", "40"))

# Prompt mode "arg" nhét prompt vào dòng lệnh; Windows giới hạn độ dài command-line
# (~32k, ConPTY/winpty còn thấp hơn) → prompt dài báo "The filename or extension is too
# long". Khi prompt vượt ngưỡng này, ghi ra temp file + truyền chỉ dẫn ngắn để agent đọc.
AGENT_PROMPT_ARG_MAX = int(os.environ.get("AGENT_PROMPT_ARG_MAX", "6000"))

# Registry các agent hỗ trợ. Mỗi field đều override được qua env để linh hoạt
# khi binary/cờ của CLI thay đổi.
#   bin           — tên/đường dẫn binary (PATH-resolved)
#   prompt_mode   — "stdin" (an toàn, tránh escaping) | "arg" (nối prompt cuối)
#   base_args     — args luôn kèm theo (chế độ headless/print)
#   model_flag    — cờ chọn model (None nếu CLI không hỗ trợ)
#   skip_perm     — args thêm khi bypass permission
def _env_args(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    return json.loads(raw) if raw else default


AI_AGENTS = {
    "claude": {
        "bin": os.environ.get("AGENT_CLAUDE_BIN", "claude"),
        "prompt_mode": "stdin",
        "base_args": _env_args("AGENT_CLAUDE_ARGS", ["-p", "--output-format", "text"]),
        "model_flag": os.environ.get("AGENT_CLAUDE_MODEL_FLAG", "--model"),
        "skip_perm": _env_args("AGENT_CLAUDE_SKIP_ARGS", ["--dangerously-skip-permissions"]),
        # claude -p ghi thẳng stdout — không cần PTY.
        "pty": os.environ.get("AGENT_CLAUDE_PTY", "0") == "1",
    },
    "antigravity": {
        # Antigravity CLI = binary `agy`. Cú pháp giống Claude Code:
        # `agy -p "<prompt>" [--model X] [--dangerously-skip-permissions]`.
        # `-p` nhận prompt làm giá trị đi kèm → prompt_mode "arg" (nối ngay sau).
        "bin": os.environ.get("AGENT_ANTIGRAVITY_BIN", "agy"),
        "prompt_mode": os.environ.get("AGENT_ANTIGRAVITY_PROMPT_MODE", "arg"),
        "base_args": _env_args("AGENT_ANTIGRAVITY_ARGS", ["-p"]),
        "model_flag": os.environ.get("AGENT_ANTIGRAVITY_MODEL_FLAG", "--model") or None,
        "skip_perm": _env_args("AGENT_ANTIGRAVITY_SKIP_ARGS", ["--dangerously-skip-permissions"]),
        # agy là TUI — print mode chỉ render ra terminal, phải chạy dưới PTY.
        "pty": os.environ.get("AGENT_ANTIGRAVITY_PTY", "1") == "1",
    },
}

# ─── Model Keys (loaded from models.json for easy updates) ──
_MODELS_FILE = Path(__file__).parent / "models.json"
# encoding BẮT BUỘC: `open()` không tham số dùng codec mặc định của hệ (cp1252 trên Windows
# tiếng Việt), nên chỉ cần một chữ có dấu trong models.json là agent chết ngay lúc import.
with open(_MODELS_FILE, encoding="utf-8") as _f:
    _MODELS = json.load(_f)

VIDEO_MODELS = _MODELS["video_models"]
UPSCALE_MODELS = _MODELS["upscale_models"]
IMAGE_MODELS = _MODELS["image_models"]

# ─── Veo 3.1 Lite [Lower Priority] — 0 credit, chỉ Ultra ────
# Họ model "lite low priority": render xếp hàng sau (chậm hơn) nhưng KHÔNG trừ credit. Cùng
# ba kiểu sinh như Veo thường, mỗi kiểu một endpoint khác nhau:
#   frame_2_video           — startImage (i2v)            → batchAsyncGenerateVideoStartImage
#   start_end_frame_2_video — startImage + endImage (nội suy) → ...StartAndEndImage
#   reference_frame_2_video — referenceImages (r2v/"inference") → ...ReferenceImages
# i2v lite vốn đã là mặc định của PAYGATE_TIER_TWO trong `video_models`; hai key còn lại chỉ
# mở khi tài khoản là Gemini Ultra, nên chúng nằm riêng ở đây thay vì trộn vào bảng theo tier.
VEO_LITE_MODELS = _MODELS.get("veo_lite_models", {})
# Độ dài clip: CHỈ kiểu nội suy (khung đầu + khung cuối) mới cho chọn — "inference" r2v và
# i2v thì Flow cứng 8s. Và giống Omni Flash, độ dài NẰM TRONG model key chứ không phải một
# field riêng: `veo_3_1_i2v_s_lite_{4,6}s_fl_low_priority` (bản 8s mặc định lại mang tên
# `veo_3_1_interpolation_lite_low_priority` — đừng suy ra theo công thức, Flow đặt tên
# không đều). Đã bắt tận tay request 6s; 4s theo đúng khuôn 6s.
VEO_LITE_FRAME_MODELS = _MODELS.get("veo_lite_frame_models", {})
VEO_LITE_FRAME_DURATIONS = list(VEO_LITE_FRAME_MODELS.keys())
VEO_LITE_DEFAULT_S = 8
# Tier được phép dùng Lite r2v/nội suy. Flow trả tier qua /v1/credits (`userPaygateTier`);
# Gemini Ultra = PAYGATE_TIER_TWO.
VEO_LITE_TIERS = {"PAYGATE_TIER_TWO"}

# ─── Image upsample (Flow /v1/flow/upsampleImage) ───────────
# Ảnh sinh ra chỉ là bản HD (phân giải thấp). Flow cho tải bản phóng to theo tier:
# TIER_ONE → 2K, TIER_TWO → 4K. Response trả base64 trong `encodedImage`.
UPSAMPLE_IMAGE_RESOLUTIONS = {
    "PAYGATE_TIER_ONE": "UPSAMPLE_IMAGE_RESOLUTION_2K",
    "PAYGATE_TIER_TWO": "UPSAMPLE_IMAGE_RESOLUTION_4K",
}
UPSAMPLE_IMAGE_DEFAULT = "UPSAMPLE_IMAGE_RESOLUTION_2K"
# Upsample trả cả ảnh 4K dưới dạng base64 → chậm hơn hẳn một call thường.
UPSAMPLE_IMAGE_TIMEOUT = float(os.environ.get("UPSAMPLE_IMAGE_TIMEOUT", "180"))

# ─── Video upsample (batchAsyncGenerateVideoUpsampleVideo) ──
# Video sinh ra cũng chỉ là bản HD. Trần upscale cũng theo tier: TIER_ONE chỉ lên được
# Full HD (1080p), TIER_TWO mới lên 4K. Khác upsample ảnh (đồng bộ, trả base64), việc này
# chạy BẤT ĐỒNG BỘ như một lượt sinh video: submit → poll, ~1 phút/video.
# Đo thực tế trên tier ONE → 1080p: KHÔNG trừ credit (914 → 914 cho một video render mới).
# Bản 4K (tier TWO) thì CÓ: ≈50 credit/video — đắt gấp 2.5 lần một lượt render clip mới, nên
# batch upscale 4K phải hỏi trước (webapp/src/lib/credits.ts). Upscale ẢNH lên 4K vẫn 0 credit.
# Mức 2K nằm giữa; CHƯA ĐO giá của nó — coi như chưa biết chứ đừng suy ra là 0.
UPSAMPLE_VIDEO_RESOLUTIONS = {
    "PAYGATE_TIER_ONE": "VIDEO_RESOLUTION_1080P",
    "PAYGATE_TIER_TWO": "VIDEO_RESOLUTION_4K",
}
UPSAMPLE_VIDEO_DEFAULT = "VIDEO_RESOLUTION_1080P"
# Thứ tự TĂNG DẦN của các mức upscale video — một chỗ duy nhất, để việc "hạ lựa chọn của dự án
# xuống đúng trần tier" không phải đoán thứ tự từ tên. Thêm mức mới thì sửa models.json, đừng
# rải hằng số vào hires.py.
UPSAMPLE_VIDEO_ORDER = _MODELS.get("upscale_video_order") or [
    "VIDEO_RESOLUTION_1080P", "VIDEO_RESOLUTION_4K"]
# Omni Flash — r2v đa-độ-dài (4/6/8/10s), key theo số giây (string). Aspect chỉ
# PORTRAIT/LANDSCAPE (không SQUARE). Dùng chung endpoint r2v.
OMNI_FLASH_MODELS = _MODELS.get("omni_flash_models", {})
OMNI_FLASH_VALID_ASPECTS = {"VIDEO_ASPECT_RATIO_PORTRAIT", "VIDEO_ASPECT_RATIO_LANDSCAPE"}

# ─── API Endpoints ───────────────────────────────────────────
ENDPOINTS = {
    "generate_images": "/v1/projects/{project_id}/flowMedia:batchGenerateImages",
    "generate_video": "/v1/video:batchAsyncGenerateVideoStartImage",
    "generate_video_start_end": "/v1/video:batchAsyncGenerateVideoStartAndEndImage",
    "generate_video_references": "/v1/video:batchAsyncGenerateVideoReferenceImages",
    "upscale_video": "/v1/video:batchAsyncGenerateVideoUpsampleVideo",
    "upscale_image": "/v1/flow/upsampleImage",
    "upload_image": "/v1/flow/uploadImage",
    "check_video_status": "/v1/video:batchCheckAsyncVideoGenerationStatus",
    "get_credits": "/v1/credits",
    "get_media": "/v1/media/{media_id}",
    "changeDisplayname_media": "/v1/flowWorkflows/{media_id}",
    "changeProject_cover_image": "/v1/projects/{project_id}?clientContext.tool=PINHOLE&updateMask=thumbnailMediaKey",
}

# ─── Header Randomization Pools ─────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
]

CHROME_VERSIONS = [
    '"Google Chrome";v="109", "Chromium";v="109"',
    '"Google Chrome";v="110", "Chromium";v="110"',
    '"Google Chrome";v="111", "Chromium";v="111"',
    '"Google Chrome";v="113", "Not-A.Brand";v="24"',
    '"Google Chrome";v="120", "Not-A.Brand";v="24"',
    '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
]

BROWSER_VALIDATIONS = [
    "SgDQo8mvrGRdD61Pwo8wyWVgYgs=",
]

CLIENT_DATA = [
    "CKi1yQEIh7bJAQiktskBCKmdygEIvorLAQiUocsBCIagzQEYv6nKARjRp88BGKqwzwE=",
]
