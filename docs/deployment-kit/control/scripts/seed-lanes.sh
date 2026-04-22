#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTROL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$CONTROL_DIR"

if [[ ! -f .env.control ]]; then
  echo ".env.control not found"
  exit 1
fi

# shellcheck source=/dev/null
source .env.control

if [[ -z "${POSTGRES_DB:-}" || -z "${POSTGRES_USER:-}" || -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "Postgres env vars are missing in .env.control"
  exit 1
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
docker compose -f docker-compose.control.yml exec -T postgres \
  psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f /docker-entrypoint-initdb.d/001-postgres-schema.sql >/dev/null 2>&1 || true

docker compose -f docker-compose.control.yml exec -T postgres \
  psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  < seed-lanes.sql

echo "Seeded lanes successfully."
