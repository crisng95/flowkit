# Two-Lane Same-VM Handoff: `hth2-box`

## Goal

Continue from the current hybrid demo and implement **2 real lanes on the same VM `hth2-box`**.

Target shape:

- `lane-01` stays on `127.0.0.1:8100` + `127.0.0.1:9222`
- `lane-02` gets its own runtime on `127.0.0.1:8110` + `127.0.0.1:9232`
- each lane has:
  - separate runtime dir
  - separate worker dir
  - separate Chrome profile
  - separate extension build/config
  - separate Google account session

## Current status after April 22, 2026 update

### Repo changes now in place

- extension now reads lane-specific endpoints from `manifest.json` `flowkit` config
- new render utility exists:
  - `docs/deployment-kit/worker/scripts/render-extension-bundle.py`
- new render helper exists:
  - `docs/deployment-kit/worker/fk_worker/extension_bundle.py`
- `bootstrap-lane.sh` now supports:
  - custom `DEPLOY_ROOT`
  - custom API / WS / runner-health ports
  - empty `SUDO_BIN` for non-root host demo bootstrap
  - missing `tests/` and missing `systemd/` source dirs

### Local Windows state

- lane-02 unpacked extension rendered to:
  - `C:\temp\flowkit-extension-unpacked-lane-02`
- lane-02 Chrome profile root created:
  - `C:\temp\flowkit-real-chrome-lane-02\UserData`
- lane-02 tunnel process started locally:
  - `ssh -N -L 8110:127.0.0.1:8110 -L 9232:127.0.0.1:9232 hth2-box`
- lane-02 Chrome was launched with the new profile and extension path

Important blocker still present:

- VM `8110/health` still reports `extension_connected=false`
- this means the lane-02 extension is not yet handshaking with the VM agent
- likely causes:
  - Chrome ignored `--load-extension`
  - unpacked extension still needs manual load in `chrome://extensions`
  - second Google account not yet signed in on the new profile

### Current VM state

- lane-02 worker root exists:
  - `/home/hth2/flowkit-worker-demo-lane-02`
- lane-02 env is prepared for:
  - API `8110`
  - WS `9232`
  - runner health `18182`
- second agent container is running:
  - container name: `flowkit-lane-02-agent`
- lane-02 agent health:
  - `http://127.0.0.1:8110/health`
  - reachable
  - `extension_connected=false`
- lane-02 runner health:
  - `http://127.0.0.1:18182/health`
  - reachable
  - `ready` still `503` because API is reachable but extension/token is not
- control services:
  - `fk_control.api` running on `18080`
  - `fk_control.scheduler` running
- demo Postgres/Redis stack is up via:
  - `control-postgres-1`
  - `control-redis-1`

### Control-plane state

- `seed-lanes.sql` was applied
- control overview now shows:
  - `lane_count=10`
  - `offline=9`
  - `idle=1`
- only `lane-02` is left `idle`
- other lanes are forced `offline` so the smoke project pins to `lane-02`

### Smoke run already exercised

Smoke project:

- title: `Lane 02 Single Chapter Smoke`
- project id: `6be54715-db27-4280-86c3-e3af1be814dd`
- chapter id: `b70c9bf7-45d0-4b87-a98e-5e08e36d6ca8`

Observed result:

- chapter assigned to `lane-02`
- `CREATE_PROJECT` job was actually attempted on `lane-02`
- `CREATE_PROJECT` failed after retries with:
  - `POST /api/projects failed: Extension not connected — cannot create project on Google Flow`
- downstream jobs were marked dead because the chapter failed at the first real stage

This proves:

- control scheduler is routing into `lane:02:jobs`
- lane-02 runner is alive and consuming
- lane-02 agent on `8110` is reachable
- remaining blocker is the local lane-02 browser/account handshake, not the same-VM worker layout

## Current repo state

Important local changes already made in repo:

- control-plane scaffold + tests
- worker scaffold + tests
- dashboard queue cleanup
- worker Docker-media fallback for `ffmpeg/ffprobe`
- local artifact fallback for upload
- clearer Flow create-project error handling

Relevant files:

