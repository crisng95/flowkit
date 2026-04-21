# Worker Bootstrap Runbook

## One-time prerequisites on each worker VM

Install:

- Python 3.12
- ffmpeg
- Google Chrome stable
- Redis/Postgres client utilities
- systemd user with service permission

Recommended user:

- `flowkit`

Recommended root:

- `/srv/flowkit`

## Bootstrap one lane

Example for `lane-01`:

```bash
cd docs/deployment-kit/worker/scripts
chmod +x bootstrap-lane.sh
./bootstrap-lane.sh lane-01 flow-account-01
```

This creates:

- `/srv/flowkit/lane-01/...`
- env files
- service unit files

## After bootstrap

1. Sync app repo into:
   - `/srv/flowkit/lane-01/app`
2. Copy unpacked extension into:
   - `/srv/flowkit/lane-01/extension`
3. Edit:
   - `/srv/flowkit/lane-01/env/lane.env`
   - `/srv/flowkit/lane-01/env/account.env`
4. Install worker requirements
5. Enable services

## Install worker requirements

```bash
cd /srv/flowkit/lane-01
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Enable services

```bash
sudo systemctl enable --now flowkit-agent-lane-01
sudo systemctl enable --now flowkit-chrome-lane-01
sudo systemctl enable --now flowkit-lane-runner-lane-01
```

## Verify

### Agent

```bash
curl http://127.0.0.1:8100/health
```

### Lane-runner health

```bash
curl http://127.0.0.1:8181/health
curl http://127.0.0.1:8181/ready
```

### Lane heartbeat

Check Redis:

```bash
redis-cli GET lane:01:heartbeat
```

### Logs

```bash
journalctl -u flowkit-agent-lane-01 -f
journalctl -u flowkit-chrome-lane-01 -f
journalctl -u flowkit-lane-runner-lane-01 -f
```

## Alternative: worker compose mode

If you want the agent and runner inside Docker instead of systemd:

```bash
cp lane.env.example ./env/lane.env
docker compose -f docker-compose.worker.yml up -d --build
```

Notes:

- `flowkit-agent` builds from `./app`
- `lane-runner` builds from this worker kit
- Chrome still stays host-managed

## Host-process lane-runner mode

Useful when the FlowKit agent already exists outside this worker kit, for example:

- agent managed by Coolify
- agent already running on the same VM
- control-plane demo where you only want to prove queue consumption

### Start lane-runner only

```bash
chmod +x scripts/lane-runner.sh
./scripts/lane-runner.sh
```

### One-command worker demo

This starts lane-runner as a host process and waits for `/health`.

```bash
chmod +x scripts/run-worker-demo.sh
./scripts/run-worker-demo.sh
```

Typical overrides for a local demo:

```bash
LANE_ID=lane-01 \
API_HOST=127.0.0.1 \
API_PORT=8100 \
REDIS_URL=redis://127.0.0.1:16379/0 \
POSTGRES_DSN='postgresql://fk:***@127.0.0.1:15432/fk_control' \
RUNNER_HEALTH_PORT=18181 \
WORKER_CONSUMER_NAME=fk-demo-lane-01 \
./scripts/run-worker-demo.sh
```

If object storage is not configured yet, you can allow local-only artifact registration for demo runs:

```bash
ALLOW_LOCAL_ARTIFACT_FALLBACK=1
```

## Same-VM lane-02 demo on `hth2-box`

Keep `lane-01` untouched on `8100/9222`. Bootstrap `lane-02` into a separate host root and health port:

```bash
DEPLOY_ROOT=/home/hth2/flowkit-worker-demo-lane-02 \
SYSTEMD_DIR=/home/hth2/flowkit-worker-demo-lane-02/systemd \
SYSTEMCTL_BIN=true \
SUDO_BIN= \
API_PORT_OVERRIDE=8110 \
WS_PORT_OVERRIDE=9232 \
RUNNER_HEALTH_PORT_OVERRIDE=18182 \
./scripts/bootstrap-lane.sh lane-02 flow-account-02
```

Expected worker root:

- `/home/hth2/flowkit-worker-demo-lane-02`
- agent HTTP: `127.0.0.1:8110`
- agent WS: `127.0.0.1:9232`
- runner health: `127.0.0.1:18182`

### Render a lane-02 unpacked extension copy on Windows

```powershell
F:\vm201 Coolify\flowkit\.venv\Scripts\python.exe `
  F:\vm201 Coolify\flowkit\docs\deployment-kit\worker\scripts\render-extension-bundle.py `
  --lane-id lane-02 `
  --output-dir C:\temp\flowkit-extension-unpacked-lane-02
```

This keeps lane-01 on the existing unpacked extension while generating a second copy that points to `8110/9232`.

### Local Windows tunnel + Chrome launch

Tunnel lane-02 separately from lane-01:

```powershell
ssh -N -L 8110:127.0.0.1:8110 -L 9232:127.0.0.1:9232 hth2-box
```

Launch a separate Chrome profile:

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --user-data-dir=C:\temp\flowkit-real-chrome-lane-02\UserData `
  --disable-extensions-except=C:\temp\flowkit-extension-unpacked-lane-02 `
  --load-extension=C:\temp\flowkit-extension-unpacked-lane-02 `
  https://labs.google/fx/tools/flow
```

If Chrome ignores `--load-extension`, manually load `C:\temp\flowkit-extension-unpacked-lane-02` in `chrome://extensions` for that profile.

### Verify lane-02 wiring

On the VM:

```bash
curl http://127.0.0.1:8110/health
curl http://127.0.0.1:18182/health
curl http://127.0.0.1:18182/ready
```

Expected state before second-account sign-in:

- `8110/health` should be reachable
- `18182/health` should show `lane_id=lane-02`
- `18182/ready` stays `503` until the lane-02 extension is connected and a Flow token is available
