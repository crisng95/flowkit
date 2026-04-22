#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/run-worker-demo.sh [--help]

Start a host-process lane-runner and wait for its health endpoint.

Optional environment overrides:
  LANE_ROOT=/abs/path/to/worker
  START_RUNNER=1
  WAIT_FOR_HEALTH=1
  WAIT_TIMEOUT_SECONDS=20
  POLL_INTERVAL_SECONDS=1
  RUNNER_PID_FILE=/tmp/lane-runner.pid
  RUNNER_LOG_FILE=/tmp/lane-runner.log
  RUNNER_HEALTH_URL=http://127.0.0.1:8181/health

Any overrides supported by lane-runner.sh are also accepted.
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANE_ROOT="${LANE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
START_RUNNER="${START_RUNNER:-1}"
WAIT_FOR_HEALTH="${WAIT_FOR_HEALTH:-1}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-20}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-1}"
RUNNER_PID_FILE="${RUNNER_PID_FILE:-$LANE_ROOT/lane-runner.pid}"
RUNNER_LOG_FILE="${RUNNER_LOG_FILE:-$LANE_ROOT/logs/lane-runner.log}"
RUNNER_HEALTH_HOST="${RUNNER_HEALTH_HOST:-0.0.0.0}"
RUNNER_HEALTH_PORT="${RUNNER_HEALTH_PORT:-8181}"
RUNNER_HEALTH_URL="${RUNNER_HEALTH_URL:-http://127.0.0.1:${RUNNER_HEALTH_PORT}/health}"
PYTHON_EXEC="${PYTHON_BIN:-python3}"

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

mkdir -p "$(dirname "$RUNNER_LOG_FILE")"

if [[ "$START_RUNNER" == "1" ]]; then
  stop_pid_file "$RUNNER_PID_FILE"
  nohup "$SCRIPT_DIR/lane-runner.sh" >"$RUNNER_LOG_FILE" 2>&1 &
  echo $! > "$RUNNER_PID_FILE"
fi

if [[ "$WAIT_FOR_HEALTH" == "1" ]]; then
  "$PYTHON_EXEC" - "$RUNNER_HEALTH_URL" "$WAIT_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS" <<'PY'
import json
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

url = sys.argv[1]
timeout_seconds = int(sys.argv[2])
poll_interval = float(sys.argv[3])
deadline = time.time() + timeout_seconds
last_error = None

while time.time() < deadline:
    try:
        with urlopen(url, timeout=5) as response:
            payload = json.load(response)
        print(json.dumps(payload))
        sys.exit(0)
    except (URLError, TimeoutError, ValueError) as exc:
        last_error = str(exc)
        time.sleep(poll_interval)

print(json.dumps({"error": "runner_health_timeout", "detail": last_error}))
sys.exit(1)
PY
fi
