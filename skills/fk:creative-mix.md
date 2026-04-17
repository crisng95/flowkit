Creative video mixing — combine techniques for cinematic results.

Usage: `/creative-mix <project_id> <video_id>`

This skill analyzes existing scenes and suggests creative enhancements using all available techniques.

## Techniques Available

### T1: Scene Chaining (i2v_fl)
Smooth transitions between scenes using start+end frames.
- **When:** Sequential scenes that should flow into each other
- **How:** Set `${ori}_end_scene_media_id` on CONTINUATION scenes

### T2: Multi-angle Breakdown (the killer technique)
Explode ONE moment into multiple camera angles — like a real film director cutting between shots. Use `EDIT_IMAGE` on the parent scene's image to create new perspectives while keeping character/environment consistency via refs.

- **When:** Dramatic peaks, action moments, emotional beats — any scene worth more than 8s of screen time
- **How:**
  1. Start with the parent scene image (e.g. wide establishing shot)
  2. `EDIT_IMAGE` the parent image with camera-angle prompts + character refs:
     - Close-up of character's face/hands/eyes
     - Over-the-shoulder of another character watching
     - Low angle / worm's eye for power/drama
     - Bird's eye / top-down for scale
     - Reaction shot from a different character's perspective
     - Detail shot (object, texture, environment element)
  3. Each edit produces a new angle that's visually consistent with the original
  4. Create INSERT scenes for each angle, chain videos between them

**Example: "Hero grabs the sword" (Scene 3, wide shot)**
```
Scene 3:  Wide shot, hero walks to sword               (ROOT, i2v)
  ├── 3a: EDIT → extreme close-up, hand grips hilt     (INSERT, start:3a end:3 → smooth zoom-in)
  ├── 3b: EDIT → OTS villain watching from shadows      (INSERT, hard cut → tension)
  ├── 3c: EDIT → low angle, sword pulled free, light    (INSERT, start:3c end:3a → smooth transition)
  └── 3d: EDIT → bird's eye, light radiates across room (INSERT, start:3d end:3c → dramatic reveal)
```
Result: One 8s moment becomes **40s of rich multi-angle cinema**.

**CRITICAL: Close-up framing rule for i2v**

The starting image is the AI's ONLY visual reference for the video. If the image is an extreme macro (just an eye, just a hand), the AI has NO information about the character's face, outfit, or environment. When the video prompt says "zoom out", the AI invents a DIFFERENT character.

Two safe patterns for close-up INSERTs:

- **Pattern A (Stay in frame):** Keep video movement within the same framing. Macro stays macro — subtle shifts, light changes, no zoom out.
  ```
  Start: eye macro → Video: eye flutter, light shifts, pupil dilates (NO pull-back)
  ```
- **Pattern B (Chain with anchor):** Use `end_image` from the parent scene (medium/wide shot) to anchor the character. The AI transitions from close-up TO the known character.
  ```
  Start: eye macro (INSERT image)
  End: parent scene medium shot (anchor)
  → i2v_fl smoothly reveals the correct character
  ```

Pattern B is preferred for dramatic close-ups — you get the cinematic zoom AND character consistency.

**Camera angle ideas for edits** (see `/fk:camera-guide`):
- `"Extreme close-up of [character]'s eyes, shallow DOF"` — emotion (use Pattern A or B!)
- `"Over-the-shoulder shot from [other character], watching"` — relationship
- `"Low angle looking up at [subject], dramatic lighting"` — power
- `"Bird's eye top-down view of the scene"` — scale/context
- `"Dutch angle, tilted frame, tension"` — unease
- `"POV shot from [character]'s perspective"` — immersion
- `"Macro detail shot of [object]"` — texture/significance (use Pattern A or B!)

### T3: Reference Video (r2v)
Generate video purely from character reference images — no start frame.
- **When:** Opening/intro shots, character reveal, abstract/dream sequences
- **How:** `type: "GENERATE_VIDEO_REFS"` with character media_ids
- The AI composes a video from the reference images directly

### T4: Parallel Orientation
Generate same scene in both VERTICAL + HORIZONTAL for multi-platform.
- **When:** Publishing to both YouTube Shorts (vertical) and YouTube (horizontal)
- **How:** Create two requests per scene, one VERTICAL one HORIZONTAL

### T5: Scene Branching (explore + pick)
Generate multiple visual variations of the same story moment, review, pick the best.

- **When:** Key scenes where quality matters most — hero moments, emotional peaks, final shots
- **How:**
  1. Create 2-3 CONTINUATION children of the same parent, each with a slightly different prompt or camera angle
  2. Generate images for all branches
  3. Review — pick the winner, delete the rest
  4. Only generate video for the winner (saves credits)
