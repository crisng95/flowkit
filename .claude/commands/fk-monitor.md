# fk-monitor — Full Pipeline Monitor

Poll project pipeline status every N seconds, detect state changes across all stages, send Telegram notifications, and optionally auto-download completed upscales.

Usage: `/fk-monitor [project_id] [orientation] [--download] [--interval N]`

- `project_id` — omit to use most recently active project
- `orientation` — `HORIZONTAL` or `VERTICAL` (auto-detected from video.orientation if omitted)
- `--download` — auto-download new upscales to `output/{slug}/4k/`
- `--interval N` — poll interval in seconds (default: 30)

## When to Use

- Long-running batch: submitted image/video/upscale jobs and want to be notified when stages complete
- Unattended generation: step away and get Telegram pings at milestones
- Debugging: spot stalled workers or failed requests early
- Auto-download: pull 4K upscales as they finish without manual polling

## Prerequisites

```bash
curl -s http://127.0.0.1:8100/health
# extension_connected must be true
```

Telegram notifications require the `mcp__telegram__reply` tool to be available in this session.

---

## Step 1: Resolve project and slug

If no `project_id` supplied, fetch the most recent project:

```bash
curl -s http://127.0.0.1:8100/api/projects
# Use the last item in the array → id, name
```

Derive slug from project name:

```python
import unicodedata, re

def slugify(name):
    # Strip diacritics
    normalized = unicodedata.normalize('NFD', name)
    ascii_only = normalized.encode('ascii', 'ignore').decode()
    # Lowercase, replace non-alphanum with underscore
    slug = re.sub(r'[^a-z0-9]+', '_', ascii_only.lower())
    # Collapse and trim
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug
```

Examples:
- "My Project - Edition" → `my_project_edition`
- "Chiến dịch giải cứu F-15E" → `chien_dich_giai_cuu_f_15e`

Get output dir (also creates directory structure):

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir
# Returns: {"slug": "...", "path": "output/...", "meta": {...}}
```

---

## Step 2: Resolve video_id and scene count

```bash
curl -s "http://127.0.0.1:8100/api/videos?project_id=<PID>"
# Use first video → id, get scene count

curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
# Total scene count = N
```

---

## Step 3: Get Telegram chat_id

The monitor sends all notifications to one chat. Ask the user for their Telegram chat_id if not already known:

```
To send Telegram notifications, I need your Telegram chat_id.
You can find it by messaging @userinfobot on Telegram.
```

Store as `CHAT_ID` for all `mcp__telegram__reply` calls.

---

## Step 4: Send start notification

```
mcp__telegram__reply(
  chat_id=CHAT_ID,
  text="🔍 Monitor started: <project_name>\n"
       "Orientation: <ORIENTATION> | Interval: <N>s\n"
       "Stages: ref images, scene images, videos, 4K upscale, downloads, TTS"
)
```

---

## Step 5: Poll loop

Run the poll cycle in a Python inline script. Each cycle:

### 5a. Fetch all data

```bash
# Fetch in parallel (run as background + wait)
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters > /tmp/fk_chars.json &
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>" > /tmp/fk_scenes.json &
curl -s "http://127.0.0.1:8100/api/requests?status=PENDING" > /tmp/fk_pending.json &
curl -s "http://127.0.0.1:8100/api/requests?status=PROCESSING" > /tmp/fk_processing.json &
curl -s "http://127.0.0.1:8100/api/requests?status=FAILED" > /tmp/fk_failed.json &
wait
```

### 5b. Compute snapshot

Detect orientation: if not passed as argument, read from `GET /api/videos/{vid}` → `orientation` field. Fall back to `HORIZONTAL` only if API returns null. Set `PREFIX` = detected orientation lowercase.

```python
import json, os, glob, time

chars   = json.load(open('/tmp/fk_chars.json'))
scenes  = json.load(open('/tmp/fk_scenes.json'))
pending = json.load(open('/tmp/fk_pending.json'))
processing = json.load(open('/tmp/fk_processing.json'))
failed  = json.load(open('/tmp/fk_failed.json'))

PREFIX = video_orientation.lower()  # from GET /api/videos/{vid} → orientation field; fall back to 'horizontal'
OUTDIR = 'output/<slug>'
TOTAL  = len(scenes)
TOTAL_CHARS = len(chars)

