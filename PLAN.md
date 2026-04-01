# google-flow-agent — Revised Plan

## What We're Building

A **standalone** system (no Veogent dependency) that lets a local Python agent generate AI videos via Google Flow API, using a Chrome extension as the browser bridge.

```
┌──────────────────┐     WebSocket      ┌──────────────────────┐
│  Python Agent    │◄──────────────────►│  Chrome Extension     │
│  (FastAPI+SQLite)│     localhost:9222  │  (MV3 Service Worker) │
│                  │                    │                       │
│  - REST API      │  ── commands ──►   │  - Token capture      │
│  - Queue worker  │  ◄── results ──    │  - reCAPTCHA solve    │
│  - Post-process  │                    │  - API proxy          │
│  - DB            │                    │  (on labs.google)     │
└──────────────────┘                    └──────────────────────┘
```

## Architecture Decisions

### Communication: Agent runs WS server, Extension connects as client
- Chrome MV3 service workers **cannot** run WebSocket servers
- Agent runs WS server on `localhost:9222`
- Extension connects to agent's WS server on startup + auto-reconnect
- Protocol: JSON messages with `{id, method, params}` → `{id, result/error}`

### Google Flow API — Real Endpoints (from production code)

| Operation | Endpoint | captchaAction |
|-----------|----------|---------------|
| **Generate Image** | `POST /v1/projects/{projectId}/flowMedia:batchGenerateImages` | `IMAGE_GENERATION` |
| **Generate Video (start frame)** | `POST /v1/video:batchAsyncGenerateVideoStartImage` | `VIDEO_GENERATION` |
| **Generate Video (start+end)** | `POST /v1/video:batchAsyncGenerateVideoStartAndEndImage` | `VIDEO_GENERATION` |
| **Generate Video (references)** | `POST /v1/video:batchAsyncGenerateVideoReferenceImages` | `VIDEO_GENERATION` |
| **Upscale Video** | `POST /v1/video:batchAsyncGenerateVideoUpsampleVideo` | `VIDEO_GENERATION` |
| **Upscale Image** | `POST /v1/flow/upsampleImage` | `IMAGE_GENERATION` |
| **Upload Image** | `POST /v1:uploadImage` | none |
| **Check Video Status** | `POST /v1/video:batchCheckAsyncVideoGenerationStatus` | none |
| **Get Credits** | `GET /v1/credits` | none |
| **Get Media** | `GET /v1/media/{mediaId}` | none |

Base: `https://aisandbox-pa.googleapis.com`
API Key (query param): `AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY`

### Payload Structure (from production)

Every generation request has:
```json
{
  "clientContext": {
    "projectId": "<numeric_project_id>",
    "recaptchaContext": {
      "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
      "token": "<solved_token>"
    },
    "sessionId": ";<timestamp_ms>",
    "tool": "PINHOLE",
    "userPaygateTier": "PAYGATE_TIER_TWO"
  },
  "requests": [{ ... }]
}
```

#### Image Generation Request (without character refs)
```json
{
  "seed": 123456,
  "prompt": "...",
  "imageAspectRatio": "IMAGE_ASPECT_RATIO_PORTRAIT",
  "imageModelName": "GEM_PIX_2",
  "clientContext": { "projectId": "...", "tool": "PINHOLE", "recaptchaContext": {...}, "sessionId": "..." }
}
```

#### Image Generation Request (with character refs — edit_image flow)
Same endpoint (`batchGenerateImages`), same wrapper. Each request item adds `imageInputs`:
```json
{
  "imageInputs": [
    {"name": "<character_media_id>", "imageInputType": "IMAGE_INPUT_TYPE_BASE_IMAGE"}
  ]
}
```

**Character media_id lifecycle:**
1. Character has a reference image URL (`imageUri` / `reference_image_url`)
2. Upload via `POST /v1:uploadImage` → returns `{mediaId: {mediaId: "actual_id"}}`
3. Store `actual_id` as character's `media_id`
4. Before using in image gen, validate: `GET /v1/media/{media_id}` → 200 = valid
5. If expired/invalid → re-upload reference image → update `media_id`
6. Pass valid IDs as `imageInputs` in `batchGenerateImages`

