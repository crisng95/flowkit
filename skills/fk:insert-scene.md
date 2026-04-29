Insert new scene(s) into an existing video chain — for multi-angle shots, cutaways, or close-ups.

Usage: `/insert-scene <video_id> <after_scene_order> <prompt>`

Example: `/insert-scene abc123 2 "Close-up of Hero's hand gripping Magic Sword, determination in eyes"`

This inserts a new scene AFTER the specified scene order, shifts subsequent scenes, and maintains the chain.

## Concept: Multi-angle from single moment

One story moment can become multiple scenes with different camera angles:
```
Scene 2: "Hero reaches for Magic Sword" (wide shot)
  └─ INSERT 2a: "Close-up of Hero's hand gripping Magic Sword hilt" (detail)
  └─ INSERT 2b: "Hero's face reflecting golden glow from Magic Sword" (reaction)
Scene 3: "Hero pulls Magic Sword from the wall" (action)
```

All INSERT scenes use the SAME `character_names` as the parent for visual consistency.

## Step 1: Get current scenes

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Find the scene at the specified `display_order`. This becomes the parent.

## Step 2: Create INSERT scene

Ask the user for:
- **Prompt**: What camera angle / action / detail to show (action only, no character appearance)
- **character_names**: Default to same as parent scene (user can override)

```bash
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<VID>",
    "display_order": <parent_order + 1>,
    "prompt": "<user prompt>",
    "character_names": ["<same as parent>"],
    "chain_type": "INSERT",
    "parent_scene_id": "<parent_scene_id>",
    "source": "user"
  }'
```

## Step 3: Shift subsequent scenes

All scenes with `display_order > parent_order` need their order incremented by 1:

```bash
# For each scene after the insert point:
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{"display_order": <current_order + 1>}'
```

Process in REVERSE order (highest first) to avoid collisions.

## Step 4: Output

Print updated scene order:
| # | Type | Chain | Prompt |
|---|------|-------|--------|

Mark the new INSERT scene. Tell user:
- "New scene inserted. Run /fk:gen-images to generate its image, then /fk:gen-chain-videos to regenerate videos with updated chain."

## Multi-angle batch

If the user wants multiple angles from one moment, ask for all prompts at once and create multiple INSERT scenes sequentially:

```
Original scene 2 (order=2) → parent
INSERT 2a (order=3) → first angle
INSERT 2b (order=4) → second angle  
Original scene 3 (order=5) → shifted from 3
```

Each INSERT scene has `parent_scene_id` = original scene 2, `chain_type: "INSERT"`.

**IMPORTANT: Create INSERT scenes one at a time.** The API auto-shifts subsequent scene orders on each INSERT. If you batch multiple INSERTs, each one must use the CURRENT state (after prior shifts), not pre-calculated orders. Create first INSERT → verify order → create next INSERT.
