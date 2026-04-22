#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/clean-queue-history.sh [--help]

Clean Redis queue history without touching Postgres orchestration rows.

Safe defaults:
  - delete chapters/lane job streams only when real backlog is 0
  - delete dead-letter streams when depth > 0
  - keep heartbeat keys unless INCLUDE_HEARTBEATS=1
  - skip active queues unless FORCE=1

Optional environment overrides:
  COMPOSE_FILE=docker-compose.control.yml
  REDIS_SERVICE=redis
  REDIS_CONTAINER=fk-demo-redis
  REDIS_DB=0
  LANE_COUNT=10
  INCLUDE_GLOBAL=1
  INCLUDE_LANE_JOBS=1
  INCLUDE_DEAD=1
  INCLUDE_HEARTBEATS=0
  FORCE=0
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTROL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$CONTROL_DIR"

if [[ -f .env.control ]]; then
  # shellcheck source=/dev/null
  source .env.control
fi

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.control.yml}"
REDIS_SERVICE="${REDIS_SERVICE:-redis}"
REDIS_DB="${REDIS_DB:-0}"
LANE_COUNT="${LANE_COUNT:-10}"
INCLUDE_GLOBAL="${INCLUDE_GLOBAL:-1}"
INCLUDE_LANE_JOBS="${INCLUDE_LANE_JOBS:-1}"
INCLUDE_DEAD="${INCLUDE_DEAD:-1}"
INCLUDE_HEARTBEATS="${INCLUDE_HEARTBEATS:-0}"
FORCE="${FORCE:-0}"

run_redis() {
  if [[ -n "${REDIS_CONTAINER:-}" ]]; then
    docker exec "$REDIS_CONTAINER" redis-cli -n "$REDIS_DB" "$@"
  else
    docker compose -f "$COMPOSE_FILE" exec -T "$REDIS_SERVICE" redis-cli -n "$REDIS_DB" "$@"
  fi
}

stream_depth() {
  local stream="$1"
  local depth
  depth="$(run_redis --raw XLEN "$stream" 2>/dev/null || echo 0)"
  [[ -n "$depth" ]] || depth=0
  echo "$depth"
}

stream_backlog() {
  local stream="$1"
  local group="$2"
  local depth pending lag
  depth="$(stream_depth "$stream")"
  pending=0
  lag="$depth"

  local lines=()
  mapfile -t lines < <(run_redis --raw XINFO GROUPS "$stream" 2>/dev/null || true)
  if [[ "${#lines[@]}" -gt 0 ]]; then
    for ((i=0; i<${#lines[@]}; i++)); do
      if [[ "${lines[$i]}" == "name" && $((i+1)) -lt ${#lines[@]} && "${lines[$((i+1))]}" == "$group" ]]; then
        for ((j=i+2; j<${#lines[@]}; j+=2)); do
          key="${lines[$j]}"
          if [[ $((j+1)) -ge ${#lines[@]} ]]; then
            break
          fi
          value="${lines[$((j+1))]}"
          if [[ "$key" == "pending" ]]; then
            pending="$value"
          elif [[ "$key" == "lag" ]]; then
            lag="$value"
          elif [[ "$key" == "name" ]]; then
            break
          fi
        done
        break
      fi
    done
  fi

  if [[ -z "$pending" ]]; then pending=0; fi
  if [[ -z "$lag" ]]; then lag="$depth"; fi
  echo $((pending + lag))
}

delete_key() {
  local key="$1"
  run_redis DEL "$key" >/dev/null
  echo "deleted $key"
}

clean_stream_if_idle() {
  local stream="$1"
  local group="$2"
  local depth backlog
  depth="$(stream_depth "$stream")"
  backlog="$(stream_backlog "$stream" "$group")"

  if [[ "$depth" -eq 0 ]]; then
    echo "skip $stream (empty)"
    return
  fi

  if [[ "$backlog" -gt 0 && "$FORCE" != "1" ]]; then
    echo "skip $stream (backlog=$backlog)"
    return
  fi

  delete_key "$stream"
}

if [[ "$INCLUDE_GLOBAL" == "1" ]]; then
  clean_stream_if_idle "chapters:pending" "scheduler"
fi

if [[ "$INCLUDE_LANE_JOBS" == "1" ]]; then
  for lane_num in $(seq -w 1 "$LANE_COUNT"); do
    clean_stream_if_idle "lane:${lane_num}:jobs" "lane:${lane_num}"
  done
fi

if [[ "$INCLUDE_DEAD" == "1" ]]; then
  for lane_num in $(seq -w 1 "$LANE_COUNT"); do
    key="lane:${lane_num}:dead"
    depth="$(stream_depth "$key")"
    if [[ "$depth" -gt 0 ]]; then
      delete_key "$key"
    else
      echo "skip $key (empty)"
    fi
  done
fi

if [[ "$INCLUDE_HEARTBEATS" == "1" ]]; then
  for lane_num in $(seq -w 1 "$LANE_COUNT"); do
    key="lane:${lane_num}:heartbeat"
    delete_key "$key"
  done
fi

echo "Queue history cleanup complete."
