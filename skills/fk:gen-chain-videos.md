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

ABORT if any scene is missing `${ori}_image_media_id` (UUID).

## Step 2: Set up end_scene_media_ids for chaining

For each CONTINUATION scene, set its `${ori}_end_scene_media_id` to its parent scene's `${ori}_image_media_id`:

```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{"${ori}_end_scene_media_id": "<parent_scene_image_media_id>"}'
```

Logic:
1. Sort scenes by `display_order`
2. For each scene with `chain_type: "CONTINUATION"` and `parent_scene_id`:
   - Look up parent scene
   - Set `${ori}_end_scene_media_id` = parent's `${ori}_image_media_id`
3. ROOT scenes and the last scene: no endImage (leave `${ori}_end_scene_media_id` null)

## Step 3: Submit ALL video requests at once

The server handles throttling automatically (max 5 concurrent, 10s cooldown). The worker reads `${ori}_end_scene_media_id` from each scene (set in Step 2) and passes it as `endImage` to the API. This triggers `start_end_frame_2_video` (i2v_fl) instead of plain `frame_2_video` (i2v).

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

Build the `requests` array from ALL scenes in display_order. Do NOT manually batch or loop.

Poll aggregate status every 30s until done:

```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
# Wait for: "done": true
# If "all_succeeded": false → some failed, check individual failures
```

## Known Limitation: Concat Gap

**Problem:** When concatenating chained videos, the endImage frames of scene N overlap with the startImage frames of scene N+1 — both are the same image. This produces **10-16 static/duplicate frames (~0.4-0.7s)** at each cut point where nothing moves.

```
Scene 1 video: [action...] [endImage = scene2 still] ← 10-16 frames
Scene 2 video: [startImage = scene2 still] [action...] ← 10-16 frames
Concat result:  ...action → [~0.8-1.4s static gap] → action...
```

**Mitigations:**
- **Trim overlap** — use `trim_start` / `trim_end` on scenes to cut the static frames before concat. Typically trim 0.4-0.7s from the end of scene N and/or the start of scene N+1.
- **Don't overuse chaining** — only chain scenes that truly need smooth visual continuity (same location, continuous action). For scene changes (new location, time jump), use ROOT without endImage — a hard cut is more natural.
- **Mix techniques** — alternate between chained (CONTINUATION) and unchained (ROOT) scenes. Hard cuts between different locations feel intentional; gaps between continuous action feel broken.

**When to chain vs not:**

| Situation | Recommendation |
|-----------|---------------|
| Same location, continuous action | CONTINUATION (chain) |
| Location change, time jump | ROOT (hard cut — no gap) |
| Dramatic moment, reaction shot | INSERT (hard cut — intentional) |
| Dream/flashback transition | ROOT or R2V (stylistic break) |

## Step 4: Output

Print table:
| Scene | Order | Chain | endImage from | video_status | Duration |
|-------|-------|-------|---------------|-------------|----------|

Print: "Chained videos ready. Run /fk:concat <VID> to merge."
Remind: "Check concat gaps — trim 0.4-0.7s overlap at chain boundaries if needed."
