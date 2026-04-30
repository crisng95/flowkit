#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=/dev/null
source "$LANE_ROOT/env/lane.env"
# shellcheck source=/dev/null
source "$LANE_ROOT/env/account.env"

mkdir -p "$CHROME_PROFILE_DIR" "$FLOWKIT_LOG_DIR"

exec google-chrome \
  --user-data-dir="$CHROME_PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-extensions-except="$FLOWKIT_EXTENSION_DIR" \
  --load-extension="$FLOWKIT_EXTENSION_DIR" \
  "https://labs.google/fx/${GOOGLE_FLOW_REGION}/tools/flow" \
  >>"$FLOWKIT_LOG_DIR/chrome.log" 2>&1
