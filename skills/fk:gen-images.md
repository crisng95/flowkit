Generate scene images for all scenes in a video.

Usage: `/fk:gen-images <project_id> <video_id>`

If not provided, ask or list projects/videos.

## Step 0: Detect orientation

```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
ORI=$(cat ${OUTDIR}/meta.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('orientation','HORIZONTAL'))")
ori=$(echo "$ORI" | tr '[:upper:]' '[:lower:]')
```
**NEVER hardcode VERTICAL or HORIZONTAL.** Use `${ORI}` for API params, `${ori}_*` for DB field lookups.

## Step 1: Pre-check — all references must be ready

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

**ABORT** if any entity is missing `media_id`. Tell user to run `/fk:gen-refs <PID>` first.

## Step 2: Get scenes and classify by chain_type

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Filter to scenes where `${ori}_image_status` != `"COMPLETED"` or `${ori}_image_media_id` is missing/not UUID.

**Classify into waves by dependency depth:**

| Wave | Condition | Request type |
|------|-----------|-------------|
| 1 | `chain_type == "ROOT"` or no `parent_scene_id` | `GENERATE_IMAGE` |
| 2 | `chain_type == "CONTINUATION"` and parent is in Wave 1 | `EDIT_IMAGE` |
| 3 | `chain_type == "CONTINUATION"` and parent is in Wave 2 | `EDIT_IMAGE` |
| N | Parent is in Wave N-1 | `EDIT_IMAGE` |

Build the wave map by walking the `parent_scene_id` chain. Scenes in the same wave are independent and can run in parallel.

**Why EDIT_IMAGE for CONTINUATION?** Instead of generating a brand-new image (low consistency), we edit from the parent scene's completed image + the current scene's ref images. This produces visually continuous frames — same environment, lighting, and character positioning evolve naturally rather than being regenerated from scratch.

## Step 3: Submit wave by wave

### Wave 1 — ROOT scenes (GENERATE_IMAGE)

```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "GENERATE_IMAGE", "scene_id": "<ROOT_SID1>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"},
      {"type": "GENERATE_IMAGE", "scene_id": "<ROOT_SID2>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"}
    ]
  }'
```

Poll until Wave 1 completes:

```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_IMAGE"
# Wait for: "done": true
```

### Wave 2+ — CONTINUATION scenes (EDIT_IMAGE)

After the parent wave completes, submit CONTINUATION scenes whose parents now have completed images:

```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "EDIT_IMAGE", "scene_id": "<CONT_SID1>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"},
      {"type": "EDIT_IMAGE", "scene_id": "<CONT_SID2>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"}
    ]
  }'
```

The worker auto-resolves `source_media_id` from the parent scene's `${ori}_image_media_id` — no need to pass it manually. Character refs from `character_names` are also auto-resolved and sent as `imageInputs` after the base image: `[parent_image, char_A, char_B, ...]`.

Poll until wave completes, then submit next wave. Repeat until all waves done.

```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=EDIT_IMAGE"
# Wait for: "done": true
```

**Tip:** If a project has no CONTINUATION scenes (all ROOT), this collapses to a single wave — same as the old behavior.

## Step 4: Verify media_ids are UUID

After all waves complete, check each scene:
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

If any `${ori}_image_media_id` starts with `CAMS` or is not UUID format, fix it by extracting UUID from `${ori}_image_url`:
```bash
# Extract UUID from URL path: /image/{UUID}?...
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{"${ori}_image_media_id": "<extracted_uuid>"}'
```

## Step 5: Output

Print results table:
| Scene | Order | chain_type | request_type | image_status | media_id (UUID) |
|-------|-------|-----------|-------------|-------------|----------------|

Print: "All scene images ready. Run /fk:gen-videos <PID> <VID> to generate videos."

## Important rules

- **GENERATE vs REGENERATE:** `GENERATE_IMAGE` skips scenes already `COMPLETED`. Use `REGENERATE_IMAGE` to force a fresh generation.
- **Cascade on regen:** `REGENERATE_IMAGE` auto-clears downstream video + upscale status for that scene. For CONTINUATION scenes, regenerating a parent also invalidates all children — re-run this skill to re-edit downstream scenes.
- **EDIT_IMAGE for CONTINUATION:** The worker auto-resolves `source_media_id` from `parent_scene_id` and `character_names` → sends as `imageInputs` after the base image `[base_image, char_A, char_B, ...]` for character consistency. Same for `EDIT_CHARACTER_IMAGE`.
- **Wave ordering is critical:** Never submit EDIT_IMAGE for a CONTINUATION scene before its parent's image is COMPLETED. The wave system enforces this automatically.
- **Mixed chains:** A video can have multiple independent chains (e.g., interview scenes as ROOT, cinematic scenes as CONTINUATION chains). Each chain resolves independently within the wave system.
