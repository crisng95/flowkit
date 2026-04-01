# Google Flow Agent — Agentic Reference

Base URL: `http://127.0.0.1:8100`

## Pre-flight Check

Before ANY workflow, verify:
```bash
curl -s http://127.0.0.1:8100/health
# Must return: {"extension_connected": true}
# If false: Chrome extension is not connected — nothing will work
```

---

## Rules (MUST follow)

1. **Media ID is always UUID** — format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`. Never use `CAMS...` / base64 strings (that's mediaGenerationId, a different thing).
2. **Scene prompts = ACTION only** — never describe character appearance. Reference images handle visual consistency via `imageInputs`. Write: `"Pippip juggling fish at the market"`. NOT: `"Pippip the orange tabby cat wearing a blue apron juggling fish"`.
3. **All reference images must exist before scene images** — the worker blocks if any referenced entity is missing `media_id`. Generate ALL ref images first, verify all have `media_id`, then generate scene images.
4. **10s cooldown between API calls** — the worker auto-waits. Don't spam requests.
5. **Locations use landscape, characters use portrait** — reference image orientation depends on entity type.
6. **UUID extraction** — if a response gives `CAMS...` instead of UUID, extract UUID from the `fifeUrl` in the response (URL contains it: `/image/{UUID}?...`).
7. **Cascade on regen** — regenerating an image auto-clears downstream video + upscale. Regenerating video auto-clears upscale.

---

## Workflow Recipes

### W1: Create a New Project

Creates project on Google Flow API, detects user tier, creates reference entities.

```bash
curl -X POST http://127.0.0.1:8100/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Project Title",
    "description": "Short description",
    "story": "Full story context used to build character profiles...",
    "language": "en",
    "characters": [
      {"name": "Hero", "entity_type": "character", "description": "Visual appearance only..."},
      {"name": "Castle", "entity_type": "location", "description": "Visual description..."},
      {"name": "Magic Sword", "entity_type": "visual_asset", "description": "Visual description..."}
    ]
  }'
```

**Response:** `{id: "<project_id>", name: "...", user_paygate_tier: "PAYGATE_TIER_ONE|TWO", ...}`

**Entity types:** `character`, `location`, `creature`, `visual_asset`, `generic_troop`, `faction`

**What happens:** Project registered on Google Flow, tier auto-detected, each entity gets `image_prompt` auto-generated with composition guidelines matching its type.

### W2: Create Video + Scenes

```bash
# Create video
curl -X POST http://127.0.0.1:8100/api/videos \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<PID>", "title": "Episode 1", "description": "...", "display_order": 0}'

# Create scenes (chain them)
# Scene 1: ROOT
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<VID>",
    "display_order": 0,
    "prompt": "Hero walks into Castle courtyard at dawn. Magic Sword glowing on the wall. Cinematic wide shot.",
    "character_names": ["Hero", "Castle", "Magic Sword"],
    "chain_type": "ROOT"
  }'

# Scene 2+: CONTINUATION (chain to previous)
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<VID>",
    "display_order": 1,
    "prompt": "Hero reaches for Magic Sword on the Castle wall. Dramatic close-up, glowing light.",
    "character_names": ["Hero", "Castle", "Magic Sword"],
    "chain_type": "CONTINUATION",
    "parent_scene_id": "<previous_scene_id>"
  }'
```

**Scene prompt formula:** `[Character] [action verb] [with/at Asset] [in/at Location]. [Camera/mood/lighting].`

**`character_names`:** List ALL reference entities that should appear — characters, locations, assets. Their `media_id`s get passed as `imageInputs` for visual consistency.

### W3: Generate Reference Images

Create a request for EACH entity. Do this BEFORE scene images.

```bash
# Get entity list
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters

# For each entity:
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "GENERATE_CHARACTER_IMAGE",
    "character_id": "<entity_id>",
    "project_id": "<PID>"
  }'
```

**Poll until done:**
```bash
curl -s http://127.0.0.1:8100/api/requests/<RID>
# Wait for status: "COMPLETED"
```

**Verify ALL entities have media_id:**
```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
# Every entity must have media_id (UUID format) before proceeding
```

**What happens:** Worker generates image with entity-type composition (portrait for characters, landscape for locations), then uploads it via `uploadImage` to get UUID `media_id`.

### W4: Generate Scene Images

Only after ALL reference images are ready.

```bash
# For each scene:
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "GENERATE_IMAGES",
    "scene_id": "<SID>",
    "project_id": "<PID>",
    "video_id": "<VID>",
    "orientation": "VERTICAL"
  }'
