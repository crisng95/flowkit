Generate videos for all scenes in a video.

Usage: `/gen-videos <project_id> <video_id>`

## Step 1: Pre-check — all scene images must be ready

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

**ABORT** if any scene is missing `vertical_image_media_id` (UUID) or `vertical_image_status` != `"COMPLETED"`. Tell user to run `/gen-images` first.

## Step 2: Filter scenes needing video

Only scenes where `vertical_video_status` != `"COMPLETED"` or `vertical_video_media_id` is missing.

## Step 3: Create requests ONE AT A TIME

Video generation is async and takes 2-5 minutes per scene. Process sequentially.

```bash
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{"type": "GENERATE_VIDEO", "scene_id": "<SID>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "VERTICAL"}'
```

Poll every 15s until `COMPLETED` or `FAILED`. Max wait: 600s (10 min) per scene.

## Step 4: Verify

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

## Step 5: Output

Print results table:
| Scene | Order | video_status | video_media_id | video_url |
|-------|-------|-------------|---------------|-----------|

Print: "All videos ready. Run /concat <VID> to download and merge."
