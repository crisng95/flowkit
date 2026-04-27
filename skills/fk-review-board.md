Start the Scene Review Board web app for visual feedback on scene chains.

Usage: `/fk-review-board [<video_id>]`

## What it does

Launches `tools/review_server.py` on port 8200, serving `tools/review_board.html` — a visual review board where you can:
- See all scenes grouped by chain
- Play scene videos inline
- Tag scenes: OK / Regen Image / Regen Video / Edit
- Write text feedback per scene
- Export feedback as JSON

The board loads scenes for `?video_id=<id>` query param (or a hardcoded fallback inside the HTML). Always pass the current project's `video_id` so the board reflects what the user is working on, not a stale default.

## Steps

### 1. Resolve current `video_id`

Priority order — stop at first match:

a. **Explicit arg** — if user passed `<video_id>` to the skill, use that.

b. **Active project** — read `GET /api/active-project`:
```bash
ACTIVE=$(curl -s http://127.0.0.1:8100/api/active-project)
VID=$(echo "$ACTIVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('video_id',''))")
PNAME=$(echo "$ACTIVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('project_name','(none)'))")
```

c. **No active project / no video_id** — list recent projects and ask user to pick:
```bash
curl -s http://127.0.0.1:8100/api/projects?limit=10 | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    print(f\"  {p['id']}  {p.get('name','-')}\")"
```
Then `PUT /api/active-project` with the chosen `project_id` and re-resolve.

If still empty, abort: "No active project. Run /fk-switch-project <PID> first."

### 2. Kill any existing process on port 8200
```bash
kill $(lsof -ti :8200) 2>/dev/null
```

### 3. Start the review server in background
```bash
python3 tools/review_server.py &
```

### 4. Open the board with explicit `video_id` query param
```bash
open "http://localhost:8200?video_id=${VID}"
```

The query param overrides the HTML's hardcoded default, so the board always loads the project resolved in step 1.

### 5. Confirm to user
```
Review Board running at http://localhost:8200?video_id=<VID>
- Project: <project_name>
- Video ID: <VID>
- Scenes loaded via API proxy (localhost:8100)
- Videos served from output/<project>/review_full/ (fallback: raw/)
- Feedback saves to tools/review_feedback.json
```

## After feedback

When the user shares feedback JSON (via copy or file), parse it and execute:
- `ok` → no action
- `regen-img` → submit REGENERATE_IMAGE requests
- `regen-vid` → submit REGENERATE_VIDEO requests
- `edit` → ask user for edit prompt, submit EDIT_IMAGE requests

Use `/fk-gen-images` or `/fk-gen-videos` skills for the actual regeneration.
