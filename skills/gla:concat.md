Download and concatenate all scene videos into a single video with optional TTS narration.

Usage: `/gla:concat <video_id> [--with-tts] [--4k]`

Default: uses best available quality (4K upscale > regular video), preserves original audio.

## Step 1: Get project, video, and scenes

```bash
curl -s http://127.0.0.1:8100/api/videos/<VID>
# Get project_id from video response
curl -s http://127.0.0.1:8100/api/projects/<PID>
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Note: project name (for output folder), orientation (HORIZONTAL or VERTICAL).
Sort scenes by `display_order`.

## Step 2: Determine video source for each scene

Priority order for each scene:
1. **Local 4K file:** `output/4k_raw/{scene_id}.mp4` (saved from rawBytes — best quality)
2. **Upscale URL:** `horizontal_upscale_url` or `vertical_upscale_url` (4K signed URL — may be expired)
3. **Video URL:** `horizontal_video_url` or `vertical_video_url` (standard quality)

Check orientation from project or first scene. Use matching prefix (`horizontal_` or `vertical_`).

**ABORT** if any scene has no video source. Tell user to run `/gla:gen-videos` first.

## Step 3: Setup output directory

```bash
PROJECT_NAME="<sanitized_project_name>"  # lowercase, spaces→underscores
mkdir -p output/${PROJECT_NAME}/{4k,narrated,norm}
```

## Step 4: Download videos (skip if local file exists)

```bash
# For each scene, check local first
if [ -f "output/4k_raw/${SCENE_ID}.mp4" ]; then
  cp "output/4k_raw/${SCENE_ID}.mp4" "output/${PROJECT_NAME}/4k/scene_${IDX}.mp4"
else
  curl -L -o "output/${PROJECT_NAME}/4k/scene_${IDX}.mp4" "${UPSCALE_URL_OR_VIDEO_URL}"
fi
```

Verify each download: `ffprobe` should return valid video stream.

## Step 5: Determine output resolution

- If `--4k` flag: use `3840:2160` (HORIZONTAL) or `2160:3840` (VERTICAL)
- Otherwise: match source resolution from first downloaded scene via ffprobe

**IMPORTANT: Never downscale 4K videos. If source is 3840x2160, output must be 3840x2160.**

## Step 6: Normalize + mix audio

### Option A: Without TTS (default)
Preserve original video audio (sound effects from Google Flow):
```bash
ffmpeg -y -i "scene_${IDX}.mp4" \
  -c:v libx264 -preset fast -crf 18 \
  -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2" \
  -r 24 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart "norm/scene_${IDX}.mp4"
```

### Option B: With TTS narration (`--with-tts`)
Mix TTS audio WITH video sound effects using `amix` filter:

```bash
# Find matching TTS wav
TTS_WAV="output/${PROJECT_NAME}/tts/scene_${IDX3}_${SCENE_ID}.wav"
# OR from: output/tts/${VIDEO_ID}/scene_${IDX3}_${SCENE_ID}.wav

if [ -f "$TTS_WAV" ]; then
  # MIX: video SFX at 30% volume + TTS narrator at 150% volume
  ffmpeg -y -i "scene_${IDX}.mp4" -i "$TTS_WAV" \
    -filter_complex "[0:a]volume=0.3[bg];[1:a]volume=1.5[fg];[bg][fg]amix=inputs=2:duration=shortest[aout]" \
    -map 0:v -map "[aout]" \
    -c:v libx264 -preset fast -crf 18 \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2" \
    -r 24 -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    -movflags +faststart "narrated/scene_${IDX}.mp4"
else
  # No TTS for this scene — normalize with original audio only
  ffmpeg -y -i "scene_${IDX}.mp4" \
    -c:v libx264 -preset fast -crf 18 \
    -vf "scale=${W}:${H}" -r 24 -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    -movflags +faststart "narrated/scene_${IDX}.mp4"
fi
```

**CRITICAL: Do NOT use `-an` (strips all audio). Always preserve or mix audio.**

## Step 7: Create concat list and merge

```bash
# Use narrated/ if --with-tts, otherwise norm/
SRC_DIR="narrated"  # or "norm"

> concat.txt
for i in $(seq 0 $((NUM_SCENES-1))); do
  idx=$(printf "%02d" $i)
  echo "file '${SRC_DIR}/scene_${idx}.mp4'" >> concat.txt
done

ffmpeg -y -f concat -safe 0 -i concat.txt -c copy -movflags +faststart \
  "${PROJECT_NAME}_final.mp4"
```

## Step 8: Verify and output

```bash
# Verify final video
ffprobe -v quiet -show_entries stream=width,height,codec_name,codec_type -of csv=p=0 "${PROJECT_NAME}_final.mp4"
ls -lh "${PROJECT_NAME}_final.mp4"
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${PROJECT_NAME}_final.mp4"

# Verify audio is present (not silent)
ffmpeg -t 10 -i "${PROJECT_NAME}_final.mp4" -af "volumedetect" -f null /dev/null 2>&1 | grep "mean_volume"
# mean_volume should be between -30 and -10 dB (not -inf which means silent)
```

Print:
```
Concat complete: <project_name>
  Output: output/<project_name>/<filename>.mp4
  Duration: X:XX
  Resolution: WxH
  Audio: AAC (SFX + TTS narrator) or AAC (SFX only)
  Size: XXX MB
  Scenes: N
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| No audio in final | Used `-an` in normalize step | Remove `-an`, use `-c:a aac` |
| TTS not audible | TTS wav not mixed, only video audio used | Use `amix` filter with `-filter_complex` |
| Video is 1080p not 4K | Normalize used wrong scale | Match source resolution, never downscale |
| Signed URL expired | GCS URLs have ~8h TTL | Check local `output/4k_raw/` files first |
| Scene order wrong | Not sorted by display_order | Sort scenes before processing |
