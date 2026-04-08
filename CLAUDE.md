# Google Flow Agent — Agentic Reference

Base URL: `http://127.0.0.1:8100`

## Pre-flight Check

Before ANY workflow, verify:
```bash
curl -s http://127.0.0.1:8100/health
# Must return: {"extension_connected": true}
# If false: Chrome extension is not connected — nothing will work

# Statusline should show at bottom of Claude Code:
# GLA: Ext:Ok T2 Auth:Ok ProjectName 40sc img:40 vid:40 4K:26 Q:0→0/5
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
8. **REGENERATE vs GENERATE** — `GENERATE_IMAGE` skips if image already exists (COMPLETED). Use `REGENERATE_IMAGE` to force a fresh generation (bypasses skip, cascades downstream). Same pattern: `REGENERATE_CHARACTER_IMAGE` clears existing ref image and generates from scratch.
9. **Edit image includes character refs** — `EDIT_IMAGE` automatically resolves character references from the scene's `character_names` and sends them as imageInputs after the base image: `[base_image, char_A, char_B, ...]`. This helps Google Flow detect and maintain character consistency during edits. Same for `EDIT_CHARACTER_IMAGE`.
10. **Video prompts use sub-clip timing** — structure 8s video as time segments. The scene image is frame 0. Each segment: `[camera] + [action] + [dialogue]`.
11. **Use cinematic camera language** — each sub-clip specifies camera angle + movement + lighting. See `skills/camera-guide.md` for full reference. Follow the emotional arc: wide (opening) → medium+push in (rising) → close-up (peak) → pull back wide (release).
12. **Character dialogue in sub-clips** — embed speech in quotes: `"0-3s: Medium tracking shot, Luna walks to bed. Luna says 'Bye mom, I love you, see you tomorrow.'"` Rules: max 10-15 words per character per 2-3s, multi-character exchanges OK (label each speaker: `Luna asks "Ready?" Hero replies "Let's go."`), use delivery verbs (says, whispers, shouts, asks, replies), silent segments are powerful.
13. **Voice descriptions on characters** — `voice_description` field (max ~30 words) auto-appended to video prompts. Dialogue tone must match voice profile.
14. **No background music** — the worker auto-appends "No background music. Keep only natural sound effects." to all video prompts.
15. **Server handles throttling** — the worker enforces max 5 concurrent requests and 10s cooldown automatically. Use `POST /api/requests/batch` to submit ALL requests at once. Do NOT manually batch in groups of 5 — that complexity lives server-side. Poll `GET /api/requests/batch-status?video_id=<VID>` for aggregate progress.
16. **Image Material required on project** — every project must have a `material` field (e.g., `realistic`, `3d_pixar`, `anime`, `stop_motion`, `minecraft`, `oil_painting`). Material controls image_prompt style for entities AND scene_prefix for scenes. List available: `GET /api/materials`.
17. **TTS voice template first** — before narrating scenes, create a voice template (`POST /api/tts/templates`) and verify the voice. Use the template as `ref_audio` for voice cloning to ensure consistent narrator voice across all scenes. CPU-only (MPS produces gibberish).
18. **Statusline** — GLA statusline auto-shows at bottom of Claude Code. Configured by `setup.sh`. Shows: extension status, auth, tier, project, scene counts, img/vid/4K progress, queue. Reads Claude session stats from stdin for model/ctx%/rate limits.
19. **Token auto-refresh** — Extension refreshes token every 45 min. Auto-opens Flow tab if none exists. Side panel warns when token stale (>60 min). Resends cached token on WS reconnect.
20. **No throwaway scripts** — NEVER write a Python script, shell script, or any file to loop over API requests. All operations must be done inline with `curl` calls. To submit N requests, use `POST /api/requests/batch`. The server throttles automatically — no loops needed.
21. **Scenes are mutable** — use `PATCH /api/scenes/{sid}` to update `prompt`, `video_prompt`, `narrator_text`, `character_names` after creation. Don't delete and recreate — patch instead.
22. **Fact-check before scripting** — ALWAYS research events via web search before writing project stories, scene prompts, or narrator text.
23. **Review before upscale** — ALWAYS run `/gla:review-video` (light mode) after video generation and before upscaling. Scenes scoring < 7.5 get their `video_prompt` updated based on review errors/fix_guide, then regen video. Max 2 review-regen cycles per scene. See `skills/gla:review-video.md` for error catalog and scoring. Facts (events, dates, names, operations, outcomes) MUST match real sources. Editorial opinion and analysis are allowed but must be framed as such. Never invent events, operation names, or statistics. See `content_policy` in channel rules for full guidelines.

**Complete video_prompt example:**
```
0-3s: Medium tracking shot following Luna to her bed, warm lamplight. Luna says "Bye mom, I love you, see you tomorrow."
3-5s: Close-up of Luna's hand reaching for the bedside lamp. Luna whispers "Goodnight, stars."
5-8s: Static wide shot through bedroom window, starry night sky, moonlight shadows. Silence, gentle wind.
```

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
      {"name": "Hero", "entity_type": "character", "description": "Visual appearance only...", "voice_description": "Deep calm heroic voice, speaks slowly with confidence"},
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
# - prompt: for IMAGE generation (what the still frame looks like)
# - video_prompt: for VIDEO generation (sub-clip timing within 8s)
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<VID>",
    "display_order": 0,
    "prompt": "Hero walks into Castle courtyard at dawn. Magic Sword glowing on the wall. Cinematic wide shot.",
    "video_prompt": "0-3s: Hero pushes open the Castle gate and steps into the courtyard. 3-6s: Hero looks up and sees Magic Sword glowing on the wall. 6-8s: Slow zoom on Magic Sword, golden light pulses.",
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
    "video_prompt": "0-2s: Hero walks toward Magic Sword on the Castle wall. 2-5s: Close-up of Hero hand reaching out, fingers wrapping around the hilt. 5-8s: Hero pulls Magic Sword free, burst of golden light fills the room.",
    "character_names": ["Hero", "Castle", "Magic Sword"],
    "chain_type": "CONTINUATION",
    "parent_scene_id": "<previous_scene_id>"
  }'
```

