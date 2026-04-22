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

## Issue: Lane stays paused and never receives jobs

### Symptoms
- Control overview shows the lane as `paused` instead of `idle`.
- Scheduler keeps requeueing chapters even though the runner process exists.
- Lane `/ready` returns `503`.

### Root Cause
- The runner heartbeat now marks a lane dispatchable only when all runtime
  requirements are true:
  - agent API reachable
  - extension connected
  - Flow key/account present
- A stale heartbeat also makes the lane non-dispatchable.

### Common Triggers
- SSH tunnel is down.
- Chrome profile is open but the unpacked extension did not load.
- Second Google account is not signed in on the correct profile.
- Runner process is up, but the agent/API port is unreachable.

### Solutions
- Check lane health:
  - `./scripts/lane-service.sh status`
  - `./scripts/lane-service.sh ready`
- Check the agent directly:
  - `curl -s http://127.0.0.1:8110/health`
  - `curl -s http://127.0.0.1:8110/api/flow/status`
- Restore the matching SSH tunnel, Chrome profile, and unpacked extension for
  that lane.
- After reconnecting extension/account, wait for the next heartbeat or restart
  the runner.

### Verification
- Lane `/ready` returns `200`.
- Control overview shows the lane back in `idle`.
- New chapters can be assigned without requeue loops.

## Issue: Flow credits endpoint returns 200 with embedded auth error

### Symptoms
- Lane health may show:
  - `extension_connected=true`
  - `flow_connected=true`
  - `flow_key_present=true`
- but direct Flow operations still fail with:
  - `UNAUTHORIZED`
  - `UNAUTHENTICATED`
- `/api/flow/credits` returns a JSON `error` object instead of usable credits.

### Root Cause
- Some Flow auth failures come back as HTTP `200` with an embedded `error` payload.
- Readiness code must inspect the JSON body, not just HTTP status.

### Common Triggers
- Local Chrome profile is connected to the extension, but the Google account session is expired.
- Flow tab stayed open while login cookies became stale.
- Wrong Google account is active in that Chrome profile.

### Solutions
- Check:
  - `GET /api/flow/credits`
- If payload contains `error`, treat the lane as auth-invalid even if WS and flow key look connected.
- Re-login the correct Google account in that lane's Chrome profile.

### Verification
- `GET /api/flow/credits` returns real credits, not `error`.
- Lane health reports:
  - `flow_auth_valid=true`
  - `runner_ready=true`
- Control overview moves the lane from `paused` to `idle`.

## Issue: CONCAT or UPLOAD marked failed with UUID serialization error

### Symptoms
- `CONCAT_CHAPTER` or `UPLOAD_ARTIFACTS` job ends `dead`.
- error text contains:
  - `Object of type UUID is not JSON serializable`
- but the chapter may already have:
  - `chapter_output_uri`
  - `local_final_path`
  - `uploaded_uris`
- final file and artifact row may already exist despite job failure.

### Root Cause
- Worker stage handlers returned `chapter["id"]` as a Python `UUID` object.
- `mark_job_completed()` serializes `result_json` with `json.dumps(...)`.
- The job therefore failed after the real work had already completed.

### Common Triggers
- Host-process control smoke chapters read from Postgres via psycopg dict rows.
- `handle_concat_chapter()` returning `chapter_id` directly.
- `handle_upload_artifacts()` returning `chapter_id` directly.

### Solutions
- Convert stage result ids to strings before returning them.
- If the failure already happened live:
  - verify final file exists
  - verify artifact row exists
  - repair job status/result and chapter status in control DB
  - avoid rerunning upload blindly because that can duplicate artifacts

### Verification
- `CONCAT_CHAPTER` and `UPLOAD_ARTIFACTS` job rows end `completed`.
- `result_json.chapter_id` is a string.
- chapter ends `completed`.
- `chapter_output_uri` and artifact rows remain present.

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
- Newer branded Google Chrome builds ignore `--load-extension` and `--disable-extensions-except` unless the blocking features are disabled explicitly.
- The lane-02 extension still points to lane-01 endpoints.
- The second Chrome profile is not signed into Google Flow yet.
- The lane-02 SSH tunnel (`8110` / `9232`) is missing or broken.
- The local machine is logged out of Tailscale, so `hth2-box` is unreachable and the tunnel cannot be created.

### Solutions
- Render a lane-specific unpacked extension bundle for `lane-02`.
- Verify the bundle manifest points to `http://127.0.0.1:8110` and `ws://127.0.0.1:9232`.
- Launch Chrome with:
  - `--disable-features=DisableLoadExtensionCommandLineSwitch,DisableDisableExtensionsExceptCommandLineSwitch`
- Check `tailscale status --json` on the local machine before retrying SSH.
- If Tailscale shows `BackendState: NoState` or `You are logged out`, run `tailscale login` and complete auth first.
- Start the lane-02 SSH tunnel.
- Open the dedicated lane-02 Chrome profile.
- Confirm the unpacked extension is really loaded in `chrome://extensions`.
- Sign in with the second Google account and open `https://labs.google/fx/tools/flow`.

