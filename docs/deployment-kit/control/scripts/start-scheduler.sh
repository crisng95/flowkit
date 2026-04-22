#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/start-scheduler.sh [--help]

Start the scheduler as a host Python process.

Optional environment overrides:
  CONTROL_ROOT=/abs/path/to/control
  ENV_FILE=.env.control
  PYTHON_BIN=python3
  POSTGRES_DSN=postgresql://...
  REDIS_URL=redis://...
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
CONTROL_ROOT="${CONTROL_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$CONTROL_ROOT/.env.control}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

load_env_file "$ENV_FILE"

cd "$CONTROL_ROOT"
export PYTHONPATH="${PYTHONPATH:-$CONTROL_ROOT}"

exec "$PYTHON_BIN" -m fk_control.scheduler
