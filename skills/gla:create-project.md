Create a new Google Flow video project. Ask the user for:

1. **Project name** and **story** (brief plot summary)
2. **Material** — the visual style for all images. Choose one of the 6 built-in styles or a custom material. Run `GET /api/materials` to show available options. Built-ins: `realistic`, `3d_pixar`, `anime`, `stop_motion`, `minecraft`, `oil_painting`. **Required.**
3. **Characters** — name + visual description of their **base default look in ONE outfit only**. No scene-specific variants (e.g. "glamorous in studio, sporty in gym"). The reference image must be a single clean image, not a multi-panel grid. Different outfits per scene come from the scene prompts, not the character description.
4. **Locations** — name + visual description of key places
5. **Visual assets** — name + visual description of key props/objects
6. **Number of scenes** and **orientation** (VERTICAL or HORIZONTAL)

Then execute:

## Step 1: Create project with all entities

```bash
curl -X POST http://127.0.0.1:8100/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "...", "description": "...", "story": "...", "material": "3d_pixar", "characters": [
    {"name": "...", "entity_type": "character", "description": "..."},
    {"name": "...", "entity_type": "location", "description": "..."},
    {"name": "...", "entity_type": "visual_asset", "description": "..."}
  ]}'
```

Save the returned `project_id`.

## Step 2: Create video

```bash
curl -X POST http://127.0.0.1:8100/api/videos \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<PID>", "title": "...", "display_order": 0}'
```

Save the returned `video_id`.

## Step 3: Create scenes

For each scene, write a prompt that describes **action + environment + mood** only. Reference entities by name. Never describe character appearance.

- Scene 1: `chain_type: "ROOT"`
- Scene 2+: `chain_type: "CONTINUATION"`, `parent_scene_id: "<previous_scene_id>"`
- `character_names`: list ALL entities that should appear (characters + locations + assets)

```bash
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{"video_id": "<VID>", "display_order": N, "prompt": "...", "character_names": [...], "chain_type": "ROOT|CONTINUATION", "parent_scene_id": "..."}'
```

---

## Prompt-Writing Guide

### Image Prompt Formula

```
[Subject] [action verb] [at/in Location]. [Specific visual detail]. [Camera/composition].
```

**Good vs Bad:**

| Bad | Good | Why |
|-----|------|-----|
| `"Hero in castle"` | `"Hero pushes open the Castle gate and steps into the sunlit courtyard"` | Vague → action + specific moment |
| `"Luna the white cat with orange suit discovers river"` | `"Luna kneels at the edge of Chocolate River, dipping a paw in, surprised expression"` | Describing appearance → refs handle that |
| `"cinematic scene"` | `"Wide shot, low angle, Luna small against vast Candy Planet landscape, cotton candy clouds"` | Buzzword → specific camera + composition |

**Anti-patterns:**
- Never describe character appearance (eyes, hair, clothing) — reference images handle that
- Never use single-word or atmosphere-only prompts: `"epic"`, `"dramatic"`, `"cinematic"`
- Always include a camera/composition cue at the end

See `gla:camera-guide.md` for full camera language reference.

---

### Video Prompt Formula

```
0-Ns: [Camera angle+movement], [Subject action]. [Optional: Character says "dialogue."]
N-Ms: [Camera angle+movement], [Subject action]. [Optional: Character says "dialogue."]
M-8s: [Camera angle+movement], [Subject action]. [Silence or atmosphere note.]
```

**Emotional arc pattern (map to 8s):**
```
0-2s: Wide/establishing + crane or pan          (opening — set the stage)
2-5s: Medium + tracking or push in              (rising — build engagement)
5-7s: Close-up + static or slow motion          (peak — maximum emotion)
7-8s: Pull back to wide or crane up             (release — breathing room)
```

**Dialogue rules:**
- Max 10-15 words per character per 2-3s segment
- Use delivery verbs: `says`, `whispers`, `shouts`, `gasps`, `asks`, `replies`, `mutters`
- Silent segments are powerful — not every segment needs dialogue
- Multi-character OK: `Luna asks "Ready?" Hero replies "Let's go."`

**Example:**
```
0-3s: Wide crane down shot, Luna emerges from rocket onto Candy Planet Surface. Luna gasps "Wow!"
3-6s: Low angle tracking shot, Luna takes first steps on candy ground. Luna says "Everything is made of candy!"
6-8s: Wide static shot, Luna small against vast landscape, cotton candy clouds. Silence, gentle wind.
```

See `gla:camera-guide.md` for angle/movement/lighting vocabulary.

---

### Narrator Text Formula

```
[What the viewer CANNOT see: context/stakes/motivation]. [Tension or consequence]. [Short punchy closer.]
```

- 2-3 sentences max per 8s scene — strictly under 20 words per sentence
- Mirror the video timing: calm opener → rising tension → punchy close
- Add off-screen context: historical facts, character motivation, stakes
- Never describe what is visually obvious: `"We see a ship sailing"` → cut it

**Example:**
```
Captain Harris spots unusual radar signatures. Dozens of Iranian fast boats race straight toward the convoy. He orders battle stations.
```

See `gla:gen-narrator.md` for word count limits per language and narrative arc guide.

---

### Anti-Patterns Table

| Bad | Why | Good |
|-----|-----|------|
| `"Hero in castle"` | Too vague — no action, no composition | `"Hero walks into Castle courtyard at dawn, Magic Sword glowing on the wall. Wide shot."` |
| `"The tall muscular hero with blonde hair wearing golden armor..."` | Describes appearance — ref image handles it | `"Hero lifts Magic Sword above head, golden light fills the room. Close-up, slow motion."` |
| `"cinematic"` alone | Meaningless without specifics | `"Wide angle, low light, shallow depth of field, warm backlight"` |
| `"Scene 1: Luna is happy"` | Emotion without action or environment | `"Luna jumps up with arms raised at Chocolate River, face lit with joy. Medium shot."` |
| `"Camera zooms in on the action"` | Vague camera direction | `"Slow push in to close-up of Hero's eyes reflecting golden glow, rack focus from sword to face"` |

---

## Output

Print a summary table:
- Project ID, Video ID
- All entities with names and types
- All scenes with prompts (truncated) and chain type
- Next step: "Run /gla:gen-refs to generate reference images"

## Step 4: Review and Update Scenes

After creating scenes, review all prompts. If any prompt is too simple or missing detail, **PATCH it — do not delete and recreate**.

```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hero charges across the Castle bridge at dawn, sword raised, golden light catching the blade. Wide shot.",
    "video_prompt": "0-3s: Wide tracking shot, Hero sprints across bridge toward camera. 3-6s: Medium shot, Hero raises Magic Sword, light bursts from blade. 6-8s: Close-up of Hero face, determined, Castle gate looming behind.",
    "character_names": ["Hero", "Castle", "Magic Sword"],
    "narrator_text": "The hero charged forward, knowing there was no turning back."
  }'
```

**Patchable fields:** `prompt`, `video_prompt`, `image_prompt`, `character_names`, `narrator_text`, `display_order`, `chain_type`.

**Workflow:** create scenes → review all prompts → PATCH to improve → then run /gla:gen-refs and /gla:gen-images. Scenes are mutable — update freely before generation starts.
