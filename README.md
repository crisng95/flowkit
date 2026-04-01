# Google Flow Agent

Standalone system to generate AI videos via Google Flow API. Uses a Chrome extension as browser bridge for authentication, reCAPTCHA solving, and API proxying.

```
┌──────────────────┐     WebSocket      ┌──────────────────────┐
│  Python Agent    │◄──────────────────►│  Chrome Extension     │
│  (FastAPI+SQLite)│     localhost:9222  │  (MV3 Service Worker) │
│                  │                    │                       │
│  - REST API :8100│  ── commands ──►   │  - Token capture      │
│  - Queue worker  │  ◄── results ──    │  - reCAPTCHA solve    │
│  - Post-process  │                    │  - API proxy          │
│  - SQLite DB     │                    │  (on labs.google)     │
└──────────────────┘                    └──────────────────────┘
```

## Why?

Google Flow (labs.google) has no official API. This project reverse-engineers the internal endpoints and uses a Chrome extension running on a real browser session to:

1. **Capture** the bearer token (`ya29.*`) from network requests
2. **Solve** reCAPTCHA Enterprise tokens via `grecaptcha.enterprise.execute()`
3. **Proxy** API calls through the browser (residential IP, cookies, session)

The Python agent manages projects, scenes, and a request queue — the extension just executes what the agent tells it to.

## Quick Start

### 1. Install the Chrome Extension

```bash
# In Chrome:
# 1. Go to chrome://extensions
# 2. Enable "Developer mode" (top right)
# 3. Click "Load unpacked"
# 4. Select the extension/ folder from this repo
```

### 2. Open Google Flow

Go to [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow) and sign in. The extension captures your bearer token automatically.

Check the extension popup — you should see:
- Agent connected (once the agent is running)
- Token captured

### 3. Start the Agent

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python -m agent.main

# Or with custom ports
API_HOST=127.0.0.1 API_PORT=8100 WS_PORT=9222 python -m agent.main
```

The agent starts:
- **REST API** on `http://127.0.0.1:8100`
- **WebSocket server** on `ws://127.0.0.1:9222` (extension auto-connects)
- **Background worker** that processes the request queue

### 4. Verify Connection

```bash
curl http://127.0.0.1:8100/health
# {"status":"ok","version":"0.2.0","extension_connected":true}

curl http://127.0.0.1:8100/api/flow/status
# {"connected":true,"flow_key_present":true}

curl http://127.0.0.1:8100/api/flow/credits
# {"credits":...,"userPaygateTier":"PAYGATE_TIER_ONE"}
```

## Usage

### Option A: Full Pipeline (recommended)

Create a project with story, characters, scenes — the agent handles Flow API integration, tier detection, and character profiles automatically.

```bash
# 1. Create project with story and characters
#    - Creates project on Google Flow (gets real projectId)
#    - Auto-detects your paygate tier from credits API
#    - Builds character profiles (description + image_prompt) from story
curl -X POST http://127.0.0.1:8100/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pipip Fish Market",
    "description": "Pipip the cat selling fish, 3D style, VERTICAL",
    "story": "Pipip is a cute orange tabby cat who runs a fish stall at a busy public market. Every morning he arrives at dawn carrying crates of fresh fish, sets up his colorful wooden stall, and charms customers with his playful personality.",
    "characters": [
      {
        "name": "Pipip",
        "description": "A cute orange tabby cat wearing a blue apron, fish seller at the public market"
      }
    ]
  }'
# → {"id": "flow-project-uuid", "story": "...", "user_paygate_tier": "PAYGATE_TIER_ONE", ...}

# 2. Create a video
curl -X POST http://127.0.0.1:8100/api/videos \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<project_id>", "title": "Pipip Story"}'
# → {"id": "vid-uuid", ...}

# 3. Create scenes
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<video_id>",
    "display_order": 0,
    "prompt": "Pipip arrives at the market at dawn with crates of fresh fish",
    "image_prompt": "A cute orange tabby cat in blue apron at a market at sunrise, 3D Pixar-style",
    "video_prompt": "A cute orange tabby cat arranging fish at his market stall, 3D animation",
    "orientation": "VERTICAL",
    "character_names": ["Pipip"]
  }'

# 4. Queue image generation (worker processes automatically)
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "GENERATE_IMAGES",
    "orientation": "VERTICAL",
    "scene_id": "<scene_id>",
    "project_id": "<project_id>",
    "video_id": "<video_id>"
  }'

# 5. Once image is done, queue video generation
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "GENERATE_VIDEO",
    "orientation": "VERTICAL",
    "scene_id": "<scene_id>",
    "project_id": "<project_id>"
  }'

# 6. Check progress
curl http://127.0.0.1:8100/api/requests/pending
curl http://127.0.0.1:8100/api/requests?scene_id=<scene_id>

# 7. Once video is done, queue upscale (optional)
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "UPSCALE_VIDEO",
    "orientation": "VERTICAL",
    "scene_id": "<scene_id>"
  }'
```

