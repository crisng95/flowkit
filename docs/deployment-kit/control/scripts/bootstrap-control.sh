#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTROL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$CONTROL_DIR"

if [[ ! -f .env.control ]]; then
  cp .env.control.example .env.control
  echo "Created .env.control from example. Edit secrets before production use."
fi

docker compose -f docker-compose.control.yml up -d --build

echo "Control plane started."
echo "Next:"
echo "  1. Edit .env.control with real credentials"
echo "  2. Run scripts/seed-lanes.sh"
