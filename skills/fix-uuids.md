Find and fix any non-UUID media_ids (CAMS... format) across all scenes and entities.

Usage: `/fix-uuids <project_id> <video_id>`

## Step 1: Check entities

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>/characters
```

For each entity, check if `media_id` is UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
If it starts with `CAMS` or doesn't match UUID pattern:
- Extract UUID from `reference_image_url` (URL contains `/image/{UUID}?...`)
- Patch: `PATCH /api/characters/<CID>` with `{"media_id": "<extracted_uuid>"}`

## Step 2: Check scenes

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

For each scene, check these fields:
- `vertical_image_media_id`
- `vertical_video_media_id`
- `vertical_upscale_media_id`
- (same for horizontal_*)

If any starts with `CAMS` or doesn't match UUID:
- Extract UUID from the corresponding URL field (`vertical_image_url`, `vertical_video_url`, etc.)
- URL format: `https://storage.googleapis.com/ai-sandbox-videofx/{type}/{UUID}?...`
- Patch: `PATCH /api/scenes/<SID>` with `{"<field>": "<extracted_uuid>"}`

## Step 3: Output

Print table of all fixes applied:
| Resource | Field | Old (CAMS...) | New (UUID) |
|----------|-------|---------------|-----------|

If no fixes needed, print "All media_ids are already UUID format."