The worker automatically:
- Picks up PENDING requests
- **Skips already-COMPLETED assets** (no wasted API calls or reCAPTCHA solves)
- Solves reCAPTCHA via extension (only for generate image/video/upscale)
- Calls the correct Google Flow endpoint with the right model for your tier
- Polls for async operations (video gen, upscale)
- Updates scene status and media URLs
- Retries on failure (up to 5 times)
- Cascade-clears downstream assets on regeneration (regen image → resets video + upscale)

### Option B: Direct API (for testing / one-off)

```bash
# Generate an image (with optional character reference for consistency)
curl -X POST http://127.0.0.1:8100/api/flow/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cute orange tabby cat at a fish market, 3D style",
    "project_id": "<project_id>",
    "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
    "character_media_ids": ["<character_media_id>"]
  }'

# Generate a video from an image
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<media_id from image>",
    "prompt": "The cat arranges fish at his stall",
    "project_id": "<project_id>",
    "scene_id": "<scene_id>",
    "user_paygate_tier": "PAYGATE_TIER_ONE"
  }'

# Check video generation status (no reCAPTCHA required)
curl -X POST http://127.0.0.1:8100/api/flow/check-status \
  -H "Content-Type: application/json" \
  -d '{"operations": [<operations from generate-video response>]}'

# Upscale a video to 4K
curl -X POST http://127.0.0.1:8100/api/flow/upscale-video \
  -H "Content-Type: application/json" \
  -d '{
    "media_id": "<video_media_id>",
    "scene_id": "<scene_id>"
  }'
```

## API Reference

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + extension status |
| **Characters** | | |
| `POST` | `/api/characters` | Create character |
| `GET` | `/api/characters` | List all characters |
| `GET` | `/api/characters/:id` | Get character |
| `PATCH` | `/api/characters/:id` | Update character |
| `DELETE` | `/api/characters/:id` | Delete character |
| **Projects** | | |
| `POST` | `/api/projects` | Create project (calls Flow API + auto-detects tier) |
| `GET` | `/api/projects` | List projects |
| `GET` | `/api/projects/:id` | Get project |
| `PATCH` | `/api/projects/:id` | Update project |
| `DELETE` | `/api/projects/:id` | Delete project |
| `POST` | `/api/projects/:id/characters/:cid` | Link character |
| `DELETE` | `/api/projects/:id/characters/:cid` | Unlink character |
| `GET` | `/api/projects/:id/characters` | List project characters |
| **Videos** | | |
| `POST` | `/api/videos` | Create video |
| `GET` | `/api/videos?project_id=` | List videos |
| `GET` | `/api/videos/:id` | Get video |
| `PATCH` | `/api/videos/:id` | Update video |
| `DELETE` | `/api/videos/:id` | Delete video |
| **Scenes** | | |
| `POST` | `/api/scenes` | Create scene |
| `GET` | `/api/scenes?video_id=` | List scenes |
| `GET` | `/api/scenes/:id` | Get scene |
| `PATCH` | `/api/scenes/:id` | Update scene |
| `DELETE` | `/api/scenes/:id` | Delete scene |
| **Requests** | | |
| `POST` | `/api/requests` | Create request |
| `GET` | `/api/requests` | List requests |
| `GET` | `/api/requests/pending` | List pending |
| `GET` | `/api/requests/:id` | Get request |
| `PATCH` | `/api/requests/:id` | Update request |
| **Flow (Direct)** | | |
| `GET` | `/api/flow/status` | Extension connection status |
| `GET` | `/api/flow/credits` | Google Flow credits + tier |
| `POST` | `/api/flow/generate-image` | Generate image (sync, requires reCAPTCHA) |
| `POST` | `/api/flow/generate-video` | Submit video gen (requires reCAPTCHA) |
| `POST` | `/api/flow/generate-video-refs` | Submit r2v video gen (requires reCAPTCHA) |
| `POST` | `/api/flow/upscale-video` | Submit upscale (requires reCAPTCHA) |
| `POST` | `/api/flow/check-status` | Poll operation status (no reCAPTCHA) |

