# Flow Kit — Architecture

## Overview
Standalone system for AI video production: Chrome extension talks to Google Flow API,
Python agent manages data locally via SQLite and orchestrates everything.

## Two Components

### 1. Extension (Chrome)
- Captures Google Flow bearer token (ya29.*) from aisandbox-pa.googleapis.com
- Solves reCAPTCHA v2 (site key: 6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV)
- Wraps ALL Google Flow API endpoints
- Exposes to local agent via WebSocket
- API methods:
  - generate_image(prompt, characters[], orientation) → mediaId + imageUrl
  - generate_video(mediaId, prompt, orientation, endSceneMediaGenId?) → mediaId + videoUrl
  - upscale_video(mediaId, orientation, resolution) → mediaId + videoUrl
  - generate_character_image(name, description) → mediaId + imageUrl
  - get_request_status(requestId) → status + output
  - get_credits() → remaining credits + tier

### 2. Local Agent (Python + SQLite)
- CRUD for projects, videos, scenes, characters
- Track requests/jobs
- Calls extension to gen image/video/upscale
- Post-processing: trim, merge (ffmpeg), add music
- Upload YouTube

## Stack
- Extension: Chrome Manifest V3, vanilla JS
- Agent: Python 3.12+, FastAPI, SQLite
- Communication: WebSocket (extension ↔ agent)

---

## Database Schema

### character (STANDALONE — not owned by project)
```sql
CREATE TABLE character (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    entity_type         TEXT NOT NULL DEFAULT 'character'
                        CHECK(entity_type IN ('character','location','creature','visual_asset','generic_troop','faction')),
    description         TEXT,
    image_prompt        TEXT,
    voice_description   TEXT,       -- max ~30 words, for video prompt voice consistency
    reference_image_url TEXT,
    media_id            TEXT,       -- UUID format from uploadImage
    created_at          DATETIME DEFAULT (datetime('now')),
    updated_at          DATETIME DEFAULT (datetime('now'))
);
```

### project
```sql
CREATE TABLE project (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    thumbnail_url       TEXT,
    language            TEXT DEFAULT 'en',
    status              TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','ARCHIVED')),
    created_at          DATETIME DEFAULT (datetime('now')),
    updated_at          DATETIME DEFAULT (datetime('now'))
);
```

### project_character (link table, M:N)
```sql
CREATE TABLE project_character (
    project_id   TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    character_id TEXT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, character_id)
);
```

### video (belongs to project)
```sql
CREATE TABLE video (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    display_order   INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','PROCESSING','COMPLETED','FAILED')),
    vertical_url    TEXT,
    horizontal_url  TEXT,
    thumbnail_url   TEXT,
    duration        REAL,
    resolution      TEXT,
    youtube_id      TEXT,
    privacy         TEXT DEFAULT 'unlisted',
    tags            TEXT,
    created_at      DATETIME DEFAULT (datetime('now')),
    updated_at      DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX idx_video_project ON video(project_id);
```

### scene (belongs to video, chainable, dual orientation)
```sql
CREATE TABLE scene (
    id                  TEXT PRIMARY KEY,
    video_id            TEXT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    display_order       INTEGER DEFAULT 0,
    prompt              TEXT,           -- image generation prompt (frame 0)
    image_prompt        TEXT,           -- override for image gen (optional)
    video_prompt        TEXT,           -- sub-clip timing: "0-3s: ... 3-5s: ... 5-8s: ..."
    character_names     TEXT,           -- JSON array of reference entity names

    -- Chain
    parent_scene_id     TEXT REFERENCES scene(id),
    chain_type          TEXT DEFAULT 'ROOT' CHECK(chain_type IN ('ROOT','CONTINUATION','INSERT')),

    -- Vertical
    vertical_image_url              TEXT,
    vertical_video_url              TEXT,
    vertical_upscale_url            TEXT,
    vertical_image_media_id     TEXT,
    vertical_video_media_id     TEXT,
    vertical_upscale_media_id   TEXT,
    vertical_image_status           TEXT DEFAULT 'PENDING',
    vertical_video_status           TEXT DEFAULT 'PENDING',

    -- Horizontal
    horizontal_image_url            TEXT,
    horizontal_video_url            TEXT,
    horizontal_upscale_url          TEXT,
    horizontal_image_media_id   TEXT,
    horizontal_video_media_id   TEXT,
    horizontal_upscale_media_id TEXT,
    horizontal_image_status         TEXT DEFAULT 'PENDING',
    horizontal_video_status         TEXT DEFAULT 'PENDING',

    -- Chain source
    vertical_end_scene_media_id   TEXT,
    horizontal_end_scene_media_id TEXT,

    -- Trim
    trim_start  REAL,
    trim_end    REAL,
    duration    REAL,

    created_at  DATETIME DEFAULT (datetime('now')),
    updated_at  DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX idx_scene_video ON scene(video_id);
CREATE INDEX idx_scene_parent ON scene(parent_scene_id);
```

### request (job tracking)
```sql
CREATE TABLE request (
    id              TEXT PRIMARY KEY,
    project_id      TEXT REFERENCES project(id),
    video_id        TEXT REFERENCES video(id),
    scene_id        TEXT REFERENCES scene(id),
    character_id    TEXT REFERENCES character(id),
    type            TEXT NOT NULL CHECK(type IN ('GENERATE_IMAGE','REGENERATE_IMAGE','EDIT_IMAGE','GENERATE_VIDEO','GENERATE_VIDEO_REFS','UPSCALE_VIDEO','GENERATE_CHARACTER_IMAGE','REGENERATE_CHARACTER_IMAGE','EDIT_CHARACTER_IMAGE')),
    orientation     TEXT CHECK(orientation IN ('VERTICAL','HORIZONTAL')),
    status          TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    request_id      TEXT,
    media_id    TEXT,
    output_url      TEXT,
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    created_at      DATETIME DEFAULT (datetime('now')),
    updated_at      DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX idx_request_scene ON request(scene_id);
CREATE INDEX idx_request_status ON request(status);
```

