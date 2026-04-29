Generate 4 YouTube-optimized thumbnail variants for a project video.

Usage: `/fk:thumbnail [project_id]`

## Step 1: Load project context

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>
curl -s "http://127.0.0.1:8100/api/videos?project_id=<PID>"
curl -s "http://127.0.0.1:8100/api/projects/<PID>/characters"
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Extract and understand:
- **Story**: what is this video about? What is the conflict? What is at stake?
- **Main character(s)**: who drives the story? (must have media_id for refs)
- **Key conflict**: what dramatic moment defines the video?
- **Language**: match the project language for text on thumbnail

## Step 2: Create 2-LINE TEXT

Every thumbnail needs **2 lines of text**:

**Line 1 (HOOK):** 2-3 power words — emotion/urgency/shock
**Line 2 (CONTEXT):** 5-8 words — what the video is about, answers "why click?"

### Examples:
- Military: Line 1 = "IRAN TẤN CÔNG!" / Line 2 = "Hải Quân Mỹ Mắc Kẹt Eo Biển Tử Thần"
- Romance: Line 1 = "CÔ ẤY ĐÃ CHẾT?" / Line 2 = "Bí Mật Kinh Hoàng Sau Đám Cưới"
- Action: Line 1 = "KHÔNG AI SỐNG SÓT" / Line 2 = "Vụ Cướp Thế Kỷ Tại Ngân Hàng Trung Ương"

### Rules:
- Both lines in project's language
- Line 1: provocative, uses power words (ATTACK, DEATH, IMPOSSIBLE, SHOCK, SECRET)
- Line 2: gives context — what/who/why (not just repeating Line 1)
- Line 2 makes Line 1 specific: "IRAN ATTACKS!" + "US Navy Trapped in Deadly Strait" → viewer knows WHAT

## Step 3: Build 4 thumbnail prompts

**ALL prompts MUST include:**
1. The hook text as bold text IN the image (not overlay)
2. Character names in `character_names` for face consistency
3. The project's material style prefix

### Non-English Text (CRITICAL)

For non-English text (Vietnamese, etc.), use the **language hint pattern** in prompts:
```
bold [COLOR] text in [LANGUAGE] clearly "[TEXT WITH DIACRITICS]" at [POSITION]
```

Example:
```
bold yellow text in Vietnamese clearly "IRAN TẤN CÔNG!" at top center in thick sans-serif font with red outline,
smaller white text in Vietnamese clearly "HẢI QUÂN MỸ MẮC KẸT EO BIỂN TỬ THẦN" below in bold font with shadow
```

**Without "in [Language] clearly":** Google Flow returns "invalid argument" for diacritical characters.

### Prompt template:

```
[MATERIAL_PREFIX] YouTube thumbnail,
bold [COLOR1] text in [LANGUAGE] clearly "[LINE1_HOOK]" at [POSITION] in thick sans-serif font with [OUTLINE_COLOR] outline,
smaller [COLOR2] text in [LANGUAGE] clearly "[LINE2_CONTEXT]" below in bold font with [SHADOW] shadow,
[MAIN_SUBJECT + EMOTION + ACTION],
[CAMERA_ANGLE + COMPOSITION],
[SETTING/ENVIRONMENT],
[LIGHTING + COLOR_PALETTE],
4K, 8K, masterpiece, highly detailed, sharp focus, HDR,
1280x720, 16:9 YouTube thumbnail format
```

### 4 variants — each uses different angle:

**V1 — Face + Text (hook via emotion):**
Main character face HUGE (50% of frame), extreme emotion, 2-line text at top.
Background: threat/explosion/danger barely visible.

**V2 — Action + Text (hook via stakes):**
Wide cinematic angle, overwhelming threat visible, 2-line text at upper-left.
Shows scale of danger.

**V3 — Confrontation + Text (hook via conflict):**
Hero vs villain/threat facing each other, 2-line text at top.
Clear visual tension between two sides.

**V4 — Mystery + Text (hook via curiosity):**
Character reacting to something OFF-SCREEN, 2-line text at upper-right.
Viewer can't see what character sees → must click.

## Step 4: Collect character refs

From entity list, include ALL main characters that have `media_id` in `character_names`.
This ensures faces match the video — critical for channel consistency.

If character refs fail (400 error), retry without refs but warn user.

## Step 5: Generate 4 thumbnails

SEQUENTIALLY with 8s cooldown between each:

```bash
# Get project output directory
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
mkdir -p "${OUTDIR}/thumbnails"

for i in 1 2 3 4; do
  curl -s -m 90 -X POST "http://127.0.0.1:8100/api/projects/<PID>/generate-thumbnail" \
    -H "Content-Type: application/json" \
    -d '{
      "prompt": "<variant_prompt_with_text_embedded>",
      "character_names": ["<main_char1>", "<main_char2>"],
      "aspect_ratio": "LANDSCAPE",
      "output_filename": "thumbnail_v'$i'.png"
    }'
  sleep 8
done
```

If reCAPTCHA fails: retry that variant once.
If 400 (missing refs): retry without character_names.

## Step 6: Resize to YouTube (1280x720)

```bash
for i in 1 2 3 4; do
  ffmpeg -y -i "${OUTDIR}/thumbnails/thumbnail_v${i}.png" \
    -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black" \
    "${OUTDIR}/thumbnails/thumbnail_v${i}_yt.png" 2>/dev/null
done
```

## Step 7: Show all 4 and evaluate

Display all 4 thumbnails using Read tool.

For EACH thumbnail, evaluate honestly:
- Is the text readable? Bold enough? Well-positioned?
- Is the face big enough (30-50% of frame)?
- Is the emotion extreme (not neutral)?
- Are colors bright and saturated (not dark/muted)?
- Would YOU click this on YouTube?
- Does it create curiosity — what happens next?

Rate each: STRONG / OK / WEAK with reason.

Ask user: "Which one? 1-4, 'regenerate N', or 'all' to redo everything"

## Step 8: Output

```
Thumbnails for: <project> — <video_title>
Hook text: <the hook words used>
Character refs: <names used>

V1 (Face+Text): [RATING] — thumbnail_v1_yt.png
V2 (Action+Text): [RATING] — thumbnail_v2_yt.png  
V3 (Confrontation+Text): [RATING] — thumbnail_v3_yt.png
V4 (Mystery+Text): [RATING] — thumbnail_v4_yt.png

Files: ${OUTDIR}/thumbnails/thumbnail_v*_yt.png (1280x720)
```
