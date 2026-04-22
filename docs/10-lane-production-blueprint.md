# FlowKit 10-Lane Production Blueprint

## Goal

Build a 10-lane production system that maximizes video throughput while keeping each Google Flow account isolated and debuggable.

Primary objective:
- Produce long-form output fast by splitting work into chapters and running chapters in parallel.

Primary constraint:
- One Google Flow account must map to one isolated runtime lane.

Decision:
- **Phase 1 production architecture = 10 worker VM x 1 lane each + 1 control VM**

Reason:
- Current FlowKit runtime is single-lane by design.
- This avoids multi-account token collisions.
- This avoids per-lane port refactors inside the same VM.
- This is the fastest path to a stable production system.

## Topology

```mermaid
flowchart LR
  subgraph Control["VM-CTL"]
    API["Control API"]
    SCHED["Scheduler"]
    PG["Postgres"]
    REDIS["Redis"]
    ASM["Assembler / Final Concat"]
    DASH["Ops Dashboard"]
    R2["R2 / Object Storage"]
  end

  subgraph W1["Worker VMs"]
    L1["lane-01"]
    L2["lane-02"]
    L3["lane-03"]
    L4["lane-04"]
    L5["lane-05"]
    L6["lane-06"]
    L7["lane-07"]
    L8["lane-08"]
    L9["lane-09"]
    L10["lane-10"]
  end

  API --> PG
  API --> REDIS
  SCHED --> PG
  SCHED --> REDIS
  ASM --> PG
  ASM --> R2

  REDIS --> L1
  REDIS --> L2
  REDIS --> L3
  REDIS --> L4
  REDIS --> L5
  REDIS --> L6
  REDIS --> L7
  REDIS --> L8
  REDIS --> L9
  REDIS --> L10

  L1 --> R2
  L2 --> R2
  L3 --> R2
  L4 --> R2
  L5 --> R2
  L6 --> R2
  L7 --> R2
  L8 --> R2
  L9 --> R2
  L10 --> R2
```

## VM Layout

### Control VM

- Hostname: `fk-ctl-01`
- Size: `4 vCPU / 8 GB RAM / 80 GB SSD`
- Services:
  - `fk-control-api`
  - `fk-scheduler`
  - `fk-assembler`
  - `fk-dashboard`
  - `postgres`
  - `redis`
  - `rclone` or native R2 client

### Worker VMs

- Hostnames:
  - `fk-w01`
  - `fk-w02`
  - `fk-w03`
  - `fk-w04`
  - `fk-w05`
  - `fk-w06`
  - `fk-w07`
  - `fk-w08`
  - `fk-w09`
  - `fk-w10`
- Size per worker: `8 vCPU / 16 GB RAM / 150 GB SSD`
- Each worker runs exactly one lane.

## Lane Mapping

| Lane | VM | Flow Account | Queue | Local Runtime | Chrome Profile | Output Prefix |
|---|---|---|---|---|---|---|
| lane-01 | fk-w01 | flow-account-01 | `lane:01:jobs` | `/srv/flowkit/lane-01/runtime` | `/srv/flowkit/lane-01/chrome-profile` | `projects/.../chapter-01/` |
| lane-02 | fk-w02 | flow-account-02 | `lane:02:jobs` | `/srv/flowkit/lane-02/runtime` | `/srv/flowkit/lane-02/chrome-profile` | `projects/.../chapter-02/` |
| lane-03 | fk-w03 | flow-account-03 | `lane:03:jobs` | `/srv/flowkit/lane-03/runtime` | `/srv/flowkit/lane-03/chrome-profile` | `projects/.../chapter-03/` |
| lane-04 | fk-w04 | flow-account-04 | `lane:04:jobs` | `/srv/flowkit/lane-04/runtime` | `/srv/flowkit/lane-04/chrome-profile` | `projects/.../chapter-04/` |
| lane-05 | fk-w05 | flow-account-05 | `lane:05:jobs` | `/srv/flowkit/lane-05/runtime` | `/srv/flowkit/lane-05/chrome-profile` | `projects/.../chapter-05/` |
| lane-06 | fk-w06 | flow-account-06 | `lane:06:jobs` | `/srv/flowkit/lane-06/runtime` | `/srv/flowkit/lane-06/chrome-profile` | `projects/.../chapter-06/` |
| lane-07 | fk-w07 | flow-account-07 | `lane:07:jobs` | `/srv/flowkit/lane-07/runtime` | `/srv/flowkit/lane-07/chrome-profile` | `projects/.../chapter-07/` |
| lane-08 | fk-w08 | flow-account-08 | `lane:08:jobs` | `/srv/flowkit/lane-08/runtime` | `/srv/flowkit/lane-08/chrome-profile` | `projects/.../chapter-08/` |
| lane-09 | fk-w09 | flow-account-09 | `lane:09:jobs` | `/srv/flowkit/lane-09/runtime` | `/srv/flowkit/lane-09/chrome-profile` | `projects/.../chapter-09/` |
| lane-10 | fk-w10 | flow-account-10 | `lane:10:jobs` | `/srv/flowkit/lane-10/runtime` | `/srv/flowkit/lane-10/chrome-profile` | `projects/.../chapter-10/` |