- `docs/deployment-kit/control/fk_control/dashboard.py`
- `docs/deployment-kit/control/fk_control/planning.py`
- `docs/deployment-kit/control/fk_control/scheduler.py`
- `docs/deployment-kit/control/fk_control/storage.py`
- `docs/deployment-kit/control/scripts/*.sh`
- `docs/deployment-kit/worker/fk_worker/client.py`
- `docs/deployment-kit/worker/fk_worker/config.py`
- `docs/deployment-kit/worker/fk_worker/media.py`
- `docs/deployment-kit/worker/fk_worker/runner.py`
- `docs/deployment-kit/worker/fk_worker/stages.py`
- `docs/deployment-kit/worker/scripts/*.sh`
- `agent/api/projects.py`

Repo working tree note:

- `agent/api/projects.py` is modified
- `tests/unit/test_projects_api.py` is untracked
- most `docs/deployment-kit/` content is still untracked

## Current VM state on `hth2-box`

### Disk / RAM

- root filesystem already expanded from ~24G to ~48G
- current root free space is healthy again
- OpenClaw and related images/volumes were removed

### Running services now

At last check:

- `flowkit` Coolify runtime container is up
- `coolify` core containers are up
- demo `fk_control.api` is currently **down**
- demo `fk_control.scheduler` is currently **down**
- demo `lane-01` worker runner is currently **down**

Health snapshot at last check:

- `http://127.0.0.1:8100/health` → `extension_connected=false`
- `http://127.0.0.1:8100/api/flow/status` → `connected=false`, `flow_key_present=true`
- `http://127.0.0.1:18080/health` → refused
- `http://127.0.0.1:18181/health` → refused

Interpretation:

- FlowKit agent is up on VM
- browser extension is not currently connected because the local Chrome/tunnel session is not currently active
- demo control/worker host processes need restart before continuing

## What was proven already

### Lane-01 full pipeline

One real chapter was completed end-to-end on `lane-01`:

- `CREATE_PROJECT`
- `CREATE_ENTITIES`
- `CREATE_VIDEO`
- `CREATE_SCENES`
- `GEN_REFS`
- `GEN_IMAGES`
- `GEN_VIDEOS`
- `CONCAT_CHAPTER`
- `UPLOAD_ARTIFACTS`

The upload path used local fallback, not real R2.

Chapter:

- `Lane 01 Single Chapter v12`

Final file:

- `/home/hth2/flowkit-worker-demo/runtime/output/lane_01_single_chapter_v12_chapter_01/lane_01_single_chapter_v12_final_reencode.mp4`

Artifact DB record points to:

- `file:///home/hth2/flowkit-worker-demo/runtime/output/lane_01_single_chapter_v12_chapter_01/lane_01_single_chapter_v12_final_reencode.mp4`

### Dashboard cleanup

- `/overview` raw queues are clean after `clean-queue-history.sh`
- dashboard default queue view hides zero-depth noise

## Hard blockers for 2 lanes on the same VM

### 1. Extension is hardcoded to lane-01 ports

Current extension uses fixed endpoints:

- WS: `ws://127.0.0.1:9222`
- callback HTTP: `http://127.0.0.1:8100/api/ext/callback`
- manifest host permission includes `http://127.0.0.1:8100/*`

Files:

- `extension/background.js`
- `extension/manifest.json`

Implication:

- to run lane-02 on the same machine, a second extension copy or parameterized extension config is required

### 2. Current local browser setup only represents one account/profile

Known local profile path:

- `C:\temp\flowkit-real-chrome\UserData`

Known unpacked extension path:

- `C:\temp\flowkit-extension-unpacked`

Implication:

- lane-02 needs a second Chrome profile and second Google account session

### 3. Current app/runtime design is single-lane by default

To make same-VM dual lane real, lane-02 needs:

- separate `FLOW_AGENT_DIR`
- separate API/WS ports
- separate worker health port
- separate worker root/output/logs

## Recommended implementation plan for next session

### Preferred same-VM lane-02 shape

Keep lane-01 unchanged.

Add lane-02 with:

- API: `127.0.0.1:8110`
- WS: `127.0.0.1:9232`
- runner health: `127.0.0.1:18182`
- worker root: `/home/hth2/flowkit-worker-demo-lane-02`
- runtime dir: `/home/hth2/flowkit-worker-demo-lane-02/runtime`
- profile dir on local Windows:
  - `C:\temp\flowkit-real-chrome-lane-02\UserData`
