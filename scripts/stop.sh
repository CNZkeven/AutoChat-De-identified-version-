#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
PGDATA="$ROOT_DIR/.pgdata"
PGPORT="${PGPORT:-5432}"

stop_pid() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
            kill "$pid" >/dev/null 2>&1 || true
            for _ in {1..10}; do
                if ! kill -0 "$pid" >/dev/null 2>&1; then
                    break
                fi
                sleep 0.5
            done
            if kill -0 "$pid" >/dev/null 2>&1; then
                kill -9 "$pid" >/dev/null 2>&1 || true
            fi
        fi
        rm -f "$pid_file"
    fi
}

stop_pid "$LOG_DIR/backend.pid"
stop_pid "$LOG_DIR/frontend.pid"

if command -v pg_ctl >/dev/null 2>&1 && [ -s "$PGDATA/PG_VERSION" ]; then
    pg_ctl -D "$PGDATA" -o "-p $PGPORT" stop -m fast >> "$LOG_DIR/postgres.log" 2>&1 || true
fi

echo "Stopped services."
