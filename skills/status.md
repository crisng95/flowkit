Show full status dashboard for a project.

Usage: `/status <project_id>` or `/status` (lists all projects)

## If no project_id: list all projects

```bash
curl -s http://127.0.0.1:8100/api/projects
```

Print table: ID | Name | Tier | Status

## With project_id: full dashboard

### 1. Server health
```bash
curl -s http://127.0.0.1:8100/health
```

### 2. Project info
```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>
```

### 3. Entities (references)
```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

Print table:
| Entity | Type | media_id | ref_url | Ready? |
|--------|------|----------|---------|--------|

### 4. Videos
```bash
curl -s "http://127.0.0.1:8100/api/videos?project_id=<PID>"
```

### 5. For each video — scenes
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Print table (sorted by display_order):
| # | Prompt (50 chars) | Refs | Image | Video | Upscale |
|---|-------------------|------|-------|-------|---------|

Where Image/Video/Upscale show: `OK`, `PENDING`, `PROCESSING`, `FAILED`

### 6. Pending/processing requests
```bash
curl -s http://127.0.0.1:8100/api/requests/pending
```

### 7. Summary

Print counts: X/Y refs ready, X/Y images done, X/Y videos done, X/Y upscaled.

Suggest next action:
- If refs missing → "Run /gen-refs <PID>"
- If images missing → "Run /gen-images <PID> <VID>"
- If videos missing → "Run /gen-videos <PID> <VID>"
- If all done → "Run /concat <VID>"
