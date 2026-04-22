#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/create-demo-project.sh [--help]

Create a demo project on the control API with sensible defaults.

Optional environment overrides:
  CONTROL_API_URL=http://127.0.0.1:8080
  SOURCE_TITLE=Fresh 10 Lane Demo
  SOURCE_BRIEF=Test split into chapters
  TARGET_DURATION_SECONDS=2700
  CHAPTER_COUNT=10
  MATERIAL_ID=realistic

Optional positional overrides:
  ./scripts/create-demo-project.sh "Title" 2700 10 realistic "Brief text"
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

CONTROL_API_URL="${CONTROL_API_URL:-http://127.0.0.1:8080}"
SOURCE_TITLE="${1:-${SOURCE_TITLE:-Fresh 10 Lane Demo}}"
TARGET_DURATION_SECONDS="${2:-${TARGET_DURATION_SECONDS:-2700}}"
CHAPTER_COUNT="${3:-${CHAPTER_COUNT:-10}}"
MATERIAL_ID="${4:-${MATERIAL_ID:-realistic}}"
SOURCE_BRIEF="${5:-${SOURCE_BRIEF:-Test split into chapters}}"

curl -sS \
  -X POST "${CONTROL_API_URL%/}/projects" \
  -H 'Content-Type: application/json' \
  -d "{
    \"source_title\": \"${SOURCE_TITLE}\",
    \"source_brief\": \"${SOURCE_BRIEF}\",
    \"target_duration_seconds\": ${TARGET_DURATION_SECONDS},
    \"material_id\": \"${MATERIAL_ID}\",
    \"chapter_count\": ${CHAPTER_COUNT}
  }"
