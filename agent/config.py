"""Configuration constants."""
import json
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────
BASE_DIR = Path(os.environ.get("FLOW_AGENT_DIR", Path(__file__).parent.parent))
DB_PATH = BASE_DIR / "flow_agent.db"

# ─── API Server ──────────────────────────────────────────────
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8100"))

# ─── WebSocket Server (extension connects here) ─────────────
WS_HOST = os.environ.get("WS_HOST", "127.0.0.1")
WS_PORT = int(os.environ.get("WS_PORT", "9222"))

# ─── Google Flow API ────────────────────────────────────────
GOOGLE_FLOW_API = "https://aisandbox-pa.googleapis.com"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY")
RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV")

# ─── Worker ──────────────────────────────────────────────────
# Stability profile (desktop default):
# - Keep moderate overall concurrency
# - Throttle image requests to reduce reCAPTCHA traffic flags
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "1"))
VIDEO_POLL_INTERVAL = int(os.environ.get("VIDEO_POLL_INTERVAL", "15"))  # polling interval for video/upscale status
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "5"))
VIDEO_POLL_TIMEOUT = int(os.environ.get("VIDEO_POLL_TIMEOUT", "420"))
API_COOLDOWN = float(os.environ.get("API_COOLDOWN", "1"))  # seconds between API calls
MAX_CONCURRENT_REQUESTS = int(os.environ.get("MAX_CONCURRENT_REQUESTS", "4"))
# All Flow generation requests consume reCAPTCHA budget.
# Keep this conservative to avoid unusual-traffic lockouts.
MAX_CONCURRENT_CAPTCHA_REQUESTS = int(os.environ.get("MAX_CONCURRENT_CAPTCHA_REQUESTS", "1"))
CAPTCHA_API_COOLDOWN = float(os.environ.get("CAPTCHA_API_COOLDOWN", "10"))  # minimum gap between captcha-consuming API calls
MAX_CONCURRENT_IMAGE_REQUESTS = int(os.environ.get("MAX_CONCURRENT_IMAGE_REQUESTS", "1"))
IMAGE_API_COOLDOWN = float(os.environ.get("IMAGE_API_COOLDOWN", "12"))  # minimum gap between image/edit requests
# Video queue can run in parallel without overloading captcha as heavily as image generation.
MAX_CONCURRENT_VIDEO_REQUESTS = int(os.environ.get("MAX_CONCURRENT_VIDEO_REQUESTS", "4"))
VIDEO_API_COOLDOWN = float(os.environ.get("VIDEO_API_COOLDOWN", "1"))  # min gap for video submit/status jobs
# Local 4K upscale is CPU/GPU intensive; keep strict concurrency by default.
MAX_CONCURRENT_LOCAL_UPSCALE_REQUESTS = int(os.environ.get("MAX_CONCURRENT_LOCAL_UPSCALE_REQUESTS", "1"))
# Ref stage (character + location) can run slightly faster than scene image stage.
MAX_CONCURRENT_CHARACTER_REF_REQUESTS = int(os.environ.get("MAX_CONCURRENT_CHARACTER_REF_REQUESTS", "2"))
CHARACTER_IMAGE_API_COOLDOWN = float(os.environ.get("CHARACTER_IMAGE_API_COOLDOWN", "5"))  # min gap for character/location ref ops
CAPTCHA_RETRY_LIMIT = int(os.environ.get("CAPTCHA_RETRY_LIMIT", "10"))
CAPTCHA_RETRY_BACKOFF_BASE = int(os.environ.get("CAPTCHA_RETRY_BACKOFF_BASE", "45"))  # seconds
CAPTCHA_RETRY_BACKOFF_MAX = int(os.environ.get("CAPTCHA_RETRY_BACKOFF_MAX", "1800"))  # seconds
CAPTCHA_GROUP_PAUSE_SEC = int(os.environ.get("CAPTCHA_GROUP_PAUSE_SEC", "180"))  # pause all image jobs
CAPTCHA_TRAFFIC_PAUSE_SEC = int(os.environ.get("CAPTCHA_TRAFFIC_PAUSE_SEC", "900"))  # strict pause for TOO_MUCH_TRAFFIC
CAPTCHA_SAFE_MODE_SEC = int(os.environ.get("CAPTCHA_SAFE_MODE_SEC", "1800"))  # temporary image safe-mode window
CAPTCHA_SAFE_MODE_IMAGE_CONCURRENCY = int(os.environ.get("CAPTCHA_SAFE_MODE_IMAGE_CONCURRENCY", "1"))
CAPTCHA_SAFE_MODE_IMAGE_COOLDOWN = float(os.environ.get("CAPTCHA_SAFE_MODE_IMAGE_COOLDOWN", "20"))
CAPTCHA_CONTENT_TIMEOUT_PAUSE_SEC = int(os.environ.get("CAPTCHA_CONTENT_TIMEOUT_PAUSE_SEC", "90"))
OPERATION_FAILED_RETRY_BASE_SEC = int(os.environ.get("OPERATION_FAILED_RETRY_BASE_SEC", "45"))
REQUEST_DISPATCH_TIMEOUT = int(os.environ.get("REQUEST_DISPATCH_TIMEOUT", "120"))  # per-request dispatch timeout
STALE_PROCESSING_TIMEOUT = int(os.environ.get("STALE_PROCESSING_TIMEOUT", "600"))  # 10 min
STALE_PENDING_LOCAL_UPSCALE_TIMEOUT = int(
    os.environ.get("STALE_PENDING_LOCAL_UPSCALE_TIMEOUT", "5400")
)  # 90 min
FLOW_CREDITS_CACHE_TTL_SEC = int(os.environ.get("FLOW_CREDITS_CACHE_TTL_SEC", "1800"))
FLOW_CREDITS_ERROR_TTL_SEC = int(os.environ.get("FLOW_CREDITS_ERROR_TTL_SEC", "30"))
TIER_SYNC_MIN_INTERVAL_SEC = int(os.environ.get("TIER_SYNC_MIN_INTERVAL_SEC", "1800"))