**This is different from scene image `mediaId`!**
- Character `media_id` = from `uploadImage` (user-uploaded reference)
- Scene image `mediaId` = from `batchGenerateImages` response (AI-generated)
- Video `startImage.mediaId` = scene image's `mediaId`
```

#### Image Generation Response
```json
{
  "media": [
    {
      "image": {
        "generatedImage": {
          "mediaId": "CkIK...",  // ← KEY: used as startImage.mediaId for video gen
          "encodedImage": "base64...",       // legacy (may be null)
          "fifeUrl": "https://...",          // public URL (new flow)
          "imageUri": "https://..."          // alias
        }
      }
    }
  ]
}
```

#### Upload Image Response
```json
{
  "mediaId": {
    "mediaId": "actual_media_id"  // ← nested!
  }
}
```

#### Video Generation Request (start image)
```json
{
  "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
  "seed": 1234,
  "textInput": { "prompt": "..." },
  "videoModelKey": "veo_3_1_i2v_s_fast_portrait_ultra",
  "startImage": { "mediaId": "<media_id>" },
  "metadata": { "sceneId": "..." }
}
```

#### Video Generation Request (start + end image)
Same as above but add:
```json
{ "endImage": { "mediaId": "<end_media_id>" } }
```

#### Upscale Video Request
```json
{
  "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
  "resolution": "VIDEO_RESOLUTION_4K",
  "seed": 12345,
  "metadata": { "sceneId": "..." },
  "videoInput": { "mediaId": "<media_id>" },
  "videoModelKey": "veo_3_1_upsampler_4k"
}
```

### Video Model Keys (tier-dependent)

| Type | Portrait (TIER_TWO) | Landscape (TIER_TWO) |
|------|---------------------|----------------------|
| frame→video | `veo_3_1_i2v_s_fast_portrait_ultra` | `veo_3_1_i2v_s_fast_ultra` |
| start+end→video | `veo_3_1_i2v_s_fast_portrait_ultra_fl` | `veo_3_1_i2v_s_fast_ultra_fl` |
| reference→video | `veo_3_0_r2v_fast_portrait_ultra` | `veo_3_0_r2v_fast_ultra` |
| upscale 4K | `veo_3_1_upsampler_4k` | `veo_3_1_upsampler_4k` |
| upscale 1080p | `veo_3_1_upsampler_1080p` | `veo_3_1_upsampler_1080p` |

TIER_ONE uses non-`_ultra` variants.

### reCAPTCHA Flow (from production extension)

3-layer architecture:
1. **injected.js** — runs in MAIN world on `labs.google`, calls `grecaptcha.enterprise.execute(SITE_KEY, {action})` 
2. **content.js** — bridge between background and injected.js via CustomEvents
3. **background.js** — receives captcha requests, forwards to content.js, gets token back

Flow:
```
Agent → WS → background.js → chrome.tabs.sendMessage → content.js 
→ CustomEvent('GET_CAPTCHA') → injected.js → grecaptcha.enterprise.execute()
→ CustomEvent('CAPTCHA_RESULT') → content.js → sendResponse → background.js 
→ WS → Agent
```

Site key: `6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV`

### Headers (from production)

Randomized browser fingerprint headers required:
- `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`
- `x-browser-channel`, `x-browser-copyright`, `x-browser-year`
- `x-browser-validation` (rotated from pool)
- `x-client-data` (rotated from pool)
- `user-agent` (rotated Chrome versions)
- `origin: https://labs.google`, `referer: https://labs.google/`

### Aspect Ratios

| Type | Portrait | Landscape |
|------|----------|-----------|
| Image | `IMAGE_ASPECT_RATIO_PORTRAIT` | `IMAGE_ASPECT_RATIO_LANDSCAPE` |
| Video | `VIDEO_ASPECT_RATIO_PORTRAIT` | `VIDEO_ASPECT_RATIO_LANDSCAPE` |

---

## Components to Build

### 1. Extension (Chrome MV3) — `extension/`

| File | Purpose |
|------|---------|
| `manifest.json` | MV3, permissions: storage/alarms/tabs/webRequest/scripting |
| `background.js` | WS client → agent, task dispatch, token capture, API proxy |
| `content.js` | Bridge background↔injected via CustomEvents |
| `injected.js` | MAIN world: `grecaptcha.enterprise.execute()` |
| `popup.html/js` | Status display (connected, token age, queue) |

**Key differences from current scaffold:**
- Extension is WS **client** (connects to agent), not server
- Has full 3-layer reCAPTCHA solving
- API calls happen IN the extension (browser context, residential IP, cookies)
- Token capture via `webRequest.onBeforeSendHeaders`

