# gla:gen-narrator — Generate Narrator Text + TTS for All Scenes

Auto-generate documentary-style narrator text from scene video_prompts, then generate TTS audio using a voice template.

Usage: `/gla:gen-narrator <video_id> [--force] [--language vi] [--speed 1.1]`

Prepares audio for `/gla:concat-fit-narrator`.

## Step 1: Load project, video, scenes

```bash
curl -s http://127.0.0.1:8100/api/videos/<VID>
curl -s http://127.0.0.1:8100/api/projects/<PID>
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Note: project name, language, story context.
Sort scenes by `display_order`.

## Step 2: Check voice template

```bash
curl -s http://127.0.0.1:8100/api/tts/templates
```

If NO templates exist:
```
No voice template found. Run /gla:gen-tts-template first to create one.
Voice consistency requires a template — without it, each scene sounds different.
```
**ABORT** — do not proceed without a voice template.

If templates exist, list them and ask user which to use (or default to the first one).

Also check for `ref_audio` files:
```bash
ls output/tts/voice_template_*.wav 2>/dev/null
```

User can specify a template name OR a ref_audio path directly.

## Step 3: Generate narrator text for each scene

For each scene (sorted by display_order):

### Skip logic (unless --force):
- If scene already has `narrator_text` AND not --force → skip

### Read the scene's `video_prompt` and `prompt`

The `video_prompt` describes what happens in the 8s video (sub-clip timing).
The `prompt` describes the still image (frame 0).
The project `story` provides overall narrative context.

### Generate narrator_text following these rules:

**Language:** Use `--language` flag or project's `language` field.

**Word count targets (for 8s scene at 1.1x speed):**
- Vietnamese: 25-35 words → fills 5-7s
- English: 20-30 words → fills 5-7s

**Documentary narrator style:**

DO:
- Add context the viewer CAN'T see: historical facts, stakes, motivations
- Add emotion and tension: "One wrong move — and it's war"
- Use short punchy sentences, varied rhythm
- Build narrative arc across scenes (setup → rising → climax → resolution)
- Match the story's genre and tone
- Reference character names from the scene's `character_names`

DON'T:
- Describe what's visually obvious: "We see a ship sailing" (viewer sees it)
- Use filler phrases: "In this scene...", "Meanwhile...", "As we can see..."
- Exceed word count (too long = rushed speech, bad audio)
- Be too short (< 15 words = dead air, awkward silence)
- Use passive voice: "The ship was attacked" → "Iran attacked the ship"

### Example (military documentary, Vietnamese):

Scene video_prompt: `0-3s: Captain Harris stands on the bridge scanning the horizon. 3-6s: Radar shows multiple fast contacts approaching. 6-8s: Captain grabs radio and orders battle stations.`

narrator_text: `Đại tá Harris phát hiện tín hiệu radar bất thường. Hàng chục tàu cao tốc Iran đang lao thẳng về phía đoàn hộ tống. Ông ra lệnh chiến đấu.`
(31 words, ~5.5s at 1.1x, adds context about Iran + convoy not visible in scene)

### Example (military documentary, English):

narrator_text: `Captain Harris spots unusual radar signatures. Dozens of Iranian fast boats are racing straight toward the convoy. He orders battle stations.`
(21 words, ~5s at 1.1x)

## Step 4: Save narrator_text to each scene

For each scene with generated text:

```bash
curl -X PATCH "http://127.0.0.1:8100/api/scenes/<SID>" \
  -H "Content-Type: application/json" \
  -d '{"narrator_text": "<generated_text>"}'
```

## Step 5: Show all narrator texts for review

Print a table:

```
Scene | Words | Est. Duration | Narrator Text
------|-------|---------------|---------------
  000 |    31 |         5.5s  | Đại tá Harris phát hiện tín hiệu...
  001 |    28 |         5.0s  | Tàu dầu Meridian Star nặng nề...
  002 |    33 |         5.8s  | Eo biển Hormuz — nơi 20% dầu mỏ...
  ...
