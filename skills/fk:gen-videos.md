Generate videos for all scenes in a video.

Usage: `/fk:gen-videos <project_id> <video_id>`

## Step 0: Detect orientation

```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
ORI=$(cat ${OUTDIR}/meta.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('orientation','HORIZONTAL'))")
ori=$(echo "$ORI" | tr '[:upper:]' '[:lower:]')
```
**NEVER hardcode VERTICAL or HORIZONTAL.** Use `${ORI}` for API params, `${ori}_*` for DB field lookups.

## Step 1: Pre-check — all scene images must be ready

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

**ABORT** if any scene is missing `${ori}_image_media_id` (UUID) or `${ori}_image_status` != `"COMPLETED"`. Tell user to run `/fk:gen-images` first.

## Step 2: Filter scenes needing video

Only scenes where `${ori}_video_status` != `"COMPLETED"` or `${ori}_video_media_id` is missing.

## Step 3: Submit ALL requests at once

The server handles throttling automatically (max 5 concurrent, 10s cooldown). Submit everything in one batch call. Video generation takes 2-5 minutes per scene.

```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "GENERATE_VIDEO", "scene_id": "<SID1>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"},
      {"type": "GENERATE_VIDEO", "scene_id": "<SID2>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"}
    ]
  }'
```

Build the `requests` array from ALL scenes filtered in Step 2. Do NOT manually batch or loop.

Poll aggregate status every 30s until done (videos take longer):

```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
# Wait for: "done": true
# If "all_succeeded": false → some failed, check individual failures
```

## Step 4: Verify

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

## Step 5: Output

Print results table:
| Scene | Order | video_status | video_media_id | video_url |
|-------|-------|-------------|---------------|-----------|

Print: "All videos ready. Run /fk:concat <VID> to download and merge."

## Important rules

- **GENERATE vs REGENERATE:** `GENERATE_VIDEO` skips scenes already `COMPLETED`. To force-regenerate, reset `${ori}_video_status` to `PENDING` first, then submit.
- **Cascade on regen:** Regenerating a video auto-clears the upscale status for that scene.
- **Chain video prompt rule (CRITICAL):** Chain scenes with children use `transition_prompt` for video generation, NOT `video_prompt`. This is because the video transitions from the current scene's image to the child scene's image. When fixing chain scene videos, always update `transition_prompt`. `video_prompt` is only used for ROOT scenes or leaf scenes (no children).
- **Chain cascade (CRITICAL):** When regenerating a scene that has CONTINUATION children, you MUST also regenerate images + videos for all descendants in the chain. The child's image was EDIT_IMAGE'd from the parent's old image — if the parent's video changes, the child's start frame won't match the parent's end frame.
  - Walk the full chain to the leaf: `parent_scene_id` links form the chain
  - Regen child images **sequentially** (each child depends on parent completing first)
  - **Update `end_scene_media_id`**: After each child image regen completes, PATCH parent's `${ori}_end_scene_media_id` = child's new `${ori}_image_media_id`. This is CRITICAL — without it, video gen uses stale end frame and the video won't transition to the child's image.
  - After all images complete + end_scene_media_ids updated, regen the **parent video too** (so its end frame matches child's new start image)
  - Then batch regen videos for all children (parent + children can be parallel)
  - **Always proactively propose this cascade to the user** — don't wait for them to notice the mismatch
