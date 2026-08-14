# Characters (r2v via @mention) — verified 14/08/2026

Flow's web UI replaced "ingredients" with a **Characters** system. Character
references work server-side: mention `@<character_name>` in any prompt and the
server resolves the entity automatically. On tier TWO the video still renders
on `veo_3_1_i2v_lite_low_priority` (0 credits) — **no `veo_3_1_r2v_fast_*`
model is needed** (that model is account-gated: 403/404 on this account).

## How it works (request chain captured from the web UI)

1. `POST /v1/flow/uploadImage` — upload a portrait image
   `{"clientContext":{"projectId":...,"tool":"PINHOLE"},"imageBytes":"<b64>"}`
2. `flow.createEntity` (tRPC) — create an empty entity
   `{"json":{"projectId":...,"collectionId":null}}` → `entityId`
3. `flow:copyProjectMedia` (tRPC) — attach the image to the entity
   `{"json":{"mediaId":...,"destinationProjectId":...,"destinationMediaContext":{"entityContext":{"entityId":...,"characterSlot":{"imageReferenceIndex":0}}}}}`
4. Generate video: prompt contains `@Mai ...` — server resolves the entity.

## API

The fork adds a scriptable endpoint (no browser needed):

```
POST /api/flow/create-character
{"project_id": "...", "media_id": "...", "image_reference_index": 0}
→ {"entityId": "...", "copy": {...}}
```

Then any `POST /api/flow/generate-video` with a prompt containing `@<name>`
uses the character reference automatically.

## Naming the character

`flow.createEntity` + `copyProjectMedia` create an "Untitled Character".
The UI names it via `character.saveCharacter` (tRPC). Until that endpoint is
reverse-engineered, open the Flow tab once, rename the character there, and
use that name in prompts. The character persists per project.

## Pipeline tip (KOL Mai case study)

- 1 anchor portrait → `create-character` once per project
- Every shot prompt starts with `@Mai` → consistent face, 0 extra credits
- Start/end frames still work as usual (start_image_media_id / end_image_media_id)