snapshot = {
    # Stage 1: ref images
    'refs_done': sum(1 for c in chars if c.get('media_id')),
    'refs_total': TOTAL_CHARS,

    # Stage 2: scene images
    'images_done': sum(1 for s in scenes if s.get(f'{PREFIX}_image_status') == 'COMPLETED'),
    'images_total': TOTAL,

    # Stage 3: scene videos
    'videos_done': sum(1 for s in scenes if s.get(f'{PREFIX}_video_status') == 'COMPLETED'),
    'videos_total': TOTAL,

    # Stage 4: 4K upscale
    'upscales_done': sum(1 for s in scenes if s.get(f'{PREFIX}_upscale_status') == 'COMPLETED'),
    'upscales_total': TOTAL,

    # Stage 5: 4K downloads
    'downloads_done': len(glob.glob(f'{OUTDIR}/4k/scene_*.mp4')),
    'downloads_total': TOTAL,

    # Stage 6: TTS narration
    'tts_done': len(glob.glob(f'{OUTDIR}/tts/scene_*.wav')),
    'tts_total': TOTAL,

    # Worker queue
    'pending_count': len(pending) if isinstance(pending, list) else pending.get('total', 0),
    'processing_count': len(processing) if isinstance(processing, list) else processing.get('total', 0),

    # Failures
    'failed_count': len(failed) if isinstance(failed, list) else failed.get('total', 0),
    'failed_types': list({r.get('type','unknown') for r in (failed if isinstance(failed, list) else [])}),
}
```

### 5c. Diff with previous snapshot and emit notifications

```python
# Milestone thresholds
MILESTONE_STEP = 10

