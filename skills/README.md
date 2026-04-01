# Skills — Google Flow Agent

Workflow skills for AI agents and humans. Each skill is a step-by-step recipe.

## Pipeline (run in order)

| # | Skill | File | Description |
|---|-------|------|-------------|
| 1 | new-project | [new-project.md](new-project.md) | Create project + entities + video + scenes |
| 2 | gen-refs | [gen-refs.md](gen-refs.md) | Generate reference images for all entities |
| 3 | gen-images | [gen-images.md](gen-images.md) | Generate scene images with character refs |
| 4 | gen-videos | [gen-videos.md](gen-videos.md) | Generate videos from scene images |
| 5 | concat | [concat.md](concat.md) | Download + merge all scene videos |

## Advanced Video

| Skill | File | Description |
|-------|------|-------------|
| gen-chain-videos | [gen-chain-videos.md](gen-chain-videos.md) | Auto start+end frame chaining for smooth transitions |
| insert-scene | [insert-scene.md](insert-scene.md) | Multi-angle shots, cutaways, close-ups |
| creative-mix | [creative-mix.md](creative-mix.md) | Analyze story + suggest all techniques combined |

## Utilities

| Skill | File | Description |
|-------|------|-------------|
| status | [status.md](status.md) | Full project dashboard + next action |
| fix-uuids | [fix-uuids.md](fix-uuids.md) | Repair any CAMS... media_ids to UUID format |

## For Claude Code users

These skills are also available as `/slash-commands` via `.claude/commands/`.