**Scene has TWO prompts:**
- `prompt`: describes the **still image** (frame 0) — `[Character] [action] [at Location]. [Camera/mood].`
- `video_prompt`: describes the **8s video motion** with sub-clip timing — `0-3s: [action]. 3-6s: [action]. 6-8s: [action].`

The worker auto-appends voice context + "no background music" to video_prompt before sending to the API.

**`character_names`:** List ALL reference entities that should appear — characters, locations, assets. Their `media_id`s get passed as `imageInputs` for visual consistency.

### W3: Generate Reference Images

Do this BEFORE scene images. Submit all entities in one batch call.

```bash
# Get entity list
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters

# Submit ALL entities at once — server handles throttling (max 5 concurrent, 10s cooldown)
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{"requests": [
    {"type": "GENERATE_CHARACTER_IMAGE", "character_id": "<CID1>", "project_id": "<PID>"},
    {"type": "GENERATE_CHARACTER_IMAGE", "character_id": "<CID2>", "project_id": "<PID>"}
  ]}'
```

**Poll aggregate status:**
```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?project_id=<PID>&type=GENERATE_CHARACTER_IMAGE"
# Wait for: "done": true
```

**Verify ALL entities have media_id:**
```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
# Every entity must have media_id (UUID format) before proceeding
```

**What happens:** Worker generates image with entity-type composition (portrait for characters, landscape for locations), then uploads it via `uploadImage` to get UUID `media_id`.

### W4: Generate Scene Images

Only after ALL reference images are ready. Submit all scenes in one batch call.

```bash
# Submit ALL scenes at once — server handles throttling
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{"requests": [
    {"type": "GENERATE_IMAGE", "scene_id": "<SID1>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "VERTICAL"},
    {"type": "GENERATE_IMAGE", "scene_id": "<SID2>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "VERTICAL"}
  ]}'
```

