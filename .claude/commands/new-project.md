Create a new Google Flow video project. Ask the user for:

1. **Project name** and **story** (brief plot summary)
2. **Characters** — name + visual description (appearance only, not personality)
3. **Locations** — name + visual description of key places
4. **Visual assets** — name + visual description of key props/objects
5. **Number of scenes** and **orientation** (VERTICAL or HORIZONTAL)

Then execute:

## Step 1: Create project with all entities

```bash
curl -X POST http://127.0.0.1:8100/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "...", "description": "...", "story": "...", "characters": [
    {"name": "...", "entity_type": "character", "description": "..."},
    {"name": "...", "entity_type": "location", "description": "..."},
    {"name": "...", "entity_type": "visual_asset", "description": "..."}
  ]}'
```

Save the returned `project_id`.

## Step 2: Create video

```bash
curl -X POST http://127.0.0.1:8100/api/videos \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<PID>", "title": "...", "display_order": 0}'
```

Save the returned `video_id`.

## Step 3: Create scenes

For each scene, write a prompt that describes **action + environment + mood** only. Reference entities by name. Never describe character appearance.

- Scene 1: `chain_type: "ROOT"`
- Scene 2+: `chain_type: "CONTINUATION"`, `parent_scene_id: "<previous_scene_id>"`
- `character_names`: list ALL entities that should appear (characters + locations + assets)

```bash
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{"video_id": "<VID>", "display_order": N, "prompt": "...", "character_names": [...], "chain_type": "ROOT|CONTINUATION", "parent_scene_id": "..."}'
```

## Output

Print a summary table:
- Project ID, Video ID
- All entities with names and types
- All scenes with prompts (truncated) and chain type
- Next step: "Run /gen-refs to generate reference images"
