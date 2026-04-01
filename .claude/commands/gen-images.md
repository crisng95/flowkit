Generate scene images for all scenes in a video.

Usage: `/gen-images <project_id> <video_id>`

If not provided, ask or list projects/videos.

## Step 1: Pre-check — all references must be ready

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

**ABORT** if any entity is missing `media_id`. Tell user to run `/gen-refs <PID>` first.

## Step 2: Get scenes

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Filter to scenes where `vertical_image_status` != `"COMPLETED"` or `vertical_image_media_id` is missing/not UUID.

## Step 3: Create requests ONE AT A TIME

For each scene needing an image:

```bash
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{"type": "GENERATE_IMAGES", "scene_id": "<SID>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "VERTICAL"}'
```

Poll every 10s until `COMPLETED` or `FAILED`. Max wait: 120s per scene.

## Step 4: Verify media_ids are UUID

After all complete, check each scene:
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

If any `vertical_image_media_id` starts with `CAMS` or is not UUID format, fix it by extracting UUID from `vertical_image_url`:
```bash
# Extract UUID from URL path: /image/{UUID}?...
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{"vertical_image_media_id": "<extracted_uuid>"}'
```

## Step 5: Output

Print results table:
| Scene | Order | image_status | media_id (UUID) |
|-------|-------|-------------|----------------|

Print: "All scene images ready. Run /gen-videos <PID> <VID> to generate videos."
