#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bootstrap-lane.sh lane-01 [flow-account-01]"
  echo
  echo "Optional environment overrides:"
  echo "  DEPLOY_ROOT=/srv/flowkit/lane-02"
  echo "  API_PORT_OVERRIDE=8110"
  echo "  WS_PORT_OVERRIDE=9232"
  echo "  RUNNER_HEALTH_PORT_OVERRIDE=18182"
  echo "  APP_SOURCE=/path/to/flowkit/repo"
  echo "  SYSTEMD_DIR=/etc/systemd/system"
  echo "  SYSTEMCTL_BIN=systemctl"
  echo "  SUDO_BIN=sudo"
  exit 1
fi

LANE_ID="$1"
FLOW_ACCOUNT_ALIAS="${2:-${LANE_ID/lane-/flow-account-}}"
LANE_NUM="${LANE_ID#lane-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_ROOT="${DEPLOY_ROOT:-/srv/flowkit/${LANE_ID}}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
SYSTEMCTL_BIN="${SYSTEMCTL_BIN:-systemctl}"
SUDO_BIN="${SUDO_BIN-sudo}"
API_PORT_OVERRIDE="${API_PORT_OVERRIDE:-}"
WS_PORT_OVERRIDE="${WS_PORT_OVERRIDE:-}"
RUNNER_HEALTH_PORT_OVERRIDE="${RUNNER_HEALTH_PORT_OVERRIDE:-}"
APP_SOURCE="${APP_SOURCE:-}"

run_privileged() {
  if [[ -n "$SUDO_BIN" ]]; then
    "$SUDO_BIN" "$@"
  else
    "$@"
  fi
}

replace_env_value() {
  local env_file="$1"
  local key="$2"
  local value="$3"
  [[ -n "$value" ]] || return 0
  run_privileged sed -i "s|^${key}=.*|${key}=${value}|" "$env_file"
}

copy_optional_tree() {
  local source_path="$1"
  local target_path="$2"
  [[ -d "$source_path" ]] || return 0
  run_privileged cp -r "$source_path" "$target_path"
}

copy_tree_contents() {
  local source_path="$1"
  local target_path="$2"
  [[ -d "$source_path" ]] || return 0
  run_privileged cp -r "${source_path}/." "$target_path/"
}

if [[ -n "$APP_SOURCE" && ! -d "$APP_SOURCE" ]]; then
  echo "APP_SOURCE does not exist: $APP_SOURCE" >&2
  exit 1
fi

run_privileged mkdir -p \
  "${DEPLOY_ROOT}/app" \
  "${DEPLOY_ROOT}/chrome-profile" \
  "${DEPLOY_ROOT}/extension" \
  "${DEPLOY_ROOT}/runtime/output" \
  "${DEPLOY_ROOT}/work" \
  "${DEPLOY_ROOT}/logs" \
  "${DEPLOY_ROOT}/env" \
  "${DEPLOY_ROOT}/scripts"

run_privileged cp -r "${WORKER_DIR}/fk_worker" "${DEPLOY_ROOT}/"
copy_optional_tree "${WORKER_DIR}/tests" "${DEPLOY_ROOT}/"
run_privileged cp "${WORKER_DIR}/requirements.txt" "${DEPLOY_ROOT}/"
run_privileged cp "${WORKER_DIR}/scripts/"*.sh "${DEPLOY_ROOT}/scripts/"
if [[ -f "${WORKER_DIR}/docker-compose.worker.yml" ]]; then
  run_privileged cp "${WORKER_DIR}/docker-compose.worker.yml" "${DEPLOY_ROOT}/"
fi
if [[ -f "${WORKER_DIR}/Dockerfile.worker" ]]; then
  run_privileged cp "${WORKER_DIR}/Dockerfile.worker" "${DEPLOY_ROOT}/"
fi
if [[ -n "$APP_SOURCE" ]]; then
  copy_tree_contents "$APP_SOURCE" "${DEPLOY_ROOT}/app"