### Request Types

| Type | Description | Async? | reCAPTCHA? |
|------|-------------|--------|------------|
| `GENERATE_IMAGES` | Generate scene image | No | Yes |
| `GENERATE_VIDEO` | Generate video from image (i2v) | Yes | Yes |
| `GENERATE_VIDEO_REFS` | Generate video from references (r2v) | Yes | Yes |
| `UPSCALE_VIDEO` | Upscale video to 4K | Yes | Yes |
| `GENERATE_CHARACTER_IMAGE` | Generate character reference | No | Yes |
| `CHECK_STATUS` | Poll operation status | No | No |

### Project Creation

`POST /api/projects` now does three things:

1. **Creates project on Google Flow** via tRPC API (`project.createProject`) — gets a real `projectId`
2. **Auto-detects user tier** from `/flow/credits` — uses correct model keys (prevents 403 errors)
3. **Creates characters with profiles** — builds `description` and `image_prompt` from the story context

```json
{
  "name": "Project Name",
  "description": "Short description",
  "story": "Full narrative that drives character profiles and scene generation...",
  "characters": [
    {"name": "Pipip", "description": "A cute orange tabby cat wearing a blue apron"}
  ]
}
```

### Model Mappings

Video and upscale model keys are stored in `agent/models.json` for easy updates when Google Flow changes models:

```json
{
  "video_models": {
    "PAYGATE_TIER_TWO": {
      "frame_2_video": {
        "VIDEO_ASPECT_RATIO_LANDSCAPE": "veo_3_1_i2v_s_fast_ultra",
        "VIDEO_ASPECT_RATIO_PORTRAIT": "veo_3_1_i2v_s_fast_portrait_ultra"
      }
    },
    "PAYGATE_TIER_ONE": { ... }
  },
  "upscale_models": { ... },
  "image_models": { "default": "GEM_PIX_2" }
}
```

### Scene Fields

Each scene stores media for **two orientations** (vertical 9:16 + horizontal 16:9):

```
vertical_image_url / vertical_image_media_id / vertical_image_status
vertical_video_url / vertical_video_media_id / vertical_video_status
vertical_upscale_url / vertical_upscale_media_id / vertical_upscale_status
(same for horizontal_*)
```

Status flow: `PENDING` → `PROCESSING` → `COMPLETED` / `FAILED`

### Scene Chaining

For smooth transitions between scenes, use continuation chains:

```
Scene 0 (ROOT) ──video──► Scene 1 (CONTINUATION)
                          └─ endImage = Scene 0's video mediaGenId
```

Set `parent_scene_id` and `chain_type: "CONTINUATION"` when creating the scene. The worker automatically uses the parent's video as `endImage` for the Google Flow API.

## Architecture

```
agent/
├── main.py              # FastAPI app + WebSocket server
├── config.py            # Configuration (loads models.json)
├── models.json          # Video/upscale/image model mappings (editable)
├── db/
│   ├── schema.py        # SQLite schema (aiosqlite)
│   └── crud.py          # Async CRUD with column whitelisting
├── models/
│   ├── enums.py         # Literal types for validation
│   ├── character.py     # + image_prompt field
│   ├── project.py       # + story, characters input
│   ├── video.py
│   ├── scene.py
│   └── request.py
├── api/
│   ├── characters.py    # REST routes
│   ├── projects.py      # Flow API integration + auto-tier + character profiles
│   ├── videos.py
│   ├── scenes.py
│   ├── requests.py
│   └── flow.py          # Direct Flow API access
├── services/
│   ├── flow_client.py   # WS bridge to extension + Flow tRPC
│   ├── headers.py       # Randomized browser headers
│   ├── scene_chain.py   # Continuation scene logic
│   └── post_process.py  # ffmpeg trim/merge/music
└── worker/
    └── processor.py     # Queue processor + skip-completed guard + poller

extension/
├── manifest.json        # Chrome MV3 + declarativeNetRequest
├── background.js        # WS client, token capture, API proxy, reCAPTCHA
├── content.js           # Bridge to injected.js
├── injected.js          # reCAPTCHA solver (MAIN world)
├── rules.json           # Declarative net request rules
├── popup.html
└── popup.js
```

