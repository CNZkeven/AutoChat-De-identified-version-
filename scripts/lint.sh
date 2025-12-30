#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m ruff check "$ROOT_DIR/backend/app"

if command -v npm >/dev/null 2>&1; then
    (cd "$ROOT_DIR" && npm run lint:frontend)
else
    echo "npm not found; skipping frontend lint" >&2
    exit 1
fi
