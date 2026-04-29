# fk:youtube-upload — Upload Video to YouTube (Shorts + Long-form)

Upload videos to YouTube with channel rule enforcement, auto-scheduling, and batch support.

Usage: `/fk:youtube-upload <channel_name> <video_path_or_dir> [--schedule "time"] [--batch] [--dry-run]`

## Step 1: Parse input and detect video type

```bash
# Single video
VIDEO="${OUTDIR}/subclips/clip_01_branded.mp4"

# Batch: directory of *_branded.mp4 files
VIDEO_DIR="${OUTDIR}/subclips/"
```

**Auto-detect Short vs Long** using `youtube/upload.py`:
```python
from youtube.upload import detect_video_type
video_type, orientation = detect_video_type(video_path)
# "short" if <61s AND vertical (9:16)
# "long" otherwise
```

## Step 2: Load channel rules

```python
from youtube.upload import load_channel_rules
rules = load_channel_rules("<channel_name>")
```

Rules file: `youtube/channels/<channel_name>/channel_rules.json`

| Rule | Short | Long | Purpose |
|------|-------|------|---------|
| `max_per_day` | 3 | 1 | YouTube algorithm favors spacing |
| `optimal_times` | 07:00, 12:00, 17:00 | 19:00 | Peak audience hours (local tz) |
| `min_gap_hours` | 4 | 4 | Min hours between any uploads |
| `avoid_hours` | 0-5 | 0-5 | Dead hours — never post |

If no `channel_rules.json` exists, warn and use defaults: 3 shorts/day, 4h gap, times 07/12/17.

## Step 3: Validate against rules

```python
from youtube.upload import validate_upload
ok, reason = validate_upload("<channel_name>", schedule_at, is_short)
if not ok:
    print(f"BLOCKED: {reason}")
    # Suggest next available slot instead
```

Validation checks (in order):
1. **Max per day** — count uploads on target date from `upload_history.json`
2. **Min gap** — time since last upload of any type
3. **Avoid hours** — schedule hour in local timezone

If validation fails, print the reason and suggest the next valid slot.

## Step 4: Schedule (single or batch)

### Single upload with explicit schedule:
```bash
/fk:youtube-upload chiensudachieu output/clip_01_branded.mp4 --schedule "2026-04-07T07:00:00+07:00"
```

### Single upload at next optimal slot:
```bash
/fk:youtube-upload chiensudachieu output/clip_01_branded.mp4
# Auto-picks next available optimal_time from channel rules
```

### Batch upload (auto-schedule all):
```python
from youtube.upload import auto_schedule
times = auto_schedule("<channel_name>", count=5, is_short=True)
# Returns: ["2026-04-07T00:00:00Z", "2026-04-07T05:00:00Z", ...]
# Respects max_per_day, optimal_times, spreads across days
```

**Batch flow:**
1. Scan `<dir>/*_branded.mp4`, sort by name
2. Call `auto_schedule()` for N files
3. Print schedule table for confirmation
4. Upload each with assigned time

## Step 5: Generate or load SEO metadata

Before uploading, ensure each video has metadata. Two modes:

### Mode A: SEO already generated (recommended)
User ran `/fk:youtube-seo` first. Provide title, description, tags as args.

### Mode B: Auto-generate per clip
If no metadata provided, run `/fk:youtube-seo` inline for each clip.

**Required metadata per upload:**
- `title` — max 65 chars (from channel rules `seo.title_max_chars`)
- `description` — with hashtags from `seo.always_include_hashtags`
- `tags` — merged with `seo.default_tags` from rules
- `category` — from `seo.default_category`

## Step 6: Upload

```python
from youtube.upload import upload_video

video_id = upload_video(
    channel_name="chiensudachieu",
    video_path="output/clip_01_branded.mp4",
    title="Title here #Shorts",
    description="Description with hashtags...",
    tags=["tag1", "tag2"],
    category_id="25",
    schedule_at="2026-04-07T00:00:00Z",  # UTC
    is_short=True,
)
```

Upload automatically:
- Adds `#Shorts` to title if `is_short=True` and not already present
- Sets privacy to `private` + `publishAt` for scheduled uploads
- Uses resumable upload with 10MB chunks (progress printed)
- Logs to `youtube/channels/<channel>/upload_history.json`

## Step 7: Verify and report

Print results to terminal:

```
YouTube Upload Complete — chiensudachieu
═══════════════════════════════════════════

 #  | Video              | Type  | Schedule (local) | Video ID    | URL
----|--------------------|----- -|------------------|-------------|----
 1  | clip_01_branded    | Short | Apr 6 17:00      | nhXfNzh12FA | youtube.com/shorts/nhXfNzh12FA
 2  | clip_02_branded    | Short | Apr 7 07:00      | abc123def   | youtube.com/shorts/abc123def
 3  | clip_03_branded    | Short | Apr 7 12:00      | ghi456jkl   | youtube.com/shorts/ghi456jkl
 ...

Upload history saved: youtube/channels/chiensudachieu/upload_history.json
```

## Step 8: `--dry-run` mode

If `--dry-run` is passed, print the schedule table WITHOUT uploading:

```
DRY RUN — No uploads will be made
═══════════════════════════════════

 #  | Video              | Type  | Schedule (local) | Validation
----|--------------------|----- -|------------------|----------
 1  | clip_01_branded    | Short | Apr 7 07:00      | OK
 2  | clip_02_branded    | Short | Apr 7 12:00      | OK
 3  | clip_03_branded    | Short | Apr 7 17:00      | OK
 4  | clip_04_branded    | Short | Apr 8 07:00      | OK

Confirm with /fk:youtube-upload chiensudachieu output/subclips/ --batch
```

## Batch Example (full workflow)

```bash
# 1. Generate SEO for all clips (run youtube-seo per clip)
# 2. Brand all clips (run brand-logo)
# 3. Upload batch with auto-schedule:

/fk:youtube-upload chiensudachieu ${OUTDIR}/subclips/ --batch --dry-run
# Review schedule, then:
/fk:youtube-upload chiensudachieu ${OUTDIR}/subclips/ --batch
```

## Channel Directory Reference

```
youtube/channels/<channel_name>/
  client_secrets.json    — OAuth2 credentials (required, local-only, gitignored)
  token.json             — Auth token (auto-created, auto-refreshes)
  channel_info.json      — Channel stats from YouTube API
  channel_rules.json     — Upload rules + SEO defaults
  <channel>_icon.png     — Brand logo for /fk:brand-logo
  upload_history.json    — Upload log (auto-created by this skill)
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "Max 3 shorts/day reached" | Already uploaded 3 today | Wait for next day or adjust rules |
| "Min gap 4h not met" | Too soon after last upload | Wait or reduce `min_gap_hours` |
| Token expired during batch | Long batch session | Token auto-refreshes; retry failed upload |
| Wrong video type detected | Edge case duration/ratio | Pass `--shorts` or `--long` to override |
| Upload quota exceeded | YouTube daily API limit | Wait 24h, YouTube resets quota at midnight PT |
