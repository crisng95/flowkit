#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/control-service.sh <start|stop|status|health> [--help]

Manage the host-process control API and scheduler with shared pid files.

Optional environment overrides:
  CONTROL_ROOT=/abs/path/to/control
  RUNTIME_ROOT=/abs/path/for/logs-and-pids
  CONTROL_API_URL=http://127.0.0.1:8080
  CONTROL_API_PID_FILE=/tmp/control-api.pid
  SCHEDULER_PID_FILE=/tmp/scheduler.pid
  CONTROL_API_LOG=/tmp/control-api.log
  SCHEDULER_LOG=/tmp/scheduler.log
  START_DELAY_SECONDS=3
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
CONTROL_ROOT="${CONTROL_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
RUNTIME_ROOT="${RUNTIME_ROOT:-$CONTROL_ROOT}"
CONTROL_API_URL="${CONTROL_API_URL:-http://127.0.0.1:8080}"
CONTROL_API_PID_FILE="${CONTROL_API_PID_FILE:-$RUNTIME_ROOT/control-api.pid}"
SCHEDULER_PID_FILE="${SCHEDULER_PID_FILE:-$RUNTIME_ROOT/scheduler.pid}"
CONTROL_API_LOG="${CONTROL_API_LOG:-$RUNTIME_ROOT/control-api.log}"
SCHEDULER_LOG="${SCHEDULER_LOG:-$RUNTIME_ROOT/scheduler.log}"
START_DELAY_SECONDS="${START_DELAY_SECONDS:-3}"
WAIT_FOR_HEALTH="${WAIT_FOR_HEALTH:-1}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-20}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$RUNTIME_ROOT"

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '\r\n' < "$pid_file"
  fi
}

pid_running() {
  local pid_file="$1"
  local pid
  pid="$(read_pid "$pid_file")"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
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

print_status_json() {
  "$PYTHON_BIN" - "$CONTROL_API_URL" "$CONTROL_API_PID_FILE" "$SCHEDULER_PID_FILE" <<'PY'
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

api_url, api_pid_file, scheduler_pid_file = sys.argv[1:4]


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


def fetch_health(url: str):
    try:
        with urlopen(f"{url.rstrip('/')}/health", timeout=3) as response:
            return json.load(response)
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return {"status": "unreachable", "detail": str(exc)}


api_pid = read_pid(api_pid_file)
scheduler_pid = read_pid(scheduler_pid_file)
payload = {
    "control_api_pid": api_pid,
    "control_api_running": pid_running(api_pid),
    "scheduler_pid": scheduler_pid,
    "scheduler_running": pid_running(scheduler_pid),
    "health": fetch_health(api_url),
}
print(json.dumps(payload))
PY
}

wait_for_health() {
  "$PYTHON_BIN" - "$CONTROL_API_URL" "$WAIT_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS" <<'PY'
import json
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

base_url = sys.argv[1].rstrip("/")
timeout_seconds = int(sys.argv[2])
poll_interval = float(sys.argv[3])
deadline = time.time() + timeout_seconds
last_error = None

while time.time() < deadline:
    try:
        with urlopen(f"{base_url}/health", timeout=5) as response:
            payload = json.load(response)
        print(json.dumps(payload))
        sys.exit(0)
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        last_error = str(exc)
        time.sleep(poll_interval)

print(json.dumps({"status": "timeout", "detail": last_error}))
sys.exit(1)
PY
}

case "$ACTION" in
  start)
    stop_pid_file "$CONTROL_API_PID_FILE"
    stop_pid_file "$SCHEDULER_PID_FILE"
    nohup "$SCRIPT_DIR/start-control-api.sh" >"$CONTROL_API_LOG" 2>&1 &
    echo $! > "$CONTROL_API_PID_FILE"
    nohup "$SCRIPT_DIR/start-scheduler.sh" >"$SCHEDULER_LOG" 2>&1 &
    echo $! > "$SCHEDULER_PID_FILE"
    sleep "$START_DELAY_SECONDS"
    if [[ "$WAIT_FOR_HEALTH" == "1" ]]; then
      wait_for_health
    else
      print_status_json
    fi
    ;;
  stop)
    stop_pid_file "$CONTROL_API_PID_FILE"
    stop_pid_file "$SCHEDULER_PID_FILE"
    print_status_json
    ;;
  status)
    print_status_json
    ;;
  health)
    wait_for_health
    ;;
  *)
    usage
    exit 1
    ;;
esac