# ─── Model Keys (loaded from models.json for easy updates) ──
_MODELS_FILE = Path(__file__).parent / "models.json"
with open(_MODELS_FILE) as _f:
    _MODELS = json.load(_f)

VIDEO_MODELS = _MODELS["video_models"]
UPSCALE_MODELS = _MODELS["upscale_models"]
IMAGE_MODELS = _MODELS["image_models"]

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
}

# ─── Output Directories ─────────────────────────────────────
OUTPUT_DIR = BASE_DIR / "output"
SHARED_OUTPUT_DIR = OUTPUT_DIR / "_shared"
TTS_TEMPLATES_DIR = SHARED_OUTPUT_DIR / "tts_templates"
MUSIC_OUTPUT_DIR = SHARED_OUTPUT_DIR / "music"
TTS_SETTINGS_PATH = BASE_DIR / "tts_settings.json"

# ─── TTS (OmniVoice) ─────────────────────────────────────────
TTS_MODEL = os.environ.get("TTS_MODEL", "k2-fsa/OmniVoice")
TTS_DEVICE = os.environ.get("TTS_DEVICE", "cpu")  # MPS produces gibberish; CPU+fp32 works
TTS_SAMPLE_RATE = int(os.environ.get("TTS_SAMPLE_RATE", "24000"))
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "elevenlabs").strip().lower()  # elevenlabs | omnivoice

# ─── TTS (ElevenLabs) ────────────────────────────────────────
ELEVENLABS_API_BASE = os.environ.get("ELEVENLABS_API_BASE", "https://api.elevenlabs.io").rstrip("/")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()
ELEVENLABS_DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_DEFAULT_VOICE_ID", "").strip()
ELEVENLABS_TIMEOUT_SEC = float(os.environ.get("ELEVENLABS_TIMEOUT_SEC", "60"))
ELEVENLABS_MAX_RETRIES = int(os.environ.get("ELEVENLABS_MAX_RETRIES", "2"))

# ─── Review / Claude Vision ──────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
REVIEW_MODEL = os.environ.get("REVIEW_MODEL", "claude-haiku-4-5-20251001")
REVIEW_FPS_LIGHT = float(os.environ.get("REVIEW_FPS_LIGHT", "4"))
REVIEW_FPS_DEEP = float(os.environ.get("REVIEW_FPS_DEEP", "8"))
REVIEW_MAX_FRAMES = int(os.environ.get("REVIEW_MAX_FRAMES", "64"))

# ─── Suno (Music Generation) — sunoapi.org ──────────────────
def _load_suno_key() -> str:
    """Load Suno API key: env var first, then channel_rules.json fallback."""
    key = os.environ.get("SUNO_API_KEY", "")
    if key:
        return key
    channels_dir = BASE_DIR / "youtube" / "channels"
    if channels_dir.exists():
        for rules_file in channels_dir.glob("*/channel_rules.json"):
            try:
                rules = json.loads(rules_file.read_text())
                key = rules.get("api_keys", {}).get("suno", "")
                if key:
                    return key
            except (json.JSONDecodeError, OSError):
                continue
    return ""

SUNO_API_KEY = _load_suno_key()
SUNO_BASE_URL = os.environ.get("SUNO_BASE_URL", "https://api.sunoapi.org")
SUNO_MODEL = os.environ.get("SUNO_MODEL", "V4")
SUNO_CALLBACK_URL = os.environ.get("SUNO_CALLBACK_URL", f"http://{API_HOST}:{API_PORT}/api/music/callback")
SUNO_POLL_INTERVAL = int(os.environ.get("SUNO_POLL_INTERVAL", "5"))
SUNO_POLL_TIMEOUT = int(os.environ.get("SUNO_POLL_TIMEOUT", "600"))

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