## Worker Directory Layout

Each worker uses the same structure:

```text
/srv/flowkit/lane-XX/
├── chrome-profile/
├── extension/
├── runtime/
│   ├── flow_agent.db
│   └── output/
├── work/
├── logs/
├── env/
│   ├── lane.env
│   └── account.env
└── scripts/
    ├── start-chrome.sh
    ├── start-agent.sh
    ├── lane-runner.py
    └── upload-artifacts.sh
```

## Services Per Worker

Each worker runs four processes.

### 1. Chrome Session

- Binary: real Chrome stable, not Playwright Chromium
- Mode: headful in persistent profile
- Purpose:
  - stay logged into one Google account
  - load unpacked FlowKit extension
  - keep one Flow tab open

Recommended:
- lightweight desktop session with XFCE
- access via Tailscale + x11vnc or noVNC

Do not:
- use browser automation for login
- share one Chrome profile across multiple lanes

### 2. FlowKit Agent

- Process: `python -m agent.main`
- Bind:
  - `127.0.0.1:8100`
  - `127.0.0.1:9222`
- Storage:
  - `/srv/flowkit/lane-XX/runtime`

### 3. Lane Runner

- Process: `lane-runner.py`
- Purpose:
  - consume jobs from `lane:XX:jobs`
  - call local FlowKit REST endpoints
  - upload artifacts to object storage
  - report stage completion back to control DB

### 4. Uploader / Cleanup

- Process:
  - embedded in lane-runner or separate cron
- Purpose:
  - push chapter artifacts to R2
  - prune expired signed URL downloads
  - cap local scratch usage

## Control Plane Components

### Postgres

Use Postgres for orchestration metadata only.

Required tables:

#### `lanes`

- `lane_id`
- `vm_name`
- `status`
- `account_alias`
- `credits_last_seen`
- `tier_last_seen`
- `token_age_seconds`
- `current_chapter_id`
- `last_heartbeat_at`

#### `projects`

- `project_id`
- `project_slug`
- `source_title`
- `target_duration_seconds`
- `status`
- `created_at`

#### `chapters`

- `chapter_id`
- `project_id`
- `chapter_index`
- `title`
- `target_duration_seconds`
- `assigned_lane_id`
- `status`
- `local_flow_project_id`
- `output_uri`

#### `jobs`

- `job_id`
- `chapter_id`
- `lane_id`
- `job_type`
- `payload_json`
- `status`
- `attempt_count`
- `created_at`
- `started_at`
- `finished_at`
- `error_text`

#### `artifacts`

- `artifact_id`
- `chapter_id`
- `artifact_type`
- `local_path`
- `storage_uri`
- `size_bytes`
- `duration_seconds`
- `checksum`

### Redis

Use Redis streams or lists.

Required keys:

- `chapters:pending`
- `lane:01:jobs`
- `lane:02:jobs`
- `lane:03:jobs`
- `lane:04:jobs`
- `lane:05:jobs`
- `lane:06:jobs`
- `lane:07:jobs`
- `lane:08:jobs`
- `lane:09:jobs`
- `lane:10:jobs`
- `lane:01:dead`
- ...
- `lane:10:dead`

### Dashboard

Dashboard must show:

- lane status
- current chapter
- token age
- Flow credits
- queue depth
- active stage
- latest error
- artifact upload lag

## Work Unit Strategy

### Do not use one 45-minute project

For long-form video, the unit of work is **chapter**, not full video.

For a 45-minute target:

- 10 chapters
- each chapter 4 to 5 minutes
- each chapter about 30 to 40 scenes
- each chapter runs on one lane only

Rule:
- one chapter = one lane from start to finish

Never:
- split scenes of the same chapter across multiple lanes
- move an in-flight chapter to another lane unless explicitly failed and re-queued

## Orchestration Flow

### Stage 0. Ingest

Input:
- source script
- title
- target duration
- style/material

Output:
- project row
- chapter plan

### Stage 1. Chapter Planner

Create:
- 10 chapter records
- each chapter gets:
  - title
  - synopsis
  - scene count target
  - estimated duration

### Stage 2. Lane Assignment

Scheduler assigns:
- chapter-01 -> lane-01
- chapter-02 -> lane-02
- ...

Assignment rules:
- lane must be `idle`
- lane token age < 30 minutes or token refresh available
- credits above minimum threshold
- lane heartbeat fresh

### Stage 3. Lane Execution

For each chapter, lane-runner executes:

1. `CREATE_PROJECT`
2. `CREATE_ENTITIES`
3. `CREATE_VIDEO`
4. `CREATE_SCENES`
5. `GEN_REFS`
6. `GEN_IMAGES`
7. `GEN_VIDEOS`
8. optional `UPSCALE`
9. `CONCAT_CHAPTER`
10. `UPLOAD_ARTIFACTS`

### Stage 4. Final Assembly

When all chapter finals exist:

1. assembler downloads chapter finals from R2
2. normalizes codecs/audio
3. concatenates chapters into master output
4. uploads:
   - `master/final_45min.mp4`
   - `master/final_45min_manifest.json`

## Lane Runner Behavior

### Batch pattern inside a lane

Use FlowKit as-is for stage execution:

- refs batch
- images batch
- videos batch

Do not queue scene-by-scene one by one unless retrying a failed scene.

Recommended per lane:
- submit stage jobs in batches of 5 to 10 scenes
- let FlowKit worker respect its own cooldown / concurrency

### Retry rules

- refs: retry up to 2
- images: retry up to 2, then simplify prompt once, then retry 1
- videos: retry up to 1 for same image, then regenerate image, then retry video
- upscale: retry up to 1 only

### Failure policy

If chapter fails:

- mark chapter `FAILED`
- keep all local artifacts
- push failure summary to control DB
- do not auto-migrate to another lane immediately

Reassignment requires:
- manual or scheduler-driven clone of chapter payload
- new chapter run id

## Exact Lane Environment

Per lane worker:

```env
LANE_ID=lane-01
FLOWKIT_ROOT=/srv/flowkit/lane-01
FLOW_AGENT_DIR=/srv/flowkit/lane-01/runtime
API_HOST=127.0.0.1
API_PORT=8100
WS_HOST=127.0.0.1
WS_PORT=9222
CONTROL_API_URL=http://fk-ctl-01:8080
REDIS_URL=redis://fk-ctl-01:6379/0
POSTGRES_DSN=postgresql://fk:***@fk-ctl-01:5432/fk_control
R2_BUCKET=flowkit-output
R2_PREFIX=projects
CHROME_PROFILE_DIR=/srv/flowkit/lane-01/chrome-profile
FLOW_ACCOUNT_ALIAS=flow-account-01
```

Each lane keeps the same API/WS ports because each lane is on a different VM.

## Chrome Profile Policy

Each lane profile must contain:

