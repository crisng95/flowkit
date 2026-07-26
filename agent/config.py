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
with open(_MODELS_FILE) as _f:
    _MODELS = json.load(_f)

VIDEO_MODELS = _MODELS["video_models"]
UPSCALE_MODELS = _MODELS["upscale_models"]
IMAGE_MODELS = _MODELS["image_models"]

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
# Bản 4K (tier TWO) chưa kiểm chứng được — nhiều khả năng mới là bản tính tiền.
UPSAMPLE_VIDEO_RESOLUTIONS = {
    "PAYGATE_TIER_ONE": "VIDEO_RESOLUTION_1080P",
    "PAYGATE_TIER_TWO": "VIDEO_RESOLUTION_4K",
}
UPSAMPLE_VIDEO_DEFAULT = "VIDEO_RESOLUTION_1080P"
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