### Verification
- `tailscale status --json` reports `BackendState: Running`.
- `http://127.0.0.1:8110/health` reports `ws.connected=true` with `connects >= 1`.
- `curl -s http://127.0.0.1:8110/health` reports `extension_connected=true`.
- `curl -s http://127.0.0.1:18182/ready` returns `200`.
- A lane-02 smoke run passes `CREATE_PROJECT` instead of failing immediately.

## Issue: Docker agent creates root-owned runtime output

### Symptoms
- `CONCAT_CHAPTER` fails with `Permission denied` under `.../runtime/output/.../4k/...mp4`.
- The chapter output directory exists but is owned by `root:root`.
- The host lane-runner cannot write downloaded clip files into the chapter output tree.

### Root Cause
- The Dockerized FlowKit agent writes chapter output into a bind-mounted runtime directory while running as `root`, so new chapter directories become root-owned on the host.

### Common Triggers
- Running `flowkit-agent` or a same-VM lane agent container without an explicit `user`.
- Mixing a Dockerized agent with a host-process lane-runner on the same runtime path.
- Reusing a runtime tree after a root-owned chapter directory was already created.

### Solutions
- Run the agent container as the host UID:GID instead of root.
- In the worker compose kit, set `FLOWKIT_UID` / `FLOWKIT_GID` and keep:
  - `user: "${FLOWKIT_UID:-1000}:${FLOWKIT_GID:-1000}"`
- Repair existing ownership before retrying local media stages.

### Verification
- `docker inspect <agent-container>` reports `Config.User` as the host UID:GID, for example `1000:1000`.
- The host user can `touch` and remove a test file inside the affected chapter output directory.
- `CONCAT_CHAPTER` no longer fails with `Permission denied`.

## Issue: Media docker helper creates root-owned norm/final files

### Symptoms
- `norm/*.mp4` and final concat outputs are created as `root:root` even when the agent container itself runs as the host user.
- Chapter can still complete, but local media artifacts under `runtime/output/.../norm` or the final mp4 are owned by root.

### Root Cause
- `fk_worker.media` launches `docker run` for `ffmpeg` / `ffprobe` without `--user`, so the helper container writes bind-mounted files as root.

### Common Triggers
- `MEDIA_DOCKER_IMAGE` and `MEDIA_DOCKER_WORK_ROOT` are enabled.
- Local media stages (`normalize_clip`, `concat_clips`, `probe_*`) use the Docker media tool path.
- `FLOWKIT_UID` / `FLOWKIT_GID` exist but are not passed into the helper `docker run`.

### Solutions
- Add `--user ${FLOWKIT_UID}:${FLOWKIT_GID}` to the helper `docker run` command.
- Keep `FLOWKIT_UID` / `FLOWKIT_GID` present in `lane.env`.
- Repair ownership of old output trees once after patching.

### Verification
- Media helper tests assert the Docker command includes `--user 1000:1000`.
- New `norm/*.mp4` and final concat outputs are created as the host user, not root.

## Issue: CONCAT_CHAPTER crashes because storage helper rejects chapter_output_uri

### Symptoms
- Local ffmpeg concat finishes and writes the final mp4.
- Then `CONCAT_CHAPTER` crashes with:
  - `TypeError: update_chapter_state() got an unexpected keyword argument 'chapter_output_uri'`

### Root Cause
- `fk_worker.stages.handle_concat_chapter()` passes `chapter_output_uri=...`, but `fk_worker.storage.update_chapter_state()` did not accept that keyword.

### Common Triggers
- A concat run reaches the DB update step after producing the final chapter file.
- The worker code is newer than the storage helper signature.

### Solutions
- Extend `update_chapter_state()` to support `chapter_output_uri`.
- Verify the `chapters` table column exists and write to it together with metadata updates.

### Verification
- Worker tests cover `update_chapter_state(..., chapter_output_uri=...)`.
- `chapters.chapter_output_uri` is populated after local concat finishes.

## Issue: GEN_VIDEOS marked completed even when a scene video failed

### Symptoms
- `GEN_VIDEOS` is marked `completed`.
- A later `CONCAT_CHAPTER` fails with `Scene <id> has no downloadable video source`.
- One or more scenes show `vertical_video_status=FAILED` or are missing video URLs.

### Root Cause
- The worker stage trusted batch request completion without re-checking scene-level output availability, so the pipeline advanced past the real failure point.

### Common Triggers
- One request in the batch fails while other scenes succeed.
- Scene rows end up with `*_video_status=FAILED` and no matching downloadable URL.
- The stage only waits for request records and does not validate final scene fields.

### Solutions
- Treat any non-`COMPLETED` request in the batch as a hard failure.
- After `GEN_IMAGES`, `GEN_VIDEOS`, or `UPSCALE`, re-read scene rows and verify the expected output URL plus `*_status=COMPLETED`.
- Fail the stage immediately instead of letting the pipeline drift into concat/upload.

### Verification
- Worker tests cover failed request records and missing scene video URLs.
- A scene with `vertical_video_status=FAILED` now raises during `GEN_VIDEOS`, not during `CONCAT_CHAPTER`.

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