### 2. Agent — `agent/`

| Module | Files | Purpose |
|--------|-------|---------|
| `main.py` | 1 | FastAPI app + WS server (dual) |
| `config.py` | 1 | All config constants |
| `db/` | 3 | schema.py, crud.py, __init__.py (aiosqlite!) |
| `models/` | 6 | Pydantic models with Literal types |
| `api/` | 6 | REST routes (characters, projects, videos, scenes, requests, ws) |
| `services/` | 4 | flow_client, scene_chain, post_process, headers |
| `worker/` | 2 | processor, status_poller |

**Key fixes from review:**
- Use `aiosqlite` for all DB operations (async, non-blocking)
- WS server in agent (not client)
- flow_client sends commands over WS, extension executes API calls
- Add Literal types for enums
- Add CORS middleware
- Bind to `127.0.0.1` by default
- Add proper header randomization
- Cleanup pending futures on disconnect
- Fix `_now()` format
- Add `ON DELETE CASCADE` to request FKs
- Add upscale_status columns

### 3. Flow Client Protocol

Agent → Extension messages:
```json
{"id": "uuid", "method": "api_request", "params": {
  "url": "https://aisandbox-pa.googleapis.com/v1/...",
  "method": "POST",
  "headers": {...randomized...},
  "body": {...payload...},
  "captchaAction": "VIDEO_GENERATION"
}}
```

Extension → Agent responses:
```json
{"id": "uuid", "status": 200, "data": {...response...}}
{"id": "uuid", "status": 403, "error": "reCAPTCHA failed"}
```

Special messages:
- `{"type": "token_captured", "flowKey": "ya29.xxx"}` — extension notifies agent
- `{"type": "status"}` — agent queries extension state
- `{"type": "ping"}` / `{"type": "pong"}` — keepalive

---

## Build Order

### Phase 1: Extension (the hard part)
1. `injected.js` — reCAPTCHA solver (copy from production, it's 37 lines)
2. `content.js` — bridge (copy from production, it's 38 lines)
3. `manifest.json` — permissions, web_accessible_resources for injected.js
4. `background.js` — WS client, token capture, API proxy handler
5. `popup.html/js` — basic status

### Phase 2: Agent Core
1. `config.py` — all constants
2. `db/schema.py` — fixed schema (aiosqlite, cascades, upscale_status)
3. `db/crud.py` — async CRUD with column whitelist
4. `models/` — Pydantic with Literal enums
5. `services/headers.py` — randomized header generation (from production)
6. `services/flow_client.py` — WS-based, sends to extension, handles responses

### Phase 3: Agent API + Worker
1. `api/` — REST routes with CORS, validation, auth
2. `api/ws.py` — WebSocket endpoint for extension
3. `worker/processor.py` — async queue processor
4. `worker/status_poller.py` — polls video generation status
5. `main.py` — FastAPI + WS server lifespan
6. `services/post_process.py` — ffmpeg (already good)
7. `services/scene_chain.py` — chain logic (already good)

### Phase 4: Test & Polish
1. Test extension in Chrome with real Flow tab
2. Test end-to-end: create project → generate image → generate video
3. Add error handling, retry logic
4. Push to GitHub

---

## What's Reusable from Current Scaffold

| Component | Status | Notes |
|-----------|--------|-------|
| `ARCHITECTURE.md` | ✅ Keep | Good overview |
| `requirements.txt` | 🔧 Fix | Add `aiosqlite`, `websockets` |
| `agent/config.py` | 🔧 Fix | Change host to 127.0.0.1, add header pools |
| `agent/db/schema.py` | 🔧 Fix | Switch to aiosqlite, add upscale_status, fix cascades |
| `agent/db/crud.py` | 🔄 Rewrite | Async + column whitelist |
| `agent/models/` | 🔧 Fix | Add Literal types, fix character_names |
| `agent/api/` | 🔧 Fix | Add CORS, auth, validation, WS endpoint |
| `agent/services/flow_client.py` | 🔄 Rewrite | WS-based, don't call API directly |
| `agent/services/post_process.py` | ✅ Keep | Already correct |
| `agent/services/scene_chain.py` | ✅ Keep | Already correct |
| `agent/worker/processor.py` | 🔧 Fix | Async DB calls |
| `agent/main.py` | 🔧 Fix | Add WS server, CORS, auth |
| `extension/*` | 🔄 Rewrite | Everything wrong |