---

## Video AI SDK

Domain-model layer that wraps FlowClient operations with type-safe classes.

### Two Execution Modes

```python
# 1. Queue-based (async — background processor picks up)
request_id = await scene.generate_image(project_id="...")
# Returns immediately. Poll request status to know when done.

# 2. Direct execution (blocking — calls FlowClient immediately)
result = await scene.execute_generate_image(project_id="...")
if result.success:
    print(result.media_id, result.url)
else:
    print(result.error)
```

### Domain Models (`agent/sdk/models/`)

| Model | Key Methods |
|-------|------------|
| `Project` | `get()`, `create()`, `add_character()`, `get_characters()`, `add_video()`, `get_videos()` |
| `Video` | `add_scene()`, `get_scenes()`, `remove_scene()`, `move_scene()` |
| `Scene` | `generate_image()`, `edit_image()`, `generate_video()`, `upscale_video()` (queue) |
| | `execute_generate_image()`, `execute_edit_image()`, `execute_generate_video()`, `execute_generate_video_refs()`, `execute_upscale_video()` (direct) |
| `Character` | `generate_image()`, `edit_image()` (queue), `execute_generate_image()`, `execute_edit_image()` (direct) |

### Value Objects (`agent/sdk/models/media.py`)

- `MediaAsset` — status + media_id + url for one asset
- `OrientationSlot` — image/video/upscale MediaAssets for one orientation
- `GenerationResult` — success/error + media_id + url from direct execution

### Services (`agent/sdk/services/`)

- `OperationService` — direct FlowClient execution (generate, edit, video, upscale, reference images) + queue wrappers
- `result_handler` — shared result parsing + DB update logic (used by both direct SDK path and background processor)

### Architecture

```
Scene.execute_generate_image()
  → OperationService.generate_scene_image()  (calls FlowClient)
  → result_handler.parse_result()            (extract media_id, url)
  → result_handler.apply_scene_result()      (update DB + cascade)
  → update local OrientationSlot             (in-memory sync)

Scene.generate_image()
  → OperationService.queue_scene_image()     (create DB request)
  → processor picks up PENDING               (background)
  → OperationService.generate_scene_image()  (same direct method)
  → result_handler.apply_scene_result()      (same DB update)
```

### Cascade Rules

- Regenerate image → clears video + upscale (downstream)
- Regenerate video → clears upscale
- Upscale → no cascade

---

## File Structure
```
google-flow-agent/
├── extension/
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   └── popup.js
├── agent/
│   ├── main.py
│   ├── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   └── crud.py
│   ├── models/              ← Pydantic models (API layer)
│   │   ├── project.py
│   │   ├── video.py
│   │   ├── scene.py
│   │   ├── character.py
│   │   ├── request.py
│   │   └── enums.py
│   ├── sdk/                 ← Video AI SDK
│   │   ├── models/
│   │   │   ├── base.py          (DomainModel with save/reload)
│   │   │   ├── media.py         (MediaAsset, OrientationSlot, GenerationResult)
│   │   │   ├── scene.py         (Scene — queue + direct execution)
│   │   │   ├── character.py     (Character — queue + direct execution)
│   │   │   ├── project.py       (Project — CRUD + relationships)
│   │   │   └── video.py         (Video — scene management)
│   │   ├── services/
│   │   │   ├── operations.py    (OperationService — FlowClient bridge)
│   │   │   └── result_handler.py (parse_result, apply_scene_result)
│   │   └── persistence/
│   │       ├── base.py          (Repository interface)
│   │       └── sqlite_repository.py
│   ├── api/
│   │   ├── projects.py
│   │   ├── videos.py
│   │   ├── scenes.py
│   │   ├── characters.py
│   │   ├── requests.py
│   │   └── flow.py
│   ├── services/
│   │   ├── flow_client.py
│   │   ├── scene_chain.py
│   │   └── post_process.py
│   └── worker/
│       ├── processor.py     (thin dispatcher, uses OperationService)
│       └── _parsing.py      (shared extraction helpers)
├── skills/                  ← AI agent skills
└── requirements.txt
```

---

## Reference Repos (READ ONLY)
- /tmp/veogent-flow-connect/ — existing Chrome extension (study background.js for token capture + WS patterns)
- /tmp/vgen-agent-backend/src/modules/scene/scene.d.ts — Scene TypeScript types
- /tmp/vgen-agent-backend/src/modules/request/request.d.ts — Request DTOs with all input data types
- /tmp/vgen-agent-video-processor/app/video/api_client.py — Google Flow API client (KEY FILE for API endpoints, auth, request/response)
- /tmp/vgen-agent-video-processor/app/worker/ — Worker patterns
- /tmp/vgen-agent-video-processor/app/image/ — Image generation patterns
- /tmp/vgen-agent-video-processor/app/config.py — Config

## Key Google Flow API Details
- Endpoint: aisandbox-pa.googleapis.com
- Auth: Bearer ya29.* token (captured by extension from Google Labs session)
- reCAPTCHA v2 enterprise required for most calls
- Each generated asset gets a unique mediaId (base64-encoded protobuf)
- Video generation is async: submit → poll → get result
- Upscale also async with same pattern
- endScene parameter chains video from previous scene's mediaId