- logged-in Google account for that lane only
- one pinned Flow tab
- one loaded unpacked extension
- no other unrelated extensions

Rules:

- no profile sharing
- no syncing one Google account across multiple lane profiles
- no headless login flow

Use a real browser session once for initial auth, then keep the profile persisted.

## Output Layout

### Local worker output

```text
/srv/flowkit/lane-01/runtime/output/<chapter_slug>/
├── refs/
├── images/
├── videos/
├── norm/
├── concat.txt
└── <chapter_slug>_final.mp4
```

### Central object storage

```text
projects/<project_slug>/chapter-01/refs/
projects/<project_slug>/chapter-01/images/
projects/<project_slug>/chapter-01/videos/
projects/<project_slug>/chapter-01/final.mp4
projects/<project_slug>/chapter-02/...
projects/<project_slug>/master/final_45min.mp4
projects/<project_slug>/master/manifest.json
```

## Monitoring and Alerts

Alert if any of these happen:

- lane disconnected > 2 minutes
- token age > 50 minutes
- credits below threshold
- local disk > 80%
- chapter stuck in one stage > configured SLA
- too many scene retries in one chapter

Dashboard metrics:

- per lane:
  - chapter id
  - current stage
  - remaining jobs
  - credits
  - token age
  - last success time
- global:
  - chapters completed today
  - scenes completed today
  - videos completed today
  - average chapter duration

## Security

- worker agents bind local only
- no public exposure of `8100` or `9222`
- control plane communicates to workers through queue + artifact storage, not public agent ports
- Chrome profiles stored on disk with VM-level encryption where possible
- do not store raw Google credentials in control DB
- store only account alias + lane mapping in Postgres

## Rollout Plan

### Phase 1

- deploy `VM-CTL`
- deploy `fk-w01` and `fk-w02`
- validate 2 lanes end to end
- validate chapter stickiness

### Phase 2

- scale to lanes 03-06
- validate scheduler fairness
- validate storage uploads and final assembly

### Phase 3

- scale to lanes 07-10
- run first 45-minute production run

## First 45-Minute Job Plan

Use this shape:

- project: one 45-minute master title
- chapters:
  - chapter-01 intro
  - chapter-02 setup
  - chapter-03 escalation
  - chapter-04 turn
  - chapter-05 consequence
  - chapter-06 reveal
  - chapter-07 pursuit
  - chapter-08 climax build
  - chapter-09 climax
  - chapter-10 resolution

Per chapter:
- 30 to 40 scenes
- same material
- same entity reference set
- same narrator style

## Exact Recommendation

Implement **this blueprint first**:

- `1 control VM`
- `10 worker VM`
- `1 lane per worker`
- `1 Google Flow account per lane`
- `1 Chrome profile per lane`
- `1 Redis queue per lane`
- `1 object-storage prefix per chapter`

Do not optimize to `2 lanes per VM` until:

- 10-lane production is stable
- token recovery is reliable
- scene retry rates are understood
- disk and CPU usage are measured in production

## Future Optimization

After stable production:

- move to `5 worker VM x 2 lane`
- add per-lane ports
- add per-lane extension build config
- add lane autoscaling

For now, speed comes from **stable horizontal isolation**, not clever multiplexing.

## Same-VM Lab Note

This blueprint is still the recommended production direction.

However, a same-VM lab path was validated on `hth2-box` to unblock local experimentation with a second isolated lane:

- keep `lane-01` on `8100/9222`
- add `lane-02` on `8110/9232`
- use a second runtime root
- use a second Chrome profile
- use a second unpacked extension bundle

Important:

- same-VM dual-lane is a lab/debug path, not the production recommendation
- it only becomes real isolation if the browser profile, extension endpoints, runtime dir, and Google account are all separated
- the control plane can successfully assign and execute jobs to `lane-02`, but `CREATE_PROJECT` still depends on the second browser profile being signed in and the lane-02 extension being connected

See also:

- `docs/deployment-kit/two-lane-same-vm-hth2-box-handoff.md`
- `docs/deployment-kit/worker/BOOTSTRAP-RUNBOOK.md`