def milestone_crossed(prev, curr, total):
    """Returns milestone value if a multiple of MILESTONE_STEP was crossed."""
    if total == 0:
        return None
    prev_m = (prev // MILESTONE_STEP) * MILESTONE_STEP
    curr_m = (curr // MILESTONE_STEP) * MILESTONE_STEP
    if curr_m > prev_m and curr < total:
        return curr_m
    return None

notifications = []

STAGES = [
    ('refs',      'Ref images',    snapshot['refs_done'],      snapshot['refs_total']),
    ('images',    'Scene images',  snapshot['images_done'],    snapshot['images_total']),
    ('videos',    'Scene videos',  snapshot['videos_done'],    snapshot['videos_total']),
    ('upscales',  '4K upscale',    snapshot['upscales_done'],  snapshot['upscales_total']),
    ('downloads', '4K downloads',  snapshot['downloads_done'], snapshot['downloads_total']),
    ('tts',       'TTS narration', snapshot['tts_done'],       snapshot['tts_total']),
]

for key, label, curr, total in STAGES:
    prev = prev_snapshot.get(f'{key}_done', 0) if prev_snapshot else 0

    if total == 0:
        continue

    # 100% completion
    if curr == total and prev < total:
        notifications.append(f'✅ {label} complete: {curr}/{total}')

    # Milestone every 10
    elif (m := milestone_crossed(prev, curr, total)):
        notifications.append(f'🔄 {label}: {curr}/{total}')

# Worker stall detection
if (snapshot['pending_count'] > 0
        and snapshot['processing_count'] == 0
        and time.time() - last_change_ts > 120):
    notifications.append(
        f'⚠️ Worker stalled! {snapshot["pending_count"]} requests pending but 0 processing.\n'
        f'Check server logs — may need to restart the GLA server.'
    )

# New failures
prev_failed = prev_snapshot.get('failed_count', 0) if prev_snapshot else 0
if snapshot['failed_count'] > prev_failed:
    new_n = snapshot['failed_count'] - prev_failed
    types_str = ', '.join(snapshot['failed_types']) or 'unknown'
    notifications.append(f'❌ {new_n} new failure(s) detected: {types_str}')

# All complete check
all_done = all(
    snapshot[f'{k}_done'] >= snapshot[f'{k}_total']
    for k in ['refs', 'images', 'videos']
    if snapshot[f'{k}_total'] > 0
)
if all_done and not prev_all_done:
    notifications.append(
        '🎉 Project complete! All pipeline stages done.\n'
        'Ready for /fk-concat'
    )
```

### 5d. Send notifications

For each notification string:

```
mcp__telegram__reply(
  chat_id=CHAT_ID,
  text="[<project_name>]\n" + notification_text
)
```

Send a combined status summary every 5 cycles regardless of changes:

```
mcp__telegram__reply(
  chat_id=CHAT_ID,
  text=(
    f"[<project_name>] Status update\n"
    f"Refs:      {refs_done}/{refs_total}\n"
    f"Images:    {images_done}/{images_total}\n"
    f"Videos:    {videos_done}/{videos_total}\n"
    f"4K upscale:{upscales_done}/{upscales_total}\n"
    f"Downloads: {downloads_done}/{downloads_total}\n"
    f"TTS:       {tts_done}/{tts_total}\n"
    f"Queue:     {pending_count} pending / {processing_count} processing"
  )
)
```

### 5e. Auto-download (when --download)

When `upscales_done` increases from previous cycle, find newly completed scenes and download:

```python
# Get scenes with completed upscale not yet downloaded locally
newly_completed = [
    s for s in scenes
    if s.get(f'{PREFIX}_upscale_status') == 'COMPLETED'
    and s.get(f'{PREFIX}_upscale_url')
    and not os.path.exists(f"{OUTDIR}/4k/scene_{s['display_order']:03d}_{s['id']}.mp4")
]
```

```bash
# For each newly completed scene:
mkdir -p output/<slug>/4k
curl -s "<upscale_url>" \
  -o "output/<slug>/4k/scene_<display_order:03d>_<scene_id>.mp4"
echo "Downloaded scene <display_order> → output/<slug>/4k/scene_<display_order:03d>_<scene_id>.mp4"
```

After each download, verify with:

```bash
ffprobe -v quiet -show_entries format=duration \
  -of csv=p=0 "output/<slug>/4k/scene_<display_order:03d>_<scene_id>.mp4"
# Should return a positive number (duration in seconds)
```

---

## Step 6: Stop conditions

Stop the loop when ANY of these are true:

1. **All upscaled + all downloaded** (if `--download`): `upscales_done == upscales_total AND downloads_done == upscales_total`
2. **All videos done** (if no `--download`): `videos_done == videos_total`
3. **User interrupts**: Ctrl+C or task cancelled
4. **Max iterations reached**: if `--max-iter N` was specified

On stop, send final summary:

```
mcp__telegram__reply(
  chat_id=CHAT_ID,
  text=(
    f"[<project_name>] Monitor stopped\n"
    f"Final state:\n"
    f"  Refs:      {refs_done}/{refs_total}\n"
    f"  Images:    {images_done}/{images_total}\n"
    f"  Videos:    {videos_done}/{videos_total}\n"
    f"  4K upscale:{upscales_done}/{upscales_total}\n"
    f"  Downloads: {downloads_done}/{downloads_total}\n"
    f"  TTS:       {tts_done}/{tts_total}\n"
    f"  Failed:    {failed_count}"
  )
)
```

---

## Full Poll Loop Structure

```python
import time

prev_snapshot = None
prev_all_done = False
last_change_ts = time.time()
cycle = 0
INTERVAL = 30  # override with --interval N

while True:
    cycle += 1

    # 1. Fetch all data (via curl to /tmp files)
    # 2. Compute snapshot
    snapshot = compute_snapshot()

    # 3. Detect change for stall tracking
    if snapshot != prev_snapshot:
        last_change_ts = time.time()

    # 4. Diff + emit notifications
    notifications = diff_snapshots(prev_snapshot, snapshot, last_change_ts)
    for n in notifications:
        send_telegram(CHAT_ID, f'[{project_name}]\n{n}')

    # 5. Periodic summary every 5 cycles
    if cycle % 5 == 0:
        send_telegram(CHAT_ID, build_summary(snapshot))

    # 6. Auto-download if --download
    if download_flag:
        download_new_upscales(snapshot, scenes)

    # 7. Check stop conditions
    if should_stop(snapshot, download_flag):
        send_final_summary(CHAT_ID, snapshot)
        break

    prev_snapshot = snapshot
    prev_all_done = all_done_check(snapshot)
    time.sleep(INTERVAL)
```

---

## Console Output (each cycle)

Print a compact status line to console each cycle so progress is visible:

```
[cycle 12 | 14:32:01] <project_name>
  Refs:    5/5  ✓  | Images: 23/40  | Videos: 18/40  | 4K: 10/40
  Queue:   3 pending / 2 processing | Failed: 0
  Next poll in 30s...
```

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Stall notification fires immediately | Server just restarted, processing=0 briefly | Stall threshold is 120s — brief gaps won't trigger |
| Downloads fail with 403 | GCS signed URL expired (~8h TTL) | Regenerate via `REGENERATE_IMAGE` then re-upscale |
| `media_id` missing on refs | Ref image generation failed | Check `/api/requests?status=FAILED`, resubmit `GENERATE_CHARACTER_IMAGE` |
| Scene count shows 0 | Wrong `video_id` | Verify `GET /api/videos?project_id=<PID>` returns correct video |
| Telegram notifications not sent | `mcp__telegram__reply` not available | Ensure Telegram MCP is connected in this session |

---

## Next Steps After Monitor Completes

| Scenario | Next Skill |
|----------|------------|
| All videos done, no 4K | `/fk-concat` |
| All 4K downloaded | `/fk-concat --4k` |
| Need narration first | `/fk-gen-narrator` → `/fk-concat --with-tts` |
| Upload to YouTube | `/fk-youtube-seo` → `/fk-youtube-upload` |
