# fk:switch-project — Switch Active Project

Switch the active project so all skills automatically target the correct project without needing explicit `project_id`.

Usage:
- `/fk:switch-project` — list projects and switch interactively
- `/fk:switch-project <project_id>` — switch to a specific project by ID
- `/fk:switch-project clear` — clear active project (revert to most-recent fallback)

---

## Step 1: List Available Projects

```bash
curl -s http://127.0.0.1:8100/api/projects | python3 -c "
import sys, json
projects = json.load(sys.stdin)
print(f'{'#':>3}  {'Name':40} {'ID':36}  {'Status':8}  Material')
print('-' * 110)
for i, p in enumerate(projects, 1):
    active = ''
    print(f'{i:>3}  {p[\"name\"][:40]:40} {p[\"id\"]:36}  {p.get(\"status\",\"?\"):8}  {p.get(\"material\",\"?\")}')
"
```

## Step 2: Show Current Active Project

```bash
curl -s http://127.0.0.1:8100/api/active-project | python3 -c "
import sys, json
ap = json.load(sys.stdin)
if ap.get('project_id'):
    print(f'Active: {ap[\"project_name\"]} ({ap[\"project_id\"][:8]}...)')
    print(f'Video:  {ap.get(\"video_id\", \"none\")}')
    print(f'Source: {ap[\"source\"]}')
else:
    print('No active project set')
"
```

## Step 3: Switch Project

If the user provided a `project_id` argument, use it directly. Otherwise, present an `AskUserQuestion` selector with up to 4 projects (most recent first, showing name + material + short ID). After user picks, switch:

```bash
curl -s -X PUT http://127.0.0.1:8100/api/active-project \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<PROJECT_ID>"}'
```

Use `AskUserQuestion` with options like:
- label: project name
- description: `#N · material · project_id_short`

If more than 4 projects exist, show the 4 most recent and let the user type "Other" for older ones.

## Step 4: Verify

```bash
curl -s http://127.0.0.1:8100/api/active-project | python3 -c "
import sys, json
ap = json.load(sys.stdin)
print(f'Switched to: {ap[\"project_name\"]}')
print(f'Project ID:  {ap[\"project_id\"]}')
print(f'Video ID:    {ap.get(\"video_id\", \"none\")}')
"
```

## Step 5: Clear (optional)

To revert to the default behavior (most recently created project):

```bash
curl -s -X DELETE http://127.0.0.1:8100/api/active-project
```

---

## How It Works

- `PUT /api/active-project` sets the active project (persists across server restarts)
- `GET /api/active-project` returns the active project, or falls back to the most recently created
- Skills that accept optional `project_id` should use `GET /api/active-project` when none is provided
- Statusline reads from this endpoint to show the correct project name

## Notes

- Switching project does NOT affect running requests — only future operations
- If the active project is deleted, the endpoint auto-clears and falls back to most recent
- The `source` field tells you whether the project was explicitly set (`explicit`) or auto-detected (`fallback_most_recent`)
