# fk:brand-logo — Apply Channel Branding (Intro + Outro + Logo + 4K Badge)

Full channel branding: prepend intro, append outro, overlay brand logo, and add 4K badge to final video.

Usage: `/fk:brand-logo <channel_name> <video_path> [--size 220] [--thumbnails] [--no-intro] [--no-outro]`

- `channel_name` — matches directory under `youtube/channels/<channel_name>/`
- `video_path` — the final video to brand (e.g., `output/.../slug_narrator_cut.mp4`)
- `--size N` — override brand logo size (default: auto-detect from resolution)
- `--thumbnails` — also apply logo to thumbnail PNGs
- `--no-intro` — skip intro prepend
- `--no-outro` — skip outro append

## Channel Directory Structure

```
youtube/channels/<channel_name>/
  <channel_name>_icon.png     # Brand logo (square, transparent bg)
  4k_icon.png                 # Optional 4K badge (auto-applied for 4K videos)
  intro_4k.mp4                # 4K intro video (optional)
  intro_4k_2x.mp4             # 2x speed intro variant (optional, preferred)
  intro_1080.mp4              # 1080p intro fallback (optional)
  outro_4k.mp4                # 4K outro video (optional)
  outro_1080.mp4              # 1080p outro fallback (optional)
  channel_info.json           # Channel metadata
```

Directory `youtube/channels/` is **gitignored** — local only per machine.

## Step 1: Locate channel assets

```bash
CHANNEL_DIR="youtube/channels/<channel_name>"
ICON="${CHANNEL_DIR}/<channel_name>_icon.png"
ICON_4K="${CHANNEL_DIR}/4k_icon.png"
```

**ABORT** if icon doesn't exist:
```
Icon not found: youtube/channels/<channel_name>/<channel_name>_icon.png
Please place your channel icon PNG there first.
```

## Step 2: Auto-detect resolution and select assets

```bash
RES=$(ffprobe -v quiet -show_entries stream=width -of csv=p=0 "$VIDEO")
```

| Resolution | Logo Size | Pad | Intro | Outro |
|-----------|-----------|-----|-------|-------|
| 3840x2160 (4K) | 220x220 | 40 | `intro_4k_2x.mp4` → `intro_4k.mp4` | `outro_4k.mp4` |
| 1920x1080 (1080p) | 130x130 | 24 | `intro_1080.mp4` → `intro_4k.mp4` | `outro_1080.mp4` → `outro_4k.mp4` |
| 1280x720 (origin) | 110x110 | 16 | `intro_1080.mp4` | `outro_1080.mp4` |

**Intro selection priority** (pick first that exists):
1. `intro_4k_2x.mp4` (speed-up variant — preferred for pacing)
2. `intro_4k.mp4`
3. `intro_1080.mp4` (will be scaled up if video is 4K)

**Outro selection priority:**
1. `outro_4k.mp4`
2. `outro_1080.mp4`

