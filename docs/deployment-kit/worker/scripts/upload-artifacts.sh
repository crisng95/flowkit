#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=/dev/null
source "$LANE_ROOT/env/lane.env"

echo "upload-artifacts stub"
echo "Push chapter outputs from $FLOW_AGENT_DIR/output to object storage."
