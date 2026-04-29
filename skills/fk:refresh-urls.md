Refresh expired GCS signed URLs for all scenes in a video (images, videos, upscale videos) and character reference images.

Usage: `/fk:refresh-urls <video_id> [--project-id <PID>]`

## When to use

- Before `/fk:review-video` if videos were generated hours ago (GCS signed URLs expire)
- Before `/fk:concat-fit-narrator` if downloading from URLs instead of local files
- After any long gap between generation and consumption of media URLs

## Pre-flight

```bash
# Extension must be connected with flow key
curl -s http://127.0.0.1:8100/api/flow/status
# Must show: {"connected": true, "flow_key_present": true}
# If flow_key_present is false: open/refresh a Google Flow tab in Chrome
```

## Step 1: Get project_id from video

```bash
VID="<video_id>"
PID=$(curl -s "http://127.0.0.1:8100/api/videos/${VID}" | python3 -c "import sys,json; print(json.load(sys.stdin)['project_id'])")
echo "Project: $PID"
```

## Step 2: Bulk refresh via TRPC

This calls Google Flow's TRPC `flow.getFlow` endpoint, extracts ALL fresh signed URLs from the response, and updates scenes + characters in DB.

```bash
curl -s -X POST "http://127.0.0.1:8100/api/flow/refresh-urls/${PID}" | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"Refreshed: {r.get('refreshed', 0)} URLs (found {r.get('found', 0)} total)\")
if r.get('error'):
    print(f\"ERROR: {r['error']}\")
"
```

**What gets updated:**
- `horizontal_image_url` / `vertical_image_url` — scene images
- `horizontal_video_url` / `vertical_video_url` — scene videos (original)
- `horizontal_upscale_url` / `vertical_upscale_url` — 4K upscaled videos
- `reference_image_url` — character/entity reference images

The server matches each URL's media_id against `*_media_id` fields on scenes and characters, updating whichever orientation/type matches.

## Step 3: Verify refresh worked

```bash
# Check a few scenes have valid URLs
curl -s "http://127.0.0.1:8100/api/scenes?video_id=${VID}" | python3 -c "
import sys, json
scenes = sorted(json.load(sys.stdin), key=lambda s: s['display_order'])

# Auto-detect orientation
ori = 'horizontal'
for s in scenes:
    if s.get('horizontal_video_status') == 'COMPLETED' and s.get('horizontal_video_url'):
        ori = 'horizontal'; break
    if s.get('vertical_video_status') == 'COMPLETED' and s.get('vertical_video_url'):
        ori = 'vertical'; break

ok = 0; expired = 0
for s in scenes:
    url = s.get(f'{ori}_video_url') or ''
    if url and 'Expires=' in url:
        import re, time
        m = re.search(r'Expires=(\d+)', url)
        if m and int(m.group(1)) > time.time():
            ok += 1
        else:
            expired += 1
    elif url:
        ok += 1
    else:
        expired += 1

print(f'Orientation: {ori.upper()}')
print(f'Valid URLs: {ok}/{len(scenes)}')
if expired:
    print(f'Still expired: {expired} — may need to open Flow tab in Chrome for flow key')
else:
    print('All URLs refreshed successfully!')
"
```

## Step 4: Per-media fallback (if TRPC fails)

If the bulk TRPC refresh doesn't cover all media (e.g., TRPC response is partial), fall back to per-media refresh:

```bash
# Get a fresh URL for a specific media_id
curl -s "http://127.0.0.1:8100/api/flow/media/<MEDIA_ID>"
# Returns: {fifeUrl: "https://...", servingUri: "https://...", ...}
```

Then update the scene manually:

```bash
curl -X PATCH "http://127.0.0.1:8100/api/scenes/<SID>" \
  -H "Content-Type: application/json" \
  -d '{"horizontal_video_url": "<FRESH_URL>"}'
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `flow_key_present: false` | Extension hasn't captured auth token | Open/refresh a Google Flow tab in Chrome |
| `Extension not connected` | Chrome extension WS disconnected | Check Chrome extension is enabled, refresh Flow tab |
| `refreshed: 0` | TRPC returned no URLs | Project may not exist on Google Flow, or auth expired |
| Some URLs still expired after refresh | media_id mismatch (upscale overwrote video_media_id) | Use per-media fallback with correct media_id |
| `get_media` returns error for media_id | Media deleted or expired on Google's side | Re-generate the video/image |
