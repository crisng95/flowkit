# FlowKit Common Issues

Use this file as the first stop before fixing any bug, runtime failure, or odd Flow or extension behavior.

Purpose:

- avoid fixing the same issue repeatedly with random guesses
- preserve proven fixes and known failure patterns
- make bug triage deterministic instead of lucky

## Mandatory Bug-Fix Workflow

1. Read this file before changing code for a bug.
2. Search for matching symptoms first.
3. If a matching issue exists, try the documented checks and solutions before editing code.
4. If no matching issue exists, debug normally and confirm root cause first.
5. After every bug fix, update this file.
6. A bug fix is not considered complete until this file is updated with either:
   - a new issue entry, or
   - an improved existing entry

## Required Entry Format

Every issue entry in this file must use this exact structure:

```md
## Issue: <short issue name>

### Symptoms
- ...

### Root Cause
- ...

### Common Triggers
- ...

### Solutions
- ...

### Verification
- ...
```

## Quick Checks

Run these first for most runtime issues:

```bash
curl -s http://127.0.0.1:8100/health
curl -s http://127.0.0.1:8100/api/flow/status
```

## Known Issues

## Issue: Agent disconnected

### Symptoms
- Extension shows `Agent disconnected`.
- Requests fail because the extension cannot talk to the local agent.

### Root Cause
- The FlowKit agent process is not running or not reachable.

### Common Triggers
- `python -m agent.main` was never started.
- Agent process crashed or was restarted.
- Local port binding is unavailable.

### Solutions
- Start or restart the agent with `python -m agent.main`.
- Re-check local connectivity with `GET /health`.

### Verification
- `curl -s http://127.0.0.1:8100/health` returns `extension_connected: true`.
- Extension no longer shows `Agent disconnected`.

## Issue: No token in extension

### Symptoms
- Extension shows `No token`.
- Requests that require authenticated Google Flow access do not proceed.

### Root Cause
- There is no active signed-in Google Flow browser session for the extension to use.

### Common Triggers
- User is signed out of Google Flow.
- The Flow tab has not been opened yet.
- Session expired in the browser profile.

### Solutions
- Open `https://labs.google/fx/tools/flow`.
- Sign in with the intended Google account.
- Keep the valid Flow tab open.

### Verification
- Extension stops showing `No token`.
- Flow status and authenticated requests start working again.

## Issue: Same-VM lane-02 shows Extension not connected

### Symptoms
- `http://127.0.0.1:8110/health` returns `extension_connected=false`.
- `http://127.0.0.1:18182/ready` returns `503`.
- Control job `CREATE_PROJECT` on `lane-02` fails with `Extension not connected`.

### Root Cause
- The second Chrome profile is not actually connected to the lane-02 agent and WS endpoints.

### Common Triggers
- Chrome launched without really loading the lane-02 unpacked extension.
- The lane-02 extension still points to lane-01 endpoints.
- The second Chrome profile is not signed into Google Flow yet.
- The lane-02 SSH tunnel (`8110` / `9232`) is missing or broken.

### Solutions
- Render a lane-specific unpacked extension bundle for `lane-02`.
- Verify the bundle manifest points to `http://127.0.0.1:8110` and `ws://127.0.0.1:9232`.
- Start the lane-02 SSH tunnel.
- Open the dedicated lane-02 Chrome profile.
- Confirm the unpacked extension is really loaded in `chrome://extensions`.
- Sign in with the second Google account and open `https://labs.google/fx/tools/flow`.

### Verification
- `curl -s http://127.0.0.1:8110/health` reports `extension_connected=true`.
- `curl -s http://127.0.0.1:18182/ready` returns `200`.
- A lane-02 smoke run passes `CREATE_PROJECT` instead of failing immediately.

## Issue: CAPTCHA_FAILED NO_FLOW_TAB

### Symptoms
- Request fails with `CAPTCHA_FAILED: NO_FLOW_TAB`.

### Root Cause
- The required Google Flow tab is closed, missing, or not in the expected session state.

### Common Triggers
- Flow tab was accidentally closed.
- Browser opened a different profile or session.
- The tab navigated away from Google Flow.

### Solutions
- Open one valid Google Flow tab.
- Make sure it is using the same logged-in browser profile as the extension.

### Verification
- Retried request no longer returns `CAPTCHA_FAILED: NO_FLOW_TAB`.

## Issue: MODEL_ACCESS_DENIED 403

### Symptoms
- Request fails with `403 MODEL_ACCESS_DENIED`.

### Root Cause
- The current Google Flow account tier does not allow the requested model.

### Common Triggers
- Manually selecting a model not available for the current account.
- Account tier changed or credits/tier assumptions are outdated.

### Solutions
- Use the model auto-detect path.
- Switch to a model supported by the active account tier.

### Verification
- The same request succeeds without `403 MODEL_ACCESS_DENIED`.

## Issue: Inconsistent scene images

### Symptoms
- Characters or visual elements drift between scenes.
- Generated shots do not preserve expected visual consistency.

### Root Cause
- Scene generation is missing valid reference inputs, or stored reference `media_id` values are broken.

### Common Triggers
- Referenced entities are missing `media_id`.
- Stored IDs are not UUID format.
- Scenes were generated before refs were ready.

### Solutions
- Check that every referenced entity has a valid UUID `media_id`.
- Run `/fk-fix-uuids` when IDs were saved in the wrong format.
- Regenerate scenes only after refs are valid.

### Verification
- All referenced entities have UUID `media_id` values.
- Regenerated scenes keep character and asset consistency.

## Issue: media_id starts with CAMS

### Symptoms
- Stored `media_id` starts with `CAMS...` instead of UUID format.

### Root Cause
- Wrong upstream identifier was stored instead of the UUID extracted from the final media URL or response payload.

### Common Triggers
- Parsing the wrong field from the Flow response.
- Older/broken data already saved in the database.

### Solutions
- Repair IDs with `/fk-fix-uuids`.
- Re-extract the UUID from `fifeUrl` or the correct response field.

### Verification
- `media_id` is stored as UUID format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.

## Issue: Upscale permission denied

### Symptoms
- Upscale request is denied or rejected.

### Root Cause
- Upscale requires `PAYGATE_TIER_TWO`, and the current account does not have it.

### Common Triggers
- Running upscale on a lower-tier account.
- Assuming all accounts support upscale.

### Solutions
- Use an eligible account.
- Skip upscale when the active account does not support it.

### Verification
- Upscale request succeeds on an eligible account, or the pipeline intentionally skips upscale.

## How To Update This File After A Bug Fix

After every bug fix:

1. Check whether an existing issue entry already matches.
2. If it matches, improve that entry with sharper symptoms, root cause, triggers, solutions, or verification.
3. If it does not match, add a new issue entry using the exact required format.
4. Prefer confirmed facts over guesses.
5. Write the shortest reliable fix, not every experiment that failed.

## Notes For LLMs

- Do not jump into code edits if a known issue already explains the symptom.
- Prefer fixing environment, session, account, model, or data problems before patching application code.
- Do not treat bug work as finished until `docs/common-issues.md` is updated.
- If a bug reappears, compare the current symptom against existing entries before trying a new approach.
