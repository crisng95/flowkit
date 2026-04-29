# Workspace Guard (FlowKit)

## Source of truth
- Canonical workspace for development/runtime: `/Volumes/DATA/Apps/FlowKit`
- Do all code changes, builds, and runtime checks in this root.

## Duplicate folder note
- Folder `/Volumes/DATA/Apps/FlowKit/flowkit` is a duplicate/legacy mirror.
- Do **not** apply fixes there unless explicitly requested.

## Quick verification before any fix
1. `pwd` must be `/Volumes/DATA/Apps/FlowKit`
2. Running processes must point to this root:
   - Electron cwd: `/Volumes/DATA/Apps/FlowKit/desktop`
   - Agent cwd: `/Volumes/DATA/Apps/FlowKit`
3. Health check must come from this runtime:
   - `curl -s http://127.0.0.1:8100/health`

