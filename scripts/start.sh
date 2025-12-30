#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
PGDATA="$ROOT_DIR/.pgdata"
PGPORT="${PGPORT:-5432}"
ENV_FILE="$ROOT_DIR/backend/.env"

mkdir -p "$LOG_DIR"
touch "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" "$LOG_DIR/postgres.log"
shopt -s nullglob
for log_file in "$LOG_DIR"/*.log; do
    : > "$log_file"
    chmod 644 "$log_file" || true
done
shopt -u nullglob

if ! command -v pg_ctl >/dev/null 2>&1; then
    echo "pg_ctl not found. Please install PostgreSQL." | tee -a "$LOG_DIR/postgres.log"
    exit 1
fi

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    mkdir -p "$PGDATA"
    initdb -D "$PGDATA" >> "$LOG_DIR/postgres.log" 2>&1
fi

if ! pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
    pg_ctl -D "$PGDATA" -l "$LOG_DIR/postgres.log" -o "-p $PGPORT" start >> "$LOG_DIR/postgres.log" 2>&1
fi

if command -v createdb >/dev/null 2>&1; then
    createdb -p "$PGPORT" autochat >> "$LOG_DIR/postgres.log" 2>&1 || true
fi

export DATABASE_URL="postgresql+psycopg://localhost:${PGPORT}/autochat"
export LOG_DIR

PYTHONPATH="$ROOT_DIR" \
    nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 >> "$LOG_DIR/backend.log" 2>&1 &

echo $! > "$LOG_DIR/backend.pid"

nohup python -m http.server 5173 --directory "$ROOT_DIR/frontend" >> "$LOG_DIR/frontend.log" 2>&1 &

echo $! > "$LOG_DIR/frontend.pid"

echo "Started services: postgres (port $PGPORT), backend (port 8000), frontend (port 5173)."