- **Combine with T2:** Branch to explore different angle breakdowns, then commit to the best cinematic sequence
- **Combine with T6:** Use REGENERATE_IMAGE on the same scene to get different seeds, or EDIT_IMAGE to tweak the best candidate

### T6: Iterative Image Refinement
Polish scene images before committing to video generation.
- **When:** Image is close but needs adjustment (lighting, composition, expression, framing)
- **How:**
  - `EDIT_IMAGE` — keeps composition, tweaks details. Automatically sends character refs for consistency.
  - `REGENERATE_IMAGE` — fresh take from the same prompt (different seed, bypasses skip check)
  - `EDIT_CHARACTER_IMAGE` — refine a character reference before using it in scenes
  - `REGENERATE_CHARACTER_IMAGE` — completely new reference image (clears existing, regenerates from scratch)
- **Workflow:** Generate → Review → Edit/Regen → Review → Video
- **Tip:** Edit preserves the base image structure. Regen gives a completely new interpretation of the same prompt.

## Step 0: Cleanup previous creative-mix scenes

Before running creative-mix, remove any previous system-generated scenes:

```bash
curl -X DELETE "http://127.0.0.1:8100/api/scenes?video_id=<VID>&source=system"
```

This deletes all `source=system` INSERT scenes and re-compacts display_order. Safe to re-run.

## Step 1: Analyze current video

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

Review scenes and suggest enhancements:

## Step 2: Suggest a creative plan

Based on the story, suggest specific enhancements. Example:

```
Scene 1 (Morning Setup) — ROOT, wide establishing shot
  → OK as-is (sets the stage)

Scene 2 (First Customer) — ROOT, hard cut (new moment)
  → No chain — location change feels natural as hard cut
  → EDIT 2a: close-up of customer's face reacting to the fish display (T2 angle breakdown)

Scene 3 (Juggling) — CONTINUATION from Scene 2
  → CHAIN from Scene 2 (smooth transition, same location)
  → This is the showpiece — T2 multi-angle breakdown:
    → EDIT 3a: "Low angle looking up at fish spinning in the air, crowd blurred, 85mm lens" 
    → EDIT 3b: "Over-the-shoulder from crowd member watching Pippip, shallow DOF"
    → EDIT 3c: "Extreme close-up Pippip's hands catching fish, slow motion, macro detail"
  → Chain: Scene3→3a (smooth zoom-in), 3a→3b (hard cut to crowd), 3b→3c (hard cut to hands)
  → One 8s moment becomes 32s of rich multi-angle cinema

Scene 4 (Temptation) — ROOT, hard cut (mood change)
  → Dream sequence intro via r2v (T3): golden fish reference images only, no start frame
  → Then Scene 4 image as main scene

Scene 5 (Resolution) — ROOT (peaceful ending, different energy)
  → EDIT 5a: "Wide pull-back, empty market stalls at sunset, volumetric light" (outro)
  → T5 branch: generate 2 versions of Scene 5, pick the most cinematic
```

## Step 3: Execute with user approval

Present the plan and ask which enhancements to apply. Then execute:

1. Create any new INSERT scenes (`POST /api/scenes` with `"source": "system"`)
2. Generate images for new scenes (`/fk:gen-images`)
2b. Review generated images — refine with EDIT_IMAGE or REGENERATE_IMAGE as needed
3. Set up chain end_scene_media_ids
4. Generate all videos with chaining (`/fk:gen-chain-videos`)
5. For r2v scenes: `POST /api/requests {type: "GENERATE_VIDEO_REFS"}`

## Step 4: Output

Print the final scene timeline:
```
00:00 Scene 1    [ROOT]         Morning Setup, wide establishing (i2v)
00:08 Scene 2    [ROOT]         First Customer arrives (i2v, hard cut)
00:16 Scene 2a   [EDIT←2]      Close-up customer reaction (i2v)
00:24 Scene 3    [CHAIN←2]     Juggling begins, medium tracking (i2v_fl)
00:32 Scene 3a   [EDIT←3]      Low angle fish in air, 85mm (i2v, start:3a end:3 smooth zoom)
00:40 Scene 3b   [EDIT←3]      OTS crowd watching, shallow DOF (i2v, hard cut)
00:48 Scene 3c   [EDIT←3]      Extreme close-up hands catch fish (i2v, hard cut)
00:56 Scene 4r   [R2V]         Dream sequence, golden fish (r2v, no start frame)
01:04 Scene 4    [ROOT]         Temptation scene (i2v, hard cut from dream)
01:12 Scene 5    [ROOT]         Resolution, warm sunset (i2v)
01:20 Scene 5a   [EDIT←5]      Wide pull-back, empty market, volumetric light (i2v)
```

Run `/fk:concat <VID>` to merge the final video.
