# gla:gen-tts-template — Generate Voice Template

Create a reusable voice template for consistent narration across all scenes.

**IMPORTANT:** Always create a voice template BEFORE narrating scenes. Without a template, each scene generates with a slightly different voice. With a template, voice cloning ensures 100% consistency.

## Prerequisites

- OmniVoice installed: `pip install omnivoice` (Python 3.10)
- Server running: `curl http://127.0.0.1:8100/health`

## Workflow

### Step 1: Create Voice Template

**IMPORTANT:** Always use the **standard base transcript** for ALL templates.
This ensures `ref_text` is always known — no need to extract/transcribe later.

**Base transcript (English):**
> The Strait of Hormuz, the narrowest point only thirty-three kilometers wide. Twenty percent of the world's oil passes through here every day.

**When user specifies a language**, translate the base transcript to their language before creating the template:

- Vietnamese → `"Eo biển Hormuz, nơi hẹp nhất chỉ ba mươi ba ki-lô-mét. Hai mươi phần trăm lượng dầu thế giới đi qua đây mỗi ngày."`
- Japanese → `"ホルムズ海峡、最も狭い地点はわずか三十三キロメートル。世界の石油の二十パーセントが毎日ここを通過する。"`
- Korean → `"호르무즈 해협, 가장 좁은 지점은 겨우 삼십삼 킬로미터. 세계 석유의 이십 퍼센트가 매일 이곳을 통과합니다."`
- (Any other language: translate the base transcript yourself)

```bash
# Example: Vietnamese template
curl -X POST http://127.0.0.1:8100/api/tts/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "narrator_male_vn",
    "text": "Eo biển Hormuz, nơi hẹp nhất chỉ ba mươi ba ki-lô-mét. Hai mươi phần trăm lượng dầu thế giới đi qua đây mỗi ngày.",
    "instruct": "male, moderate pitch, young adult",
    "speed": 1.0
  }'
```

The `text` field serves dual purpose:
1. **During template creation:** OmniVoice speaks this text to generate the template WAV
2. **During scene narration:** Used as `ref_text` for voice cloning (phoneme alignment)

Same base transcript across all templates → `ref_text` is always known → consistent voice cloning without transcript extraction.

### Step 2: Listen & Verify

Open the returned `audio_path` and verify the voice matches your vision. If not, delete and recreate with different `instruct`.

### Step 3: Link to Project

```bash
curl -X PATCH http://127.0.0.1:8100/api/projects/<PID> \
  -H "Content-Type: application/json" \
  -d '{"narrator_ref_audio": "<audio_path from step 1>"}'
```

Or pass `template` name directly when narrating (recommended):
```bash
curl -X POST http://127.0.0.1:8100/api/videos/<VID>/narrate \
  -d '{"project_id": "<PID>", "template": "narrator_male_vn", "speed": 1.1}'
```

## Valid Instruct Terms

### English
- **Gender:** male, female
- **Age:** child, teenager, young adult, middle-aged, elderly
- **Pitch:** very low pitch, low pitch, moderate pitch, high pitch, very high pitch
- **Style:** whisper
- **Accent:** american accent, british accent, australian accent, canadian accent, indian accent, japanese accent, korean accent, chinese accent, russian accent, portuguese accent

### Tips
- Use comma + space between terms: `"male, low pitch, american accent"`
- Keep instruct short — 2-3 terms work best
- For Vietnamese narration, `"male, moderate pitch, young adult"` gives a clear documentary voice
- `speed: 1.1` gives slightly faster, more dynamic pacing

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tts/templates` | POST | Create voice template |
| `/api/tts/templates` | GET | List all templates |
| `/api/tts/templates/{name}` | GET | Get template details |
| `/api/tts/templates/{name}` | DELETE | Delete template |

## Important Notes

- Voice templates use **voice design** (instruct string) to generate an anchor voice
- When narrating scenes, the template WAV is used as **ref_audio** for voice cloning
- This ensures every scene sounds like the same narrator
- CPU mode only (MPS produces artifacts) — generation takes ~15-30s per template
- Template WAV is saved permanently in `output/tts/templates/`
