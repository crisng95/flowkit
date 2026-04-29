Generate reference images for all entities in a project.

Usage: `/fk:gen-refs <project_id>`

If no project_id provided, use `GET /api/active-project` or list projects via `GET /api/projects`.

## Step 1: Check health

```bash
curl -s http://127.0.0.1:8100/health
```
Must have `extension_connected: true`. Abort if not.

## Step 2: Get entities

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

Filter to entities that do NOT yet have `media_id` (UUID format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`). Never use `CAMS...` strings — those are `mediaGenerationId`, not `media_id`. Skip entities already done.

**Orientation by entity type:** characters, creatures, visual_assets, generic_troops, factions → **portrait**. Locations → **landscape**. The worker handles this automatically based on `entity_type`.

**GENERATE vs REGENERATE:** `GENERATE_CHARACTER_IMAGE` skips if `media_id` already exists. Use `REGENERATE_CHARACTER_IMAGE` to force a fresh generation (clears existing image first).

## Step 3: Submit ALL requests at once

The server handles throttling automatically (max 5 concurrent, 10s cooldown). Submit everything in one batch call:

```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "GENERATE_CHARACTER_IMAGE", "character_id": "<CID1>", "project_id": "<PID>"},
      {"type": "GENERATE_CHARACTER_IMAGE", "character_id": "<CID2>", "project_id": "<PID>"}
    ]
  }'
```

Build the `requests` array from ALL entities missing `media_id` in Step 2. Do NOT manually batch or loop.

Poll aggregate status every 15s until done:

```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?project_id=<PID>&type=GENERATE_CHARACTER_IMAGE"
# Wait for: "done": true
# If "all_succeeded": false → some failed, check individual failures
```

## Step 4: Verify

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

Print results table:
| Entity | Type | media_id | Status |
|--------|------|----------|--------|

All entities must have `media_id` in UUID format. If any failed, report and suggest retry.

## Step 5: Troubleshoot UNSAFE_GENERATION failures

If any entities failed with `PUBLIC_ERROR_UNSAFE_GENERATION`, this means the AI safety filter flagged the character's appearance (typically recognizable political/public figures). Fix with progressive de-identification:

### Round 1: Left-side profile

For each failed entity, rewrite `image_prompt` to show **left side three-quarter profile view** instead of front-facing. This reduces face recognition while keeping the character identifiable by silhouette, hair, clothing, and build.

```bash
# Update image_prompt to left-side profile
curl -s -X PATCH http://127.0.0.1:8100/api/characters/<CID> \
  -H "Content-Type: application/json" \
  -d '{"image_prompt": "<rewritten prompt with left side three-quarter profile view>"}'

# Regenerate with new prompt
curl -s -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{"type": "REGENERATE_CHARACTER_IMAGE", "character_id": "<CID>", "project_id": "<PID>"}'
```

**Prompt rewrite rules for left-side:**
- Replace "front-facing" / "facing camera" with "seen from the left side three-quarter profile"
- Add "Left side three-quarter view, showing silhouette from head to toe"
- Keep ALL clothing, build, hair, and posture descriptions intact
- Remove any age + ethnicity + political role combinations that are too specific

### Round 2: Back view (if left-side still fails)

If left-side profile still triggers UNSAFE_GENERATION, escalate to **full back view**:

```bash
# Update image_prompt to back view
curl -s -X PATCH http://127.0.0.1:8100/api/characters/<CID> \
  -H "Content-Type: application/json" \
  -d '{"image_prompt": "<rewritten prompt with back view>"}'

# Regenerate
curl -s -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{"type": "REGENERATE_CHARACTER_IMAGE", "character_id": "<CID>", "project_id": "<PID>"}'
```

**Prompt rewrite rules for back view:**
- Replace view direction with "seen from behind"
- Add "Back view, showing full silhouette from head to toe"
- Keep clothing, build, hair descriptions
- Remove age/ethnicity if still failing — use only clothing + build + hair

### Round 3: Generic silhouette (last resort)

If back view still fails, strip all identifying details:

```bash
curl -s -X PATCH http://127.0.0.1:8100/api/characters/<CID> \
  -H "Content-Type: application/json" \
  -d '{"image_prompt": "Single reference image of an elderly man seen from behind, [hair color] hair, [build] build, [clothing only]. Back view showing full silhouette. Photorealistic studio lighting, neutral grey background."}'
```

### Scope: only fix what's broken

Only apply troubleshooting to entities that actually failed with UNSAFE_GENERATION. Do NOT modify entities that generated successfully — their existing ref images are fine.

### Also handle PUBLIC_ERROR_MINOR_INPUT_IMAGE

If error is `PUBLIC_ERROR_MINOR_INPUT_IMAGE`, the image_prompt describes or implies minors (children). Fix by:
- Remove any mention of children, kids, babies, young people
- Remove "carrying child", "with children", "crying families"
- Replace with adult-only descriptions

Poll and verify after each round. Print final results table showing all entities with media_id status.

Print: "All references ready. Run /fk:gen-images <PID> <VID> to generate scene images."