```

**Orientation:** `VERTICAL` (portrait 9:16) or `HORIZONTAL` (landscape 16:9)

**What happens:** Worker collects all `media_id`s from entities listed in scene's `character_names`, passes them as `imageInputs`, generates image. If any entity is missing `media_id`, request fails and retries later.

**Verify:**
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
# Check: vertical_image_status = "COMPLETED", vertical_image_media_id = UUID
```

### W5: Generate Videos

Only after scene images are ready.

```bash
# For each scene with a completed image:
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "GENERATE_VIDEO",
    "scene_id": "<SID>",
    "project_id": "<PID>",
    "video_id": "<VID>",
    "orientation": "VERTICAL"
  }'
```

**What happens:** Worker reads scene's `vertical_image_media_id` as `startImage`, submits video gen, polls until complete (can take 2-5 minutes). For CONTINUATION scenes with `parent_scene_id`, also uses `endImage` for smooth transitions.

**Verify:**
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
# Check: vertical_video_status = "COMPLETED", vertical_video_url = GCS URL
```

### W6: Upscale Videos (TIER_TWO only)

```bash
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "UPSCALE_VIDEO",
    "scene_id": "<SID>",
    "project_id": "<PID>",
    "video_id": "<VID>",
    "orientation": "VERTICAL"
  }'
```

**Note:** Upscale to 4K requires `PAYGATE_TIER_TWO`. TIER_ONE will get "caller does not have permission".

### W7: Download + Concat Videos

```bash
# Get scene video URLs
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
# Extract vertical_video_url (or vertical_upscale_url if upscaled) for each scene

# Download each scene video, then concat with ffmpeg:
# 1. Normalize (same codec/resolution/fps)
ffmpeg -y -i scene_1.mp4 -c:v libx264 -preset fast -crf 18 \
  -vf "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2" \
  -r 24 -pix_fmt yuv420p -an scene_1_norm.mp4

# 2. Create concat list
echo "file 'scene_1_norm.mp4'" > concat.txt
echo "file 'scene_2_norm.mp4'" >> concat.txt
# ...

# 3. Concat
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy -movflags +faststart output.mp4
```

---

## Full Pipeline Order

```
1. Health check          GET  /health → extension_connected: true
2. Create project        POST /api/projects (with entities)
3. Create video          POST /api/videos
4. Create scenes         POST /api/scenes (with character_names, chain_type)
5. Gen ref images        POST /api/requests {type: GENERATE_CHARACTER_IMAGE} per entity
   ↳ Wait ALL complete, verify all have media_id (UUID)
6. Gen scene images      POST /api/requests {type: GENERATE_IMAGES} per scene
   ↳ Wait ALL complete, verify vertical_image_media_id (UUID)
7. Gen videos            POST /api/requests {type: GENERATE_VIDEO} per scene
   ↳ Wait ALL complete (2-5 min each)