If no intro/outro file found → skip that step (don't abort).

## Step 3: Normalize intro/outro to match main video

Intro and outro must match the main video's resolution, fps, and codec for clean concat.

```bash
# Normalize intro
ffmpeg -y -i "$INTRO_FILE" \
  -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -preset fast -crf 18 -r 24 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "/tmp/gla_intro_norm.mp4"

# Normalize outro
ffmpeg -y -i "$OUTRO_FILE" \
  -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -preset fast -crf 18 -r 24 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "/tmp/gla_outro_norm.mp4"
```

**IMPORTANT: Never downscale. If main video is 4K, intro/outro output must be 4K too.**

## Step 4: Normalize main video audio

**CRITICAL:** Main video audio may be 24kHz mono (from TTS mixing) while intro/outro are 48kHz stereo. All parts must match before concat or audio will drop out.

```bash
ffprobe -v quiet -show_entries stream=sample_rate,channels -select_streams a -of csv=p=0 "$VIDEO"
# If NOT "48000,2" → re-encode audio:
ffmpeg -y -i "$VIDEO" \
  -c:v copy \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart \
  "/tmp/gla_main_norm.mp4"
# If already 48kHz stereo → just copy:
# cp "$VIDEO" "/tmp/gla_main_norm.mp4"
```

## Step 5: Concat intro + main + outro

```bash
# Build concat list
cat > /tmp/gla_brand_concat.txt << EOF
file '/tmp/gla_intro_norm.mp4'
file '/tmp/gla_main_norm.mp4'
file '/tmp/gla_outro_norm.mp4'
EOF

# If --no-intro: remove intro line
# If --no-outro: remove outro line

ffmpeg -y -f concat -safe 0 -i /tmp/gla_brand_concat.txt \
  -c copy -movflags +faststart \
  "/tmp/gla_with_intro_outro.mp4"
```

## Step 6: Apply brand logo overlay

The logo covers the **Veo watermark** ("V" text) at the bottom-right corner.

```bash
ffmpeg -y -i "/tmp/gla_with_intro_outro.mp4" -i "$ICON" \
  -filter_complex "[1:v]scale=${SIZE}:${SIZE},format=rgba[icon];[0:v][icon]overlay=W-w-${PAD}:H-h-${PAD}" \
  -c:v libx264 -preset fast -crf 18 -r 24 -pix_fmt yuv420p \
  -c:a copy -movflags +faststart \
  "${VIDEO%.mp4}_branded.mp4"
```

## Step 7: Apply 4K badge (if applicable)

Check for `4k_icon.png` AND source video is 4K (width >= 3840):

```bash
if [ -f "$ICON_4K" ] && [ "$RES" -ge 3840 ]; then
  ffmpeg -y -i "${VIDEO%.mp4}_branded.mp4" -i "$ICON_4K" \
    -filter_complex "[1:v]scale=-1:180,format=rgba[icon4k];[0:v][icon4k]overlay=W-w-40:40" \
    -c:v libx264 -preset fast -crf 18 -r 24 -pix_fmt yuv420p \
    -c:a copy -movflags +faststart \
    "${VIDEO%.mp4}_branded_tmp.mp4"
  mv "${VIDEO%.mp4}_branded_tmp.mp4" "${VIDEO%.mp4}_branded.mp4"
fi
```

## Step 8: Apply to thumbnails (if --thumbnails)

```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")

for thumb in "${OUTDIR}/thumbnails/thumbnail_v"*_yt.png; do
  ffmpeg -y -i "$thumb" -i "$ICON" \
    -filter_complex "[1:v]scale=72:72[icon];[0:v][icon]overlay=W-w-16:H-h-16" \
    "${thumb%_yt.png}_final.png" 2>/dev/null
done
```

## Step 9: Cleanup and verify

```bash
# Remove temp files
rm -f /tmp/gla_intro_norm.mp4 /tmp/gla_main_norm.mp4 /tmp/gla_outro_norm.mp4 /tmp/gla_with_intro_outro.mp4 /tmp/gla_brand_concat.txt

# Verify
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${VIDEO%.mp4}_branded.mp4"
ffprobe -v quiet -show_entries stream=width,height -of csv=p=0 "${VIDEO%.mp4}_branded.mp4"
ls -lh "${VIDEO%.mp4}_branded.mp4"
```

Print:
```
Channel branding applied: <channel_name>
  Output: <output_path>_branded.mp4
  Duration: X:XX (intro Xs + main Xs + outro Xs)
  Resolution: WxH
  Intro: <intro_file> (Xs)
  Outro: <outro_file> (Xs)
  Brand logo: <size>x<size> at bottom-right
  4K badge: 180px at top-right (if applied)
  Size: XXX MB
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Audio gap at intro/main join | Different audio codecs | Normalize step ensures AAC throughout |
| Resolution mismatch glitch | Intro is 1080p, main is 4K | Normalize step scales intro to match |
| Intro too long | Full-length intro | Use `intro_4k_2x.mp4` (2x speed) or trim |
| No intro/outro found | Files not in channel dir | Place `intro_4k.mp4` / `outro_4k.mp4` in channel directory |
| Logo covers content | Size too large | Use `--size N` to override |