- extension dir on local Windows:
  - `C:\temp\flowkit-extension-unpacked-lane-02`

### Recommended technical moves

1. Parameterize extension endpoints or create a lane-02 extension copy
2. Add lane-02 worker env and scripts
3. Add lane-02 host-process runner on VM
4. Add second local SSH tunnel:
   - `8110 -> 8110`
   - `9232 -> 9232`
5. Launch second Chrome profile with second extension + second Google account
6. Seed/control-test a single-chapter project pinned to lane-02

## Exact next action now

1. On Windows, open the lane-02 Chrome profile.
2. Go to `chrome://extensions`.
3. Confirm `C:\temp\flowkit-extension-unpacked-lane-02` is actually loaded.
4. Sign in with the second Google account in that lane-02 profile.
5. Open `https://labs.google/fx/tools/flow`.
6. Verify:
   - `http://127.0.0.1:8110/health` shows `extension_connected=true`
   - `http://127.0.0.1:18182/ready` returns `200`
7. Re-run a one-chapter smoke project on control API.

Once step 6 turns green, the same lane-02 runtime should be able to pass `CREATE_PROJECT` for real.

## Exact next-session prompt

Use this in the next Codex session:

```text
Continue in repo F:\\vm201 Coolify\\flowkit.

Read first:
- F:\\vm201 Coolify\\flowkit\\README.md
- F:\\vm201 Coolify\\flowkit\\docs\\10-lane-production-blueprint.md
- F:\\vm201 Coolify\\flowkit\\docs\\deployment-kit\\two-lane-same-vm-hth2-box-handoff.md

Goal:
- implement 2 real lanes on the same VM hth2-box
- keep lane-01 as-is on 8100/9222
- add lane-02 on 8110/9232
- do NOT fake multi-lane by reusing one profile/account/runtime

Current facts to respect:
- lane-01 already proved end-to-end with local artifact fallback
- control/dashboard cleanup is already done
- current VM root is 48G with healthy free space
- control API, scheduler, and lane-01 runner are currently down and may need restart
- current agent on VM is still on 8100/9222
- extension is hardcoded to 8100/9222 in extension/background.js and extension/manifest.json
- current local profile is C:\\temp\\flowkit-real-chrome\\UserData
- current local extension is C:\\temp\\flowkit-extension-unpacked

Required implementation direction:
1. Create a proper lane-02 runtime/worker layout:
   - /home/hth2/flowkit-worker-demo-lane-02
   - API 8110
   - WS 9232
   - health 18182
2. Add a lane-02 extension strategy:
   - either parameterize the extension endpoints cleanly
   - or generate a second unpacked extension copy for lane-02
3. Add second local Chrome profile guidance/launch command for lane-02
4. Add second SSH tunnel command for lane-02
5. Restart/verify control API + scheduler + lane-01 if needed
6. Bring up lane-02 worker and prove a single chapter can at least reach CREATE_PROJECT with the second account

Important:
- use TDD for code changes where practical
- verify with commands, don’t just assume
- keep /overview raw contract stable unless absolutely necessary
- preserve lane-01 working path

Target success for this session:
- lane-02 runtime and worker are actually launchable
- local lane-02 browser/extension wiring is ready
- one single-chapter run assigned to lane-02 is exercised
```

## Recommended first commands next session

On VM:

- check/restart:
  - `/home/hth2/flowkit-control-demo/start-control-api.sh`
  - `/home/hth2/flowkit-control-demo/start-scheduler.sh`
- check lane-01 runner:
  - `/home/hth2/flowkit-worker-demo/scripts/run-worker-demo.sh`

On Windows:

- restore lane-01 tunnel if needed:
  - `ssh -N -L 8100:127.0.0.1:8100 -L 9222:127.0.0.1:9222 hth2-box`
- plan second tunnel:
  - `ssh -N -L 8110:127.0.0.1:8110 -L 9232:127.0.0.1:9232 hth2-box`

## Notes

- If same-VM two-lane starts getting messy, stop and explicitly compare:
  - same VM dual lane
  - second VM for lane-02
- But the requested direction for next session is to pursue same-VM lane-02 first.