Total: 40 scenes, ~1200 words, ~210s narration
```

Ask user: "Review OK? Type 'yes' to generate TTS, or 'edit N' to modify scene N's text."

## Step 6: Generate TTS for all scenes

**CRITICAL: Always use a registered template** (not raw `ref_audio`).
The template stores `ref_text` — without it, voice cloning produces inconsistent voices across scenes.

```bash
curl -X POST "http://127.0.0.1:8100/api/videos/<VID>/narrate" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<PID>",
    "template": "<template_name>",
    "speed": 1.1,
    "mix": false
  }'
```

The `template` parameter resolves both `ref_audio` (voice WAV) AND `ref_text` (transcript) from `templates.json`.

If user insists on raw `ref_audio`, always pass `ref_text` too:
```bash
curl -X POST "http://127.0.0.1:8100/api/videos/<VID>/narrate" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<PID>",
    "ref_audio": "<voice_template_path>",
    "ref_text": "<transcript of the voice template>",
    "speed": 1.1,
    "mix": false
  }'
```

**Why ref_text matters:** OmniVoice uses `ref_audio` + `ref_text` together for voice cloning.
Without `ref_text`, it falls back to generic voice design → each scene sounds different.

**mix: false** — we don't mix here. Mixing happens in `/gla:concat-fit-narrator`.

## Step 7: Copy TTS to project directory

TTS files are generated to `output/tts/<video_id>/`. Copy them to the project directory:

```bash
PROJECT_NAME="<sanitized_project_name>"
mkdir -p output/${PROJECT_NAME}/tts
cp output/tts/<VID>/scene_*.wav output/${PROJECT_NAME}/tts/
```

Verify file naming matches expected pattern:
```
scene_000_<scene_id>.wav
scene_001_<scene_id>.wav
...
scene_039_<scene_id>.wav
```

## Step 8: Verify and output

```bash
ls output/${PROJECT_NAME}/tts/scene_*.wav | wc -l
# Should match number of scenes with narrator_text

# Check a few durations
for f in $(ls output/${PROJECT_NAME}/tts/scene_00*.wav | head -5); do
  echo "$(basename $f): $(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f")s"
done
```

Print:
```
Narrator generation complete: <project_name>
  Scenes narrated: N/M
  Language: Vietnamese
  Voice: <template_name or ref_audio>
  Speed: 1.1x
  Total narration: XXXs
  Output: output/<project_name>/tts/

  Next step: /gla:concat-fit-narrator <video_id>
```

## Narrative Arc Guide

When writing narrator text for 30-40 scenes, follow a narrative arc:

| Phase | Scenes | Tone | Example |
|-------|--------|------|---------|
| **Setup** | 1-5 | Calm, informative | "Eo biển Hormuz — tuyến đường huyết mạch..." |
| **Rising** | 6-15 | Building tension | "Radar phát hiện nhiều tín hiệu bất thường..." |
| **Climax** | 16-25 | Intense, urgent | "Iran tấn công! Hàng chục tàu lao về phía đoàn hộ tống!" |
| **Resolution** | 26-35 | Relief, reflection | "Đoàn tàu đã vượt qua eo biển an toàn..." |
| **Epilogue** | 36-40 | Reflective, closing | "Chiến dịch Hormuz Shield — bài học về sức mạnh răn đe..." |

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| TTS sounds different each scene | No voice template | Run /gla:gen-tts-template first |
| Narrator text too long | Exceeds word count | Keep under 35 VN / 30 EN words |
| Dead air in scene | Narrator text too short | Aim for 25+ VN / 20+ EN words |
| Wrong language | Didn't match project language | Use --language flag or check project.language |
| TTS files not found by concat | Wrong output path | Copy to output/{project}/tts/ |
| Narrator describes visuals | Bad writing style | Remove "we see", describe context/stakes instead |
