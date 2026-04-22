# Control Plane Runbook

## Goal

Bring up the control plane locally or on `fk-ctl-01` with minimum manual steps.

## Files used

- [docker-compose.control.yml](/F:/vm201 Coolify/flowkit/docs/deployment-kit/control/docker-compose.control.yml)
- [Dockerfile](/F:/vm201 Coolify/flowkit/docs/deployment-kit/control/Dockerfile)
- [requirements.txt](/F:/vm201 Coolify/flowkit/docs/deployment-kit/control/requirements.txt)
- [postgres-schema.sql](/F:/vm201 Coolify/flowkit/docs/deployment-kit/control/postgres-schema.sql)
- [seed-lanes.sql](/F:/vm201 Coolify/flowkit/docs/deployment-kit/control/seed-lanes.sql)

## First bootstrap

```bash
cd docs/deployment-kit/control
cp .env.control.example .env.control
```

Edit:

- `POSTGRES_PASSWORD`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

Then:

```bash
chmod +x scripts/bootstrap-control.sh
./scripts/bootstrap-control.sh
```

## Seed lane metadata

```bash
chmod +x scripts/seed-lanes.sh
./scripts/seed-lanes.sh
```

## Reset demo state

Use this before re-running a control-plane demo from scratch.

### Compose mode

```bash
chmod +x scripts/reset-control-state.sh
./scripts/reset-control-state.sh
```

### Custom container mode

Useful when Postgres and Redis are not running under the local compose project name, for example the `hth2-box` demo:

```bash
POSTGRES_CONTAINER=fk-demo-postgres \
REDIS_CONTAINER=fk-demo-redis \
POSTGRES_DB=fk_control \
POSTGRES_USER=fk \
./scripts/reset-control-state.sh
```

What it resets:

- deletes project, chapter, job, artifact, and heartbeat rows
- returns all lanes to `idle`
- clears Redis keys:
  - `chapters:pending`
  - `lane:XX:jobs`
  - `lane:XX:dead`
  - `lane:XX:heartbeat`

## Clean queue history only

Use this when you want to keep Postgres rows and completed chapter/job history,
but remove noisy Redis stream history from `/overview`.

```bash
chmod +x scripts/clean-queue-history.sh
./scripts/clean-queue-history.sh
```

Behavior:

- deletes `chapters:pending` only when backlog is `0`
- deletes `lane:XX:jobs` only when backlog is `0`
- deletes `lane:XX:dead` when depth is greater than `0`
- keeps heartbeat keys unless `INCLUDE_HEARTBEATS=1`

Force cleanup of active queues only if you really mean it:

```bash
FORCE=1 ./scripts/clean-queue-history.sh
```

## Host-process mode

Useful for lightweight demos where Postgres and Redis stay in containers, but API and scheduler run directly on the host Python runtime.

### Start API

```bash
chmod +x scripts/start-control-api.sh
./scripts/start-control-api.sh
```

### Start scheduler

```bash
chmod +x scripts/start-scheduler.sh
./scripts/start-scheduler.sh
```

### One-command demo flow

This starts host-process API + scheduler, resets state, creates a demo project, then prints `/overview`.

```bash
chmod +x scripts/run-control-demo.sh
./scripts/run-control-demo.sh
```

By default the script waits until:

- all chapters are assigned
- expected job rows exist
- `chapters:pending` backlog is `0`

If you want the immediate snapshot only:

```bash
WAIT_FOR_ASSIGNMENTS=0 ./scripts/run-control-demo.sh
```

For a remote demo like `hth2-box`:

```bash
POSTGRES_CONTAINER=fk-demo-postgres \
REDIS_CONTAINER=fk-demo-redis \
POSTGRES_DB=fk_control \
POSTGRES_USER=fk \
CONTROL_API_URL=http://127.0.0.1:18080 \
CONTROL_API_BIND=0.0.0.0 \
CONTROL_API_PORT=18080 \
POSTGRES_DSN='postgresql://fk:***@127.0.0.1:15432/fk_control' \
REDIS_URL='redis://127.0.0.1:16379/0' \
./scripts/run-control-demo.sh \
  "Fresh 10 Lane Demo" \
  2700 \
  10 \
  realistic \
  "Test split into chapters"
```

## Verify

### Compose services

```bash
docker compose -f docker-compose.control.yml ps
```

### Control API

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/lanes
curl http://127.0.0.1:8080/projects
```

### Create a demo project

```bash
chmod +x scripts/create-demo-project.sh
./scripts/create-demo-project.sh
```

Custom demo target:

```bash
CONTROL_API_URL=http://127.0.0.1:18080 \
./scripts/create-demo-project.sh \
  "Fresh 10 Lane Demo" \
  2700 \
  10 \
  realistic \
  "Test split into chapters"
```

Expected:

- 1 project row in Postgres
- 10 chapter rows
- 10 messages added to `chapters:pending`

### Redis inspection

```bash
redis-cli XLEN chapters:pending
redis-cli XRANGE chapters:pending - +
redis-cli XPENDING chapters:pending scheduler
```

## Notes

- Scheduler only routes chapters to lanes marked `idle`
- If `lanes` table is empty, scheduler will not consume work
- `/overview` queue fields now represent real backlog, not raw stream history
- `*:stream_depth` fields in `/overview` show raw Redis stream history for debugging
- This runbook is for scaffold bring-up, not full production hardening