**Orientation:** `VERTICAL` (portrait 9:16) or `HORIZONTAL` (landscape 16:9)

**Poll aggregate status:**
```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_IMAGE"
# Wait for: "done": true
```

**What happens:** Worker collects all `media_id`s from entities listed in scene's `character_names`, passes them as `imageInputs`, generates image. If any entity is missing `media_id`, request fails and retries later.

**Verify:**
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
# Check: vertical_image_status = "COMPLETED", vertical_image_media_id = UUID
```

### W5: Generate Videos

Only after scene images are ready. Submit all scenes in one batch call.

```bash
# Submit ALL scenes at once — server handles throttling
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{"requests": [
    {"type": "GENERATE_VIDEO", "scene_id": "<SID1>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "VERTICAL"},
    {"type": "GENERATE_VIDEO", "scene_id": "<SID2>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "VERTICAL"}
  ]}'
```

**Poll aggregate status (videos take 2-5 min each):**
```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
# Wait for: "done": true (poll every 30s)
```

**What happens:** Worker reads scene's `vertical_image_media_id` as `startImage`, submits video gen, polls until complete. For CONTINUATION scenes with `parent_scene_id`, also uses `endImage` for smooth transitions.

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
# Get project output dir (creates dir + meta.json)
OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
# e.g. OUT=output/chien_dich_giai_cuu_f_15e

# Get scene video URLs
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
# Extract vertical_video_url (or vertical_upscale_url if upscaled) for each scene

# Download each scene video into output dir:
# curl -s "<vertical_video_url>" -o "${OUT}/scenes/scene_01.mp4"
# (for 4K: save to ${OUT}/4k/scene_01.mp4)

# Concat with ffmpeg:
# 1. Normalize (same codec/resolution/fps) into ${OUT}/norm/
ffmpeg -y -i "${OUT}/scenes/scene_1.mp4" -c:v libx264 -preset fast -crf 18 \
  -vf "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2" \
  -r 24 -pix_fmt yuv420p -an "${OUT}/norm/scene_1_norm.mp4"

# 2. Create concat list
echo "file '${OUT}/norm/scene_1_norm.mp4'" > concat.txt
echo "file '${OUT}/norm/scene_2_norm.mp4'" >> concat.txt
# ...

# 3. Concat to final output
SLUG=$(basename "$OUT")
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy -movflags +faststart "${OUT}/${SLUG}_final.mp4"
```

### W8: Get Project Output Directory

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir
```

Returns slug + path + meta. Auto-creates directory structure + meta.json on first call.

---

## Full Pipeline Order

```
0.  Health check          GET  /health → extension_connected: true
1.  Research              /gla:research "topic" (fact-check via web search, save to .omc/research/)
2.  Create project        POST /api/projects (with entities + material, story from research)
2.5 Get output dir        GET  /api/projects/{pid}/output-dir (creates dir + meta.json)
3.  Create video          POST /api/videos
4.  Create scenes         POST /api/scenes (with character_names, chain_type, narrator_text)
5.  Gen ref images        POST /api/requests/batch (all entities)
    ↳ Poll: GET /api/requests/batch-status?project_id=<PID>&type=GENERATE_CHARACTER_IMAGE
    ↳ Wait for done=true, verify all entities have media_id (UUID)
6.  Gen scene images      POST /api/requests/batch (all scenes)
    ↳ Poll: GET /api/requests/batch-status?video_id=<VID>&type=GENERATE_IMAGE
    ↳ Wait for done=true, verify image_media_id (UUID)
7.  Gen videos            POST /api/requests/batch (all scenes)
    ↳ Poll every 30s: GET /api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO
    ↳ Wait for done=true (videos take 2-5 min each)
7.5 Review videos         POST /api/videos/{vid}/review?project_id=<PID>&mode=light
    ↳ Scores each scene (0-10) on 6 dimensions via Claude Vision
    ↳ Pass: score >= 7.5 | Fail: update video_prompt from errors → regen → re-review (max 2 cycles)
8.  (Optional) Upscale    POST /api/requests/batch (TIER_TWO only)
    ↳ Poll: GET /api/requests/batch-status?video_id=<VID>&type=UPSCALE_VIDEO
9.  (Optional) TTS        Create voice template → POST /api/videos/{vid}/narrate
    ↳ Requires narrator_text on scenes + voice template
10. Download + concat     ffmpeg normalize + mix narration + concat
```

**Server handles throttling:** The worker enforces max 5 concurrent + 10s cooldown. Submit ALL requests via `/batch` — do NOT manually stagger or loop.

**Between steps 5→6:** MUST verify every entity has `media_id`. If any is missing, scene image gen will block.

**Between steps 6→7:** Verify `image_media_id` is UUID format for each scene.

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
| Request (batch) | `POST /api/requests/batch` | — | — | — | — |

### Special Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Server status + extension connected |
| `GET /api/flow/status` | Extension connection + flow key status |
| `GET /api/flow/credits` | User credits + tier |
| `POST /api/requests/batch` | Submit N requests at once; server throttles automatically |
| `GET /api/requests/batch-status?video_id=X` | Aggregate status (total/pending/processing/completed/failed/done) |
| `GET /api/requests?video_id=X&project_id=Y` | List requests filtered by video and/or project |
| `GET /api/requests/pending` | List pending requests |
| `GET /api/projects/{pid}/characters` | List entities linked to project |
| `POST /api/projects/{pid}/characters/{cid}` | Link entity to project |
| `GET /api/projects/{pid}/output-dir` | Get/create project output directory + meta.json |
| `WS /ws/dashboard` | Real-time push events to extension side panel |

### Request Types (for POST /api/requests)

| type | Required fields | What it does |
|------|----------------|-------------|
| `GENERATE_CHARACTER_IMAGE` | `character_id`, `project_id` | Gen ref image → upload → UUID media_id (skips if already exists) |
| `REGENERATE_CHARACTER_IMAGE` | `character_id`, `project_id` | Clear existing + regenerate ref image (never skipped) |
| `EDIT_CHARACTER_IMAGE` | `character_id`, `project_id` | Edit ref image with base image + prompt (never skipped) |
| `GENERATE_IMAGE` | `scene_id`, `project_id`, `video_id`, `orientation` | Gen scene image with ref imageInputs (skips if already COMPLETED) |
| `REGENERATE_IMAGE` | `scene_id`, `project_id`, `video_id`, `orientation` | Force-regenerate scene image (never skipped, cascades video+upscale) |
| `EDIT_IMAGE` | `scene_id`, `project_id`, `video_id`, `orientation` | Edit scene image with base image + character refs in imageInputs |
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
  statusline.sh        — Claude Code statusline script
output/                — Project video output (structured per-project)
  _shared/             — Shared assets (TTS templates, music)
    tts_templates/     — Voice templates for narration
    music/             — Generated music tracks
  {project_slug}/      — Per-project output (slugified name)
    meta.json          — Project metadata (id, name, slug, orientation)
    scenes/            — Raw scene videos from API
    4k/                — 4K raw bytes from API
    tts/               — TTS narration WAVs
    narrated/          — Scenes with TTS mixed in
    trimmed/           — Duration-trimmed scenes
    norm/              — Normalized (codec/res/fps)
    thumbnails/        — Generated thumbnail PNGs
    subclips/          — YouTube-ready branded clips
    review/            — Video review contact sheets
    {slug}_final.mp4   — Final concatenated video
youtube/
  auth.py              — OAuth2 multi-channel auth (run: python3 youtube/auth.py <channel>)
  upload.py            — Upload with scheduling + channel rule validation
  channels/            — Per-channel config (local-only, gitignored)
    <channel_name>/
      client_secrets.json   — OAuth2 credentials (required, local-only)
      token.json            — Auth token (auto-created on first auth, auto-refreshes)
      channel_info.json     — Channel stats from YouTube API (auto-created)
      channel_rules.json    — Upload rules: max/day, optimal times, SEO defaults
      <channel>_icon.png    — Brand logo for /gla:brand-logo watermark overlay
      upload_history.json   — Upload log (auto-created by /gla:youtube-upload)
skills/                — AI agent skill definitions (invoked as /gla:<name>)
```

---

## Output Directory Convention

Every project output goes to `output/{slug}/` where slug is the project name cleaned of unicode, diacritics, and special characters.

**Get project output dir (auto-creates with meta.json):**
```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir
# Returns: {"slug": "chien_dich_giai_cuu_f_15e", "path": "output/chien_dich_giai_cuu_f_15e", "meta": {...}}
```

**Slugify rules:** strip diacritics → lowercase → non-alphanum to `_` → collapse `__` → trim edges.
- "Chiến dịch giải cứu F-15E" → `chien_dich_giai_cuu_f_15e`
- "A Day in My Life (Realistic)" → `a_day_in_my_life_realistic`

**Shared assets** (not project-scoped): `output/_shared/tts_templates/`, `output/_shared/music/`

**meta.json** is auto-created in each project dir on first access:
```json
{
  "project_id": "uuid",
  "project_name": "Original Name With Unicode",
  "slug": "clean_slug",
  "video_id": "uuid",
  "orientation": "VERTICAL",
  "material": "realistic",
  "scene_count": 40,
  "created_at": "ISO8601"
}
```

---

## YouTube Channel Management

### Auth Flow

1. Place `client_secrets.json` in `youtube/channels/<channel_name>/`
2. Run: `python3 youtube/auth.py <channel_name>` (macOS Apple Silicon: `arch -arm64 python3 youtube/auth.py <channel_name>`)
3. Browser opens for Google OAuth consent (scopes: youtube.readonly + youtube.upload)
4. Token saved to `token.json` — auto-refreshes on expiry

### Channel Rules (`channel_rules.json`)

Each channel has a rules file controlling upload scheduling and SEO defaults:

| Key | Example | Purpose |
|-----|---------|---------|
| `shorts.max_per_day` | `3` | Max Shorts uploads per day |
| `shorts.optimal_times` | `["07:00","12:00","17:00"]` | Best posting times (channel timezone) |
| `long_form.max_per_day` | `1` | Max long video uploads per day |
| `long_form.optimal_times` | `["19:00"]` | Prime time for long-form |
| `scheduling.min_gap_hours` | `4` | Minimum hours between any uploads |
| `scheduling.avoid_hours` | `[0,1,2,3,4,5]` | Hours to never post (dead hours) |
| `seo.niche` | `"geopolitics-military-documentary"` | Content niche for keyword targeting |
| `seo.default_tags` | `["phim tài liệu",...]` | Tags included in every upload |
| `seo.always_include_hashtags` | `["#PhimTàiLiệu","#QuânSự"]` | Hashtags always prepended to description |
| `seo.hashtag_language` | `"mixed_vi_en"` | Hashtag language strategy |
| `seo.title_max_chars` | `65` | Max title length |
| `seo.default_category` | `"25"` | YouTube category ID (25=News, 22=People, 27=Education) |

### Skill Chain

```
/gla:youtube-seo   → generates title, description, hashtags, tags (reads channel_rules.json for niche/tags)
/gla:brand-logo    → applies channel icon watermark (reads <channel>_icon.png)
/gla:youtube-upload → validates rules + uploads (reads channel_rules.json for scheduling)
```

Typical workflow: `youtube-seo` → `brand-logo` → `youtube-upload`

### Upload Validation

`youtube/upload.py` validates every upload against channel rules before submitting:
1. **Max per day** — counts uploads on target date from `upload_history.json`
2. **Min gap** — time since last upload of any type
3. **Avoid hours** — schedule hour in channel timezone
4. Auto-detects Short (<61s + vertical 9:16) vs Long-form
