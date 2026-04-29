Show live GLA status in Claude Code statusline.

Usage: `/fk:dashboard`

The GLA statusline shows real-time project status at the bottom of Claude Code:

```
Opus 4.6 (1M ctx) ctx:14% rl:18%/5h 67%/7d | GLA: ✓ext Operation Hormu 40sc img:40 vid:40 4K:26 ▶0/5
```

## What it shows

- **OMC info**: model, context usage, rate limits (5h & 7d)
- **GLA info**: extension status, project name, scene count, image/video/4K progress, worker slots

## Setup

Statusline is auto-configured by `bash setup.sh`. To manually configure:

```bash
# In .claude/settings.local.json, add:
{
  "statusLine": {
    "type": "command",
    "command": "<project_root>/scripts/statusline.sh"
  }
}
```

Requires `jq` and `curl` installed.
