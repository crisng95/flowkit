# fk-gen-narrator-free — Zero-Cost TTS via Microsoft Edge Neural Voices

Generate narrator TTS for a video's scenes without a cloned voice template.
Use this instead of `/fk-gen-narrator` when there is no voice template
(`/fk-gen-tts-template` not run) and the project doesn't need per-channel
voice cloning — Edge TTS needs no account, no API key, and no reference
audio, only a Python package.

Usage: `/fk-gen-narrator-free <video_id> [--voice <edge-voice-id>] [--rate +0%]`

Produces the same `${OUTDIR}/tts/scene_<IDX3>_<scene_id>.wav` files that
`/fk-gen-narrator` produces, so `/fk-concat --with-tts` works unchanged
regardless of which skill generated them.

## When to use this vs `/fk-gen-narrator`

| | `/fk-gen-narrator` | `/fk-gen-narrator-free` |
|---|---|---|
| Cost | Free (self-hosted OmniVoice) but requires voice template setup | Free, zero setup |
| Voice | Cloned from a reference WAV — matches a specific person/channel | Fixed catalog of Microsoft neural voices |
| Setup | `/fk-gen-tts-template` or `/fk-import-voice` first | `pip install edge-tts`, nothing else |
| Best for | Channel branding, consistent narrator identity across videos | One-off projects, prototypes, languages with no trained template yet |

If a voice template already exists, prefer `/fk-gen-narrator` for voice
consistency across a channel's catalog. Use this skill when there is none
and the user doesn't want to set one up right now.

## Step 1: Check / install edge-tts

```bash
python -c "import edge_tts" 2>/dev/null || pip install edge-tts
```

## Step 2: Narrator text

Same rules as `/fk-gen-narrator` Step 3 (word-count limits per language,
documentary style, narrative arc) — read that skill's Step 3 and Step 2's
narrative-arc table if scenes don't already have `narrator_text`. Save with:

```bash
curl -X PATCH "http://127.0.0.1:8100/api/scenes/<SID>" \
  -H "Content-Type: application/json" \
  -d '{"narrator_text": "<generated_text>"}'
```

Skip scenes already carrying `narrator_text` unless `--force`.

## Step 3: Pick a voice

| Voice ID | Language/Region | Profile | Good for |
|---|---|---|---|
| `vi-VN-HoaiMyNeural` | Vietnamese (F) | Crystalline clarity, nuanced emotional delivery | Poetic drama, fairy tale, introspective narrative |
| `vi-VN-NamMinhNeural` | Vietnamese (M) | Resonant baritone, authoritative | History, military, documentary, epic action |
| `en-US-AndrewNeural` | English US (M) | Warm, conversational | General narration |
| `en-US-AvaNeural` | English US (F) | Clear, bright | General narration |

Full catalog: `edge-tts --list-voices`. Default: `vi-VN-HoaiMyNeural` for
Vietnamese projects, `en-US-AndrewNeural` otherwise, unless `--voice` is given.

## Step 4: Generate TTS per scene, fitting the 8s clip

**Critical: a scene's video is 8s. The TTS file must land under that — Edge
TTS has no hard word-count gate like the cloned-voice path, so an
under-rate first pass can run long and get clipped by the concat step.**

Generate once at the requested rate (default `+0%`), probe the duration,
and only escalate the rate if it doesn't fit — don't guess a rate up front:

```python
import asyncio, subprocess, edge_tts

async def gen(text, out_path, voice, rate):
    await edge_tts.Communicate(text, voice=voice, rate=rate).save(out_path)

def duration_s(path):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True)
    return float(out.stdout.strip())

async def gen_fitted(text, out_path, voice, base_rate, max_s=7.5):
    """Try base_rate, then step the rate up until it fits max_s."""
    rate_pct = int(base_rate.strip('%').replace('+', '') or 0)
    for attempt in range(4):  # +0, then +8, +16, +24 on top of base
        rate = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"
        await gen(text, out_path, voice, rate)
        d = duration_s(out_path)
        if d <= max_s:
            return d, rate
        rate_pct += 8
    return d, rate  # last attempt — report overrun, don't loop forever
```

Run this per scene (skip scenes with no `narrator_text`, e.g. interview
scenes — see `/fk-gen-narrator` Step 1 classification). `max_s=7.5` leaves
a buffer under the 8s clip length; tighten to `7.0` if the concat step also
applies a leading `-ss` trim.

Report any scene that still overruns after 4 attempts — don't silently
ship clipped narration. Shorten the text instead of escalating rate further
(above ~+24% the voice starts sounding rushed).

## Step 5: Output directory

Same as `/fk-gen-narrator` Step 7 — `${OUTDIR}/tts/scene_<IDX3>_<scene_id>.wav`,
`IDX3` zero-padded 3-digit `display_order`.

```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python -c "import sys,json; print(json.load(sys.stdin)['path'])")
mkdir -p "${OUTDIR}/tts"
```

## Step 6: Verify and hand off

```bash
for f in "${OUTDIR}"/tts/scene_*.wav; do
  echo "$(basename "$f"): $(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f")s"
done
```

Print:
```
Free TTS generation complete: <project_name>
  Voice: <voice_id>
  Scenes narrated: N/M
  Scenes needing a rate bump to fit: K
  Output: ${OUTDIR}/tts/

  Next step: /fk-concat <video_id> --with-tts
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| TTS clipped mid-sentence in final video | TTS longer than scene's 8s clip | Re-run Step 4 — it auto-escalates rate; if still over, shorten `narrator_text` |
| `edge_tts` import error | Package not installed in the active venv | `source venv/Scripts/activate` (or `venv/bin/activate`) before `pip install edge-tts` |
| Voice sounds different per scene | Mixed voice IDs across scenes | Pass the same `--voice` for every scene in one video |
| No internet / corporate proxy blocks Edge TTS | Edge TTS calls a Microsoft cloud endpoint, not fully offline | Fall back to `/fk-gen-narrator` with a local voice template |
