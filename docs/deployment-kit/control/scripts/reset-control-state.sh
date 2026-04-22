#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/reset-control-state.sh [--help]

Reset control-plane state for repeatable demo runs.

Defaults:
  - compose mode using docker-compose.control.yml
  - services: postgres, redis
  - database: fk_control
  - user: fk
  - lane count: 10

Optional environment overrides:
  COMPOSE_FILE=docker-compose.control.yml
  POSTGRES_SERVICE=postgres
  REDIS_SERVICE=redis
  POSTGRES_CONTAINER=fk-demo-postgres
  REDIS_CONTAINER=fk-demo-redis
  POSTGRES_DB=fk_control
  POSTGRES_USER=fk
  REDIS_DB=0
  LANE_COUNT=10

Container override mode:
  If POSTGRES_CONTAINER and REDIS_CONTAINER are set, the script uses
  docker exec instead of docker compose exec.
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
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
REDIS_SERVICE="${REDIS_SERVICE:-redis}"
POSTGRES_DB="${POSTGRES_DB:-fk_control}"
POSTGRES_USER="${POSTGRES_USER:-fk}"
REDIS_DB="${REDIS_DB:-0}"
LANE_COUNT="${LANE_COUNT:-10}"

run_postgres() {
  if [[ -n "${POSTGRES_CONTAINER:-}" ]]; then
    docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"
  else
    docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"
  fi
}

run_redis() {
  if [[ -n "${REDIS_CONTAINER:-}" ]]; then
    docker exec "$REDIS_CONTAINER" redis-cli -n "$REDIS_DB" "$@"
  else
    docker compose -f "$COMPOSE_FILE" exec -T "$REDIS_SERVICE" redis-cli -n "$REDIS_DB" "$@"
  fi
}

redis_keys=("chapters:pending")
for lane_num in $(seq -w 1 "$LANE_COUNT"); do
  redis_keys+=(
    "lane:${lane_num}:jobs"
    "lane:${lane_num}:dead"
    "lane:${lane_num}:heartbeat"
  )
done

run_postgres -v ON_ERROR_STOP=1 -c "
truncate table artifacts, jobs, chapters, projects, lane_heartbeats cascade;
update lanes
set status = 'idle',
    current_chapter_id = null,
    credits_last_seen = null,
    token_age_seconds = null,
    last_error_text = null,
    last_heartbeat_at = null;
" >/dev/null

run_redis DEL "${redis_keys[@]}" >/dev/null

echo "Control state reset complete."
echo "Postgres target: ${POSTGRES_CONTAINER:-compose:$POSTGRES_SERVICE}"
echo "Redis target: ${REDIS_CONTAINER:-compose:$REDIS_SERVICE}"
echo "Lane count reset: $LANE_COUNT"