### How It Works

1. **Extension** captures bearer token from `aisandbox-pa.googleapis.com` requests
2. **Extension** connects to agent's WebSocket server (`ws://127.0.0.1:9222`)
3. **Agent** receives API requests via REST or queue
4. **Agent** sends commands to extension via WS: `{method: "api_request", params: {url, body, captchaAction}}`
5. **Extension** solves reCAPTCHA (only when `captchaAction` is present), injects token, makes API call
6. **Extension** returns result to agent via WS
7. **Worker** polls async operations (video gen, upscale) until completion
8. **Agent** updates scene/request status in SQLite

### reCAPTCHA Usage

Only these operations require reCAPTCHA solving:
- `generate_images` → `captchaAction: "IMAGE_GENERATION"`
- `generate_video` → `captchaAction: "VIDEO_GENERATION"`
- `generate_video_from_references` → `captchaAction: "VIDEO_GENERATION"`
- `upscale_video` → `captchaAction: "VIDEO_GENERATION"`

All other API calls (check status, get credits, upload image, create project) do **not** require reCAPTCHA.

### Google Flow API Endpoints

| Operation | Endpoint | reCAPTCHA |
|-----------|----------|-----------|
| Create Project | `POST labs.google/fx/api/trpc/project.createProject` | No |
| Generate Image | `POST /v1/projects/{id}/flowMedia:batchGenerateImages` | Yes |
| Generate Video | `POST /v1/video:batchAsyncGenerateVideoStartImage` | Yes |
| Generate Video (chain) | `POST /v1/video:batchAsyncGenerateVideoStartAndEndImage` | Yes |
| Generate Video (r2v) | `POST /v1/video:batchAsyncGenerateVideoReferenceImages` | Yes |
| Upscale Video | `POST /v1/video:batchAsyncGenerateVideoUpsampleVideo` | Yes |
| Check Status | `POST /v1/video:batchCheckAsyncVideoGenerationStatus` | No |
| Get Credits | `GET /v1/credits` | No |
| Upload Image | `POST /v1:uploadImage` | No |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `127.0.0.1` | REST API bind address |
| `API_PORT` | `8100` | REST API port |
| `WS_HOST` | `127.0.0.1` | WebSocket server bind |
| `WS_PORT` | `9222` | WebSocket server port |
| `POLL_INTERVAL` | `5` | Worker poll interval (seconds) |
| `MAX_RETRIES` | `5` | Max retries per request |
| `VIDEO_POLL_TIMEOUT` | `420` | Video gen poll timeout (seconds) |

## Post-Processing

After all scenes are generated and upscaled, use the post-process utilities:

```python
from agent.services.post_process import trim_video, merge_videos, add_music

# Trim each scene
trim_video("scene0_4k.mp4", "scene0_trimmed.mp4", start=0, end=6)
trim_video("scene1_4k.mp4", "scene1_trimmed.mp4", start=0, end=4)

# Merge all trimmed scenes
merge_videos(["scene0_trimmed.mp4", "scene1_trimmed.mp4"], "merged.mp4")

# Add background music
add_music("merged.mp4", "music.mp3", "final.mp4", music_volume=0.3)
```

All ffmpeg outputs use `-movflags +faststart` for streaming compatibility.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Extension shows "Agent disconnected" | Make sure `python -m agent.main` is running |
| Extension shows "No token" | Open [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow) and do any action |
| `CAPTCHA_FAILED: NO_FLOW_TAB` | Need a Google Flow tab open in Chrome |
| `CAPTCHA_FAILED: grecaptcha not available` | Wait for the Flow page to fully load |
| API returns 403 MODEL_ACCESS_DENIED | Tier mismatch — auto-detect should handle this, or set `user_paygate_tier` manually |
| API returns 429 | Rate limited — wait and retry |
| Video gen stuck in PROCESSING | Check `/api/requests?status=PROCESSING` — worker polls automatically |
| Duplicate generation requests | Worker skips already-COMPLETED assets automatically |

## License

MIT
