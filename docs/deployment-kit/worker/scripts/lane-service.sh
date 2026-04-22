#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/lane-service.sh <start|stop|status|health|ready> [--help]

Manage the host-process lane runner with shared pid/log files.

Optional environment overrides:
  LANE_ROOT=/abs/path/to/worker
  RUNNER_PID_FILE=/tmp/lane-runner.pid
  RUNNER_LOG_FILE=/tmp/lane-runner.log
  RUNNER_HEALTH_URL=http://127.0.0.1:8181/health
  RUNNER_READY_URL=http://127.0.0.1:8181/ready
  WAIT_FOR_HEALTH=1
  WAIT_TIMEOUT_SECONDS=20
  POLL_INTERVAL_SECONDS=1
  PYTHON_BIN=python3
EOF
}

ACTION="${1:-}"
if [[ -z "$ACTION" || "$ACTION" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANE_ROOT="${LANE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$LANE_ROOT/env/lane.env}"

load_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    local key="${line%%=*}"
    local value="${line#*=}"
    if [[ -z "${!key+x}" ]]; then
      export "$key=$value"
    fi
  done < "$env_file"
}

load_env_file "$ENV_FILE"

RUNNER_PID_FILE="${RUNNER_PID_FILE:-$LANE_ROOT/lane-runner.pid}"
RUNNER_LOG_FILE="${RUNNER_LOG_FILE:-$LANE_ROOT/logs/lane-runner.log}"
RUNNER_HEALTH_PORT="${RUNNER_HEALTH_PORT:-8181}"
RUNNER_HEALTH_URL="${RUNNER_HEALTH_URL:-http://127.0.0.1:${RUNNER_HEALTH_PORT}/health}"
RUNNER_READY_URL="${RUNNER_READY_URL:-http://127.0.0.1:${RUNNER_HEALTH_PORT}/ready}"
WAIT_FOR_HEALTH="${WAIT_FOR_HEALTH:-1}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-20}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '\r\n' < "$pid_file"
  fi
}

stop_pid_file() {
  local pid_file="$1"
  local pid
  pid="$(read_pid "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    sleep 1
  fi
  rm -f "$pid_file"
}

fetch_url_json() {
  "$PYTHON_BIN" - "$1" <<'PY'
import json
import sys
from urllib.error import URLError
from urllib.request import urlopen

url = sys.argv[1]
try:
    with urlopen(url, timeout=3) as response:
        payload = json.load(response)
    print(json.dumps(payload))
    sys.exit(0)
except (URLError, TimeoutError, ValueError, OSError) as exc:
    print(json.dumps({"status": "unreachable", "detail": str(exc)}))
    sys.exit(1)
PY
}

print_status_json() {
  "$PYTHON_BIN" - "$RUNNER_PID_FILE" "$RUNNER_HEALTH_URL" "$RUNNER_READY_URL" <<'PY'
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

pid_file, health_url, ready_url = sys.argv[1:4]


def read_pid(path_str: str):
    path = Path(path_str)
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return int(value) if value else None


def pid_running(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        import os

        os.kill(pid, 0)
    except OSError:
        return False
    return True


def fetch(url: str):
    try:
        with urlopen(url, timeout=3) as response:
            payload = json.load(response)
        return {"ok": True, "payload": payload}
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return {"ok": False, "payload": {"status": "unreachable", "detail": str(exc)}}


runner_pid = read_pid(pid_file)
payload = {
    "runner_pid": runner_pid,
    "runner_running": pid_running(runner_pid),
    "health": fetch(health_url),
    "ready": fetch(ready_url),
}
print(json.dumps(payload))
PY
}

case "$ACTION" in
  start)
    START_RUNNER=1 \
    WAIT_FOR_HEALTH="$WAIT_FOR_HEALTH" \
    WAIT_TIMEOUT_SECONDS="$WAIT_TIMEOUT_SECONDS" \
    POLL_INTERVAL_SECONDS="$POLL_INTERVAL_SECONDS" \
    RUNNER_PID_FILE="$RUNNER_PID_FILE" \
    RUNNER_LOG_FILE="$RUNNER_LOG_FILE" \
    "$SCRIPT_DIR/run-worker-demo.sh"
    ;;
  stop)
    stop_pid_file "$RUNNER_PID_FILE"
    print_status_json
    ;;
  status)
    print_status_json
    ;;
  health)
    fetch_url_json "$RUNNER_HEALTH_URL"
    ;;
  ready)
    fetch_url_json "$RUNNER_READY_URL"
    ;;
  *)
    usage
    exit 1
    ;;
esac
