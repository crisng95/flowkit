# fk:gen-text-overlays — Generate Text Overlays from Narrator Text

Analyze narrator text for each scene and extract key data points (dates, locations, statistics, milestones, costs) to create `text_overlays.json` for `/fk:concat-fit-narrator`.

Usage: `/fk:gen-text-overlays <video_id> [--language vi]`

- `video_id` — the video to generate overlays for
- `--language` — target language code (default: auto-detect from narrator text). **All overlay text MUST be in this language with proper diacritics/characters.**

## Step 1: Load project, video, scenes

```bash
curl -s http://127.0.0.1:8100/api/videos/<VID>
# Get project_id
curl -s http://127.0.0.1:8100/api/projects/<PID>
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir
```

Sort scenes by `display_order`. Note `OUTDIR` from output-dir response.

## Step 2: Detect target language

If `--language` not provided, auto-detect from the first scene's `narrator_text`:
- Vietnamese diacritics (ắ, ề, ổ, ử, ơ, etc.) → `vi`
- Spanish characters (ñ, á, é, etc.) → `es`
- Default → `en`

**CRITICAL RULE: All overlay text MUST be written in the detected language with full diacritics and proper characters. NEVER strip diacritics or romanize.**

Examples:
- Vietnamese: "Chiến dịch Tapalpa" NOT "Chien dich Tapalpa"
- Vietnamese: "Tiền thưởng" NOT "Tien thuong"
- Spanish: "Operación Tapalpa" NOT "Operacion Tapalpa"

## Step 3: Analyze each scene's narrator text

For each scene with `narrator_text`, extract data points that fit these overlay categories:

### Overlay styles

| Style | What to extract | Color |
|-------|----------------|-------|
| `date` | Dates, times, timestamps, time references | Cyan |
| `name` | Locations, operation names, people, organizations | White |
| `stat` | Numbers, quantities, distances, technology milestones | White |
| `cost` | Casualties, monetary values, damage, human cost | Gold |

### Extraction rules

1. **NOT every scene needs overlays.** Only add overlays when there's a clear, impactful data point.
2. **Target ~40-50% of scenes** having overlays (e.g., 25-30 out of 60 scenes).
3. **Max 2 text items per scene** — one primary, one secondary.
4. **Keep text SHORT** — max 40 characters per line. Abbreviate if needed.
5. **Prioritize hard data** — numbers, dates, names, costs over descriptive text.
6. **Avoid repeating** the same information across adjacent scenes.

### What makes a good overlay

Good:
- "22 tháng 2, 2026" (specific date)
- "Tiền thưởng: $15,000,000" (hard number)
- "Guadalajara, Jalisco" (specific location)
- "25 lính hy sinh — 70+ người chết" (casualty stats)
- "Net-Centric Warfare" (tech milestone — keep original English terms)

Bad:
- "Mọi thứ thay đổi" (too vague)
- "Tình hình rất căng thẳng" (no data point)
- "Chiến dịch tiếp tục" (no specific info)

### Special handling

- **Technical terms** (Net-Centric Warfare, RPG, DEA, CJNG, FIFA): keep in original language/acronym.
- **People names**: keep original spelling (El Mencho, El Pelón, Nemesio Oseguera Cervantes).
- **Currency**: use `$X,XXX,XXX` format with dollar sign.
- **Casualty numbers**: pair with context (e.g., "25 lính hy sinh" not just "25").

## Step 4: Generate text_overlays.json

Build JSON object where keys are scene `display_order` (as string), values are arrays of overlay items:

```json
{
  "0": [
    {"text": "22 tháng 2, 2026", "style": "date"},
    {"text": "Tapalpa, Jalisco, Mexico", "style": "name"}
  ],
  "8": [
    {"text": "Mật danh: Chiến dịch Tapalpa", "style": "name"},
    {"text": "6 trực thăng — hàng trăm đặc nhiệm", "style": "stat"}
  ]
}
```

## Step 5: Validate and save

Before saving, validate:
1. All text is in the correct target language with proper diacritics
2. No text exceeds 40 characters
3. No scene has more than 2 overlay items
4. Scene indices are valid (within 0 to scene_count-1)
5. All styles are one of: `date`, `name`, `stat`, `cost`

Print validation table:

```
Scene | Style | Text (40 char max)
------|-------|-------------------
  000 | date  | 22 tháng 2, 2026
  000 | name  | Tapalpa, Jalisco, Mexico
  008 | name  | Mật danh: Chiến dịch Tapalpa
  ...
Total: X overlays across Y scenes (Z% coverage)
```

Save to `${OUTDIR}/text_overlays.json`.

```bash
# Verify JSON is valid
python3 -c "import json; d=json.load(open('${OUTDIR}/text_overlays.json')); print(f'{len(d)} scenes with overlays, {sum(len(v) for v in d.values())} total items')"
```

## Step 6: Report

```
Text overlays generated: <project_name>
  Language: <detected_language>
  Scenes with overlays: X/Y (Z%)
  Total overlay items: N
  Styles: date=A, name=B, stat=C, cost=D
  Output: ${OUTDIR}/text_overlays.json

Ready for /fk:concat-fit-narrator
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Text without diacritics | Language not detected | Pass `--language vi` explicitly |
| Too many overlays | Over-extraction | Aim for 40-50% scene coverage |
| Text too long | Not abbreviated | Keep under 40 chars, use short forms |
| Overlays feel repetitive | Adjacent scenes have similar data | Space out overlays, skip adjacent scenes |
