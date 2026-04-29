Start the Scene Review Board web app for visual feedback on scene chains.

Usage: `/fk:review-board`

## What it does

Launches `tools/review_server.py` on port 8200, serving `tools/review_board.html` — a visual review board where you can:
- See all scenes grouped by chain
- Play scene videos inline
- Tag scenes: OK / Regen Image / Regen Video / Edit
- Write text feedback per scene
- Export feedback as JSON

## Steps

1. Kill any existing process on port 8200:
```bash
kill $(lsof -ti :8200) 2>/dev/null
```

2. Start the review server in background:
```bash
python3 tools/review_server.py &
```

3. Open in browser:
```bash
open http://localhost:8200
```

4. Confirm to user:
```
Review Board running at http://localhost:8200
- Scenes loaded from active project via API proxy (localhost:8100)
- Videos served from output/<project>/review_full/
- Feedback saves to tools/review_feedback.json
```

## After feedback

When the user shares feedback JSON (via copy or file), parse it and execute:
- `ok` → no action
- `regen-img` → submit REGENERATE_IMAGE requests
- `regen-vid` → submit REGENERATE_VIDEO requests  
- `edit` → ask user for edit prompt, submit EDIT_IMAGE requests

Use `/fk:gen-images` or `/fk:gen-videos` skills for the actual regeneration.
