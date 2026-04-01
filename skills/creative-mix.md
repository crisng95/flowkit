Creative video mixing — combine techniques for cinematic results.

Usage: `/creative-mix <project_id> <video_id>`

This skill analyzes existing scenes and suggests creative enhancements using all available techniques.

## Techniques Available

### T1: Scene Chaining (i2v_fl)
Smooth transitions between scenes using start+end frames.
- **When:** Sequential scenes that should flow into each other
- **How:** Set `vertical_end_scene_media_id` on CONTINUATION scenes

### T2: Multi-angle INSERT
Break one moment into multiple camera angles.
- **When:** Dramatic or important story moments deserve more screen time
- **How:** Create INSERT scenes with different prompts (close-up, reaction, detail)

### T3: Reference Video (r2v)
Generate video purely from character reference images — no start frame.
- **When:** Opening/intro shots, character reveal, abstract/dream sequences
- **How:** `type: "GENERATE_VIDEO_REFS"` with character media_ids
- The AI composes a video from the reference images directly

### T4: Parallel Orientation
Generate same scene in both VERTICAL + HORIZONTAL for multi-platform.
- **When:** Publishing to both YouTube Shorts (vertical) and YouTube (horizontal)
- **How:** Create two requests per scene, one VERTICAL one HORIZONTAL

### T5: Scene Branching
One parent scene → multiple CONTINUATION children = alternate story paths.
- **When:** "What if" variations, A/B testing different story directions
- **How:** Multiple scenes with same `parent_scene_id` but different prompts

## Step 1: Analyze current video

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

Review scenes and suggest enhancements:

## Step 2: Suggest a creative plan

Based on the story, suggest specific enhancements. Example:

```
Scene 1 (Morning Setup) — ROOT
  → OK as-is (establishing shot)

Scene 2 (First Customer) — CONTINUATION
  → CHAIN from Scene 1 (smooth transition sunrise → morning)
  → INSERT 2a: "Close-up reaction of Mai's eyes widening seeing the fish" (reaction shot)

Scene 3 (Juggling) — CONTINUATION  
  → CHAIN from Scene 2
  → INSERT 3a: "Low angle looking up at fish spinning in the air, crowd blurred behind" (dynamic angle)
  → INSERT 3b: "Crowd POV watching Pippip perform, hands clapping" (audience perspective)

Scene 4 (Temptation) — CONTINUATION
  → CHAIN from Scene 3
  → This is the dramatic peak — add r2v intro: dream sequence of Golden Fish glowing

Scene 5 (Resolution) — CONTINUATION
  → CHAIN from Scene 4
  → INSERT 5a: "Empty market stalls at sunset, peaceful wide shot" (outro establishing shot)
```

## Step 3: Execute with user approval

Present the plan and ask which enhancements to apply. Then execute:

1. Create any new INSERT scenes (`POST /api/scenes`)
2. Generate images for new scenes (`/gen-images`)
3. Set up chain end_scene_media_ids
4. Generate all videos with chaining (`/gen-chain-videos`)
5. For r2v scenes: `POST /api/requests {type: "GENERATE_VIDEO_REFS"}`

## Step 4: Output

Print the final scene timeline:
```
00:00 Scene 1    [ROOT]         Morning Setup (i2v)
00:08 Scene 2    [CHAIN←1]     First Customer (i2v_fl, smooth from scene 1)
00:16 Scene 2a   [INSERT←2]    Mai's reaction close-up (i2v)
00:24 Scene 3    [CHAIN←2a]    Juggling (i2v_fl)
00:32 Scene 3a   [INSERT←3]    Low angle fish arc (i2v)
00:40 Scene 4    [CHAIN←3a]    Temptation (i2v_fl)
00:48 Scene 4r   [R2V]         Dream sequence (r2v, no start frame)
00:56 Scene 5    [CHAIN←4]     Resolution (i2v_fl)
01:04 Scene 5a   [INSERT←5]    Sunset outro (i2v)
```

Run `/concat <VID>` to merge the final video.
