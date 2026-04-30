#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=/dev/null
source "$LANE_ROOT/env/lane.env"

mkdir -p "$FLOW_AGENT_DIR" "$FLOWKIT_LOG_DIR"
cd "$FLOWKIT_REPO"

exec python -m agent.main >>"$FLOWKIT_LOG_DIR/agent.log" 2>&1
