Generate videos with automatic scene chaining (start+end frame transitions).

Usage: `/gen-chain-videos <project_id> <video_id>`

This creates smooth transitions between CONTINUATION scenes by using the **next scene's image as the endImage** of the current scene's video.

## How chaining works

```
Scene 1 (ROOT):         startImage = scene1.image                        → video
Scene 2 (CONTINUATION): startImage = scene2.image, endImage = scene1.image → video transitions FROM scene1 TO scene2
Scene 3 (CONTINUATION): startImage = scene3.image, endImage = scene2.image → video transitions FROM scene2 TO scene3
Last scene:             startImage = lastScene.image                      → video (no endImage)
```

The `endImage` is the PARENT scene's image — the video smoothly transitions from the parent's visual world into the current scene.

## Step 1: Pre-check

```bash
# All scene images must be ready with UUID media_ids
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

ABORT if any scene is missing `vertical_image_media_id` (UUID).

## Step 2: Set up end_scene_media_ids for chaining

For each CONTINUATION scene, set its `vertical_end_scene_media_id` to its parent scene's `vertical_image_media_id`:

```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{"vertical_end_scene_media_id": "<parent_scene_image_media_id>"}'
```

Logic:
1. Sort scenes by `display_order`
2. For each scene with `chain_type: "CONTINUATION"` and `parent_scene_id`:
   - Look up parent scene
   - Set `vertical_end_scene_media_id` = parent's `vertical_image_media_id`
3. ROOT scenes and the last scene: no endImage (leave `vertical_end_scene_media_id` null)

## Step 3: Generate videos ONE AT A TIME, in order

Process in display_order (scene 1 first, then 2, etc.):

```bash
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{"type": "GENERATE_VIDEO", "scene_id": "<SID>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "VERTICAL"}'
```

The worker automatically reads `vertical_end_scene_media_id` and passes it as `endImage` to the API. This triggers `start_end_frame_2_video` (i2v_fl) instead of plain `frame_2_video` (i2v).

Poll every 15s. Max wait: 600s per scene.

## Step 4: Output

Print table:
| Scene | Order | Chain | endImage from | video_status | Duration |
|-------|-------|-------|---------------|-------------|----------|

Print: "Chained videos ready. Run /concat <VID> to merge."