8. (Optional) Upscale    POST /api/requests {type: UPSCALE_VIDEO} per scene
9. Download + concat     ffmpeg normalize + concat
```

**Between steps 5→6:** MUST verify every entity has `media_id`. If any is missing, scene image gen will block.

**Between steps 6→7:** Verify `vertical_image_media_id` is UUID format for each scene.

---

## API Quick Reference

### CRUD Endpoints

| Resource | Create | List | Get | Update | Delete |
|----------|--------|------|-----|--------|--------|
| Project | `POST /api/projects` | `GET /api/projects` | `GET /api/projects/{pid}` | `PATCH /api/projects/{pid}` | `DELETE /api/projects/{pid}` |
| Character/Entity | `POST /api/characters` | `GET /api/characters` | `GET /api/characters/{cid}` | `PATCH /api/characters/{cid}` | `DELETE /api/characters/{cid}` |
| Video | `POST /api/videos` | `GET /api/videos?project_id=X` | `GET /api/videos/{vid}` | `PATCH /api/videos/{vid}` | `DELETE /api/videos/{vid}` |
| Scene | `POST /api/scenes` | `GET /api/scenes?video_id=X` | `GET /api/scenes/{sid}` | `PATCH /api/scenes/{sid}` | `DELETE /api/scenes/{sid}` |
| Request | `POST /api/requests` | `GET /api/requests` | `GET /api/requests/{rid}` | `PATCH /api/requests/{rid}` | — |

### Special Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Server status + extension connected |
| `GET /api/flow/status` | Extension connection + flow key status |
| `GET /api/flow/credits` | User credits + tier |
| `GET /api/requests/pending` | List pending requests |
| `GET /api/projects/{pid}/characters` | List entities linked to project |
| `POST /api/projects/{pid}/characters/{cid}` | Link entity to project |

### Request Types (for POST /api/requests)

| type | Required fields | What it does |
|------|----------------|-------------|
| `GENERATE_CHARACTER_IMAGE` | `character_id`, `project_id` | Gen ref image → upload → UUID media_id |
| `GENERATE_IMAGES` | `scene_id`, `project_id`, `video_id`, `orientation` | Gen scene image with ref imageInputs |
| `GENERATE_VIDEO` | `scene_id`, `project_id`, `video_id`, `orientation` | Gen video from scene image (i2v) |
| `GENERATE_VIDEO_REFS` | `scene_id`, `project_id`, `video_id`, `orientation` | Gen video from ref images only (r2v) |
| `UPSCALE_VIDEO` | `scene_id`, `project_id`, `video_id`, `orientation` | Upscale video to 4K |

### Request Statuses

`PENDING` → `PROCESSING` → `COMPLETED` or `FAILED`

### Scene Fields (per orientation)

Each scene has vertical + horizontal variants:
- `vertical_image_url`, `vertical_image_media_id`, `vertical_image_status`
- `vertical_video_url`, `vertical_video_media_id`, `vertical_video_status`
- `vertical_upscale_url`, `vertical_upscale_media_id`, `vertical_upscale_status`
- Same for `horizontal_*`

### Entity Types + Image Composition

| entity_type | Aspect Ratio | Composition |
|-------------|-------------|-------------|
| `character` | Portrait | Full body head-to-toe, front-facing, centered, neutral background |
| `location` | Landscape | Establishing shot, level horizon, atmospheric, show depth |
| `creature` | Portrait | Full body, natural stance, distinctive features |
| `visual_asset` | Portrait | Detailed view, textures, materials, scale reference |
| `generic_troop` | Portrait | Military pose, full/three-quarter body |
| `faction` | Portrait | Military pose, full/three-quarter body |

---

## Common Patterns

### Check if all ref images are ready
```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters | \
  python3 -c "import sys,json; entities=json.load(sys.stdin); \
  missing=[e['name'] for e in entities if not e.get('media_id')]; \
  print('READY' if not missing else f'MISSING: {missing}')"
```

### Fix CAMS... media_id on a scene (extract UUID from URL)
```bash
# Get scene, extract UUID from vertical_image_url
curl -s http://127.0.0.1:8100/api/scenes/<SID> | \
  python3 -c "import sys,json,re; s=json.load(sys.stdin); \
  url=s.get('vertical_image_url',''); \
  m=re.search(r'/([0-9a-f-]{36})',url); \
  print(m.group(1) if m else 'NO UUID')"

# Patch with correct UUID
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{"vertical_image_media_id": "<UUID>"}'
```

### Reset a scene for regeneration
```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{
    "vertical_image_status": "PENDING",
    "vertical_image_media_id": null,
    "vertical_image_url": null,
    "vertical_video_status": "PENDING",
    "vertical_video_media_id": null,
    "vertical_video_url": null,
    "vertical_upscale_status": "PENDING",
    "vertical_upscale_media_id": null,
    "vertical_upscale_url": null
  }'
```

---

## File Structure

```
agent/
  main.py              — FastAPI + WS server entry point
  config.py            — All constants (ports, API keys, model keys, cooldown)
  models.json          — Video/image model keys per tier
  db/schema.py         — SQLite schema
  db/crud.py           — Async CRUD operations
  models/              — Pydantic models (project, video, scene, character, request, enums)
  api/                 — REST routes (projects, videos, scenes, characters, requests, flow)
  services/
    flow_client.py     — WS-based API client (sends to extension)
    headers.py         — Randomized browser headers
    post_process.py    — ffmpeg trim/merge/music
    scene_chain.py     — Scene chaining logic
  worker/
    processor.py       — Background worker (processes PENDING requests)
extension/             — Chrome MV3 extension (WS client, reCAPTCHA, API proxy)
scripts/               — Seed/utility scripts
output/                — Generated video output
```
