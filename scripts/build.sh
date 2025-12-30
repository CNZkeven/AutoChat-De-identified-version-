#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m compileall "$ROOT_DIR/backend/app"

if command -v npm >/dev/null 2>&1; then
    (cd "$ROOT_DIR" && npm run build:frontend)
else
    echo "npm not found; skipping frontend build" >&2
    exit 1
fi
