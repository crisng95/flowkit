Generate reference images for all entities in a project.

Usage: `/gen-refs <project_id>`

If no project_id provided, ask the user or list projects via `GET /api/projects`.

## Step 1: Check health

```bash
curl -s http://127.0.0.1:8100/health
```
Must have `extension_connected: true`. Abort if not.

## Step 2: Get entities

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

Filter to entities that do NOT yet have `media_id` (UUID format). Skip ones already done.

## Step 3: Create requests ONE AT A TIME

For each entity missing `media_id`, create a request and **wait for it to complete** before creating the next one. This avoids API spam.

```bash
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{"type": "GENERATE_CHARACTER_IMAGE", "character_id": "<CID>", "project_id": "<PID>"}'
```

Poll every 10s:
```bash
curl -s http://127.0.0.1:8100/api/requests/<RID>
```

Wait for `status: "COMPLETED"` or `"FAILED"`. Max wait: 120s per entity.

## Step 4: Verify

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

Print results table:
| Entity | Type | media_id | Status |
|--------|------|----------|--------|

All entities must have `media_id` in UUID format. If any failed, report and suggest retry.

Print: "All references ready. Run /gen-images <PID> <VID> to generate scene images."
