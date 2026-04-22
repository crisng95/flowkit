#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/run-control-demo.sh [--help]

Reset state, ensure host-process control services are running, create a demo
project, and print /overview.

Optional environment overrides:
  CONTROL_ROOT=/abs/path/to/control
  RUNTIME_ROOT=/abs/path/for/logs-and-pids
  START_SERVICES=1
  RESET_STATE=1
  START_DELAY_SECONDS=3
  WAIT_FOR_ASSIGNMENTS=1
  WAIT_TIMEOUT_SECONDS=30
  POLL_INTERVAL_SECONDS=1
  CONTROL_API_URL=http://127.0.0.1:8080
  CONTROL_API_PID_FILE=/tmp/control-api.pid
  SCHEDULER_PID_FILE=/tmp/scheduler.pid
  CONTROL_API_LOG=/tmp/control-api.log
  SCHEDULER_LOG=/tmp/scheduler.log

Any overrides supported by:
  - reset-control-state.sh
  - create-demo-project.sh
  - start-control-api.sh
  - start-scheduler.sh
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTROL_ROOT="${CONTROL_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
RUNTIME_ROOT="${RUNTIME_ROOT:-$CONTROL_ROOT}"
START_SERVICES="${START_SERVICES:-1}"
RESET_STATE="${RESET_STATE:-1}"
START_DELAY_SECONDS="${START_DELAY_SECONDS:-3}"
WAIT_FOR_ASSIGNMENTS="${WAIT_FOR_ASSIGNMENTS:-1}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-30}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-1}"
CONTROL_API_URL="${CONTROL_API_URL:-http://127.0.0.1:8080}"
CONTROL_API_PID_FILE="${CONTROL_API_PID_FILE:-$RUNTIME_ROOT/control-api.pid}"
SCHEDULER_PID_FILE="${SCHEDULER_PID_FILE:-$RUNTIME_ROOT/scheduler.pid}"
CONTROL_API_LOG="${CONTROL_API_LOG:-$RUNTIME_ROOT/control-api.log}"
SCHEDULER_LOG="${SCHEDULER_LOG:-$RUNTIME_ROOT/scheduler.log}"
CHAPTER_COUNT_INPUT="${3:-${CHAPTER_COUNT:-10}}"

mkdir -p "$RUNTIME_ROOT"

stop_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(tr -d '\r\n' < "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      sleep 1
    fi
    rm -f "$pid_file"
  fi
}

if [[ "$START_SERVICES" == "1" ]]; then
  stop_pid_file "$CONTROL_API_PID_FILE"
  stop_pid_file "$SCHEDULER_PID_FILE"

  nohup "$SCRIPT_DIR/start-control-api.sh" >"$CONTROL_API_LOG" 2>&1 &
  echo $! > "$CONTROL_API_PID_FILE"

  nohup "$SCRIPT_DIR/start-scheduler.sh" >"$SCHEDULER_LOG" 2>&1 &
  echo $! > "$SCHEDULER_PID_FILE"

  sleep "$START_DELAY_SECONDS"
fi

if [[ "$RESET_STATE" == "1" ]]; then
  "$SCRIPT_DIR/reset-control-state.sh"
fi

"$SCRIPT_DIR/create-demo-project.sh" "$@"
echo

if [[ "$WAIT_FOR_ASSIGNMENTS" == "1" ]]; then
  "$PYTHON_BIN" - "$CONTROL_API_URL" "$CHAPTER_COUNT_INPUT" "$WAIT_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS" <<'PY'
import json
import sys
import time
from urllib.request import urlopen

base_url = sys.argv[1].rstrip("/")
expected_chapters = int(sys.argv[2])
timeout_seconds = int(sys.argv[3])
poll_interval = float(sys.argv[4])
expected_jobs = expected_chapters * 9
deadline = time.time() + timeout_seconds
last_payload = None

while time.time() < deadline:
    with urlopen(f"{base_url}/overview", timeout=10) as response:
        payload = json.load(response)
    last_payload = payload
    summary = payload.get("summary", {})
    queues = payload.get("queues", {})
    assigned = summary.get("chapter_status_counts", {}).get("assigned", 0)
    backlog = queues.get("chapters:pending", 0)
    if (
        summary.get("chapter_count") == expected_chapters
        and summary.get("job_count") == expected_jobs
        and assigned == expected_chapters
        and backlog == 0
    ):
        print(json.dumps(payload))
        sys.exit(0)
    time.sleep(poll_interval)

print(json.dumps(last_payload or {"error": "overview_unavailable"}))
sys.exit(1)
PY
else
  curl -sS "${CONTROL_API_URL%/}/overview"
fi