fi

run_privileged cp "${WORKER_DIR}/lane.env.example" "${DEPLOY_ROOT}/env/lane.env"
run_privileged cp "${WORKER_DIR}/account.env.example" "${DEPLOY_ROOT}/env/account.env"

run_privileged sed -i "s|lane-01|${LANE_ID}|g" "${DEPLOY_ROOT}/env/lane.env"
run_privileged sed -i "s|flow-account-01|${FLOW_ACCOUNT_ALIAS}|g" "${DEPLOY_ROOT}/env/lane.env"
run_privileged sed -i "s|flow-account-01|${FLOW_ACCOUNT_ALIAS}|g" "${DEPLOY_ROOT}/env/account.env"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "FLOWKIT_ROOT" "${DEPLOY_ROOT}"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "FLOWKIT_REPO" "${DEPLOY_ROOT}/app"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "FLOW_AGENT_DIR" "${DEPLOY_ROOT}/runtime"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "FLOWKIT_WORK_DIR" "${DEPLOY_ROOT}/work"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "FLOWKIT_LOG_DIR" "${DEPLOY_ROOT}/logs"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "CHROME_PROFILE_DIR" "${DEPLOY_ROOT}/chrome-profile"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "FLOWKIT_EXTENSION_DIR" "${DEPLOY_ROOT}/extension"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "API_PORT" "$API_PORT_OVERRIDE"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "WS_PORT" "$WS_PORT_OVERRIDE"
replace_env_value "${DEPLOY_ROOT}/env/lane.env" "RUNNER_HEALTH_PORT" "$RUNNER_HEALTH_PORT_OVERRIDE"

if [[ -d "${WORKER_DIR}/systemd" ]]; then
  run_privileged cp "${WORKER_DIR}/systemd/flowkit-agent.service" "${SYSTEMD_DIR}/flowkit-agent-${LANE_ID}.service"
  run_privileged cp "${WORKER_DIR}/systemd/flowkit-chrome.service" "${SYSTEMD_DIR}/flowkit-chrome-${LANE_ID}.service"
  run_privileged cp "${WORKER_DIR}/systemd/flowkit-lane-runner.service" "${SYSTEMD_DIR}/flowkit-lane-runner-${LANE_ID}.service"

  run_privileged sed -i "s|/srv/flowkit/lane-01|${DEPLOY_ROOT}|g" "${SYSTEMD_DIR}/flowkit-agent-${LANE_ID}.service"
  run_privileged sed -i "s|/srv/flowkit/lane-01|${DEPLOY_ROOT}|g" "${SYSTEMD_DIR}/flowkit-chrome-${LANE_ID}.service"
  run_privileged sed -i "s|/srv/flowkit/lane-01|${DEPLOY_ROOT}|g" "${SYSTEMD_DIR}/flowkit-lane-runner-${LANE_ID}.service"

  run_privileged "$SYSTEMCTL_BIN" daemon-reload
fi

echo "Bootstrapped ${LANE_ID} at ${DEPLOY_ROOT}"
echo "Next:"
if [[ -n "$APP_SOURCE" ]]; then
  echo "  1. FlowKit app code copied from ${APP_SOURCE} into ${DEPLOY_ROOT}/app"
else
  echo "  1. Sync FlowKit app code into ${DEPLOY_ROOT}/app"
fi
echo "  2. Put extension files into ${DEPLOY_ROOT}/extension"
echo "  3. Edit ${DEPLOY_ROOT}/env/lane.env and account.env"
echo "  4. Install Python deps"
echo "  5. Enable services:"
echo "     sudo systemctl enable --now flowkit-agent-${LANE_ID}"
echo "     sudo systemctl enable --now flowkit-chrome-${LANE_ID}"
echo "     sudo systemctl enable --now flowkit-lane-runner-${LANE_ID}"
