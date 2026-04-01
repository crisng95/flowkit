Download and concatenate all scene videos into a single video.

Usage: `/concat <video_id> [output_dir]`

Default output_dir: `output/`

## Step 1: Get scenes with video URLs

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Sort by `display_order`. For each scene, use `vertical_upscale_url` if available (upscaled), otherwise `vertical_video_url`.

**ABORT** if any scene is missing video URL. Tell user to run `/gen-videos` first.

## Step 2: Get video title for folder name

```bash
curl -s http://127.0.0.1:8100/api/videos/<VID>
```

Create output folder: `output/<sanitized_title>/`

## Step 3: Download each scene

Use python httpx or curl to download each video:
```python
import httpx
client = httpx.Client(timeout=120, follow_redirects=True)
for scene in scenes:
    url = scene.get('vertical_upscale_url') or scene['vertical_video_url']
    r = client.get(url)
    with open(f'output/.../scene_{n}.mp4', 'wb') as f:
        f.write(r.content)
```

## Step 4: Normalize videos (same codec/resolution/fps)

```bash
ffmpeg -y -i scene_N.mp4 \
  -c:v libx264 -preset fast -crf 18 \
  -vf "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2" \
  -r 24 -pix_fmt yuv420p -an \
  scene_N_norm.mp4
```

For HORIZONTAL videos, use `scale=1280:720` and `pad=1280:720` instead.

## Step 5: Create concat list and merge

```bash
# Write concat.txt
echo "file 'scene_1_norm.mp4'" > concat.txt
echo "file 'scene_2_norm.mp4'" >> concat.txt
# ...for all scenes

# Concat
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy -movflags +faststart full_video.mp4
```

## Step 6: Output

Print:
- Output path
- Duration (from ffprobe)
- Resolution
- File size
- Individual scene files preserved for manual editing
