#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/lane-runner.sh [--help]

Start the lane-runner as a host Python process.

Optional environment overrides:
  LANE_ROOT=/abs/path/to/worker
  ENV_FILE=/abs/path/to/lane.env
  PYTHON_BIN=python3
  LOG_FILE=/abs/path/to/lane-runner.log
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANE_ROOT="${LANE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$LANE_ROOT/env/lane.env}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

load_env_file "$ENV_FILE"

FLOWKIT_LOG_DIR="${FLOWKIT_LOG_DIR:-$LANE_ROOT/logs}"
LOG_FILE="${LOG_FILE:-$FLOWKIT_LOG_DIR/lane-runner.log}"

mkdir -p "$FLOWKIT_LOG_DIR"
export PYTHONPATH="${PYTHONPATH:-$LANE_ROOT}"

exec "$PYTHON_BIN" -m fk_worker.runner >>"$LOG_FILE" 2>&1
