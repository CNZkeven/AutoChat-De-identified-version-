#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
PGDATA="$ROOT_DIR/.pgdata"
PGPORT="${PGPORT:-5432}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
POSTGRES_MARKER="$LOG_DIR/postgres.local"

log_info() {
    echo "[stop] $*"
}

log_warn() {
    echo "[stop][warn] $*" >&2
}

log_error() {
    echo "[stop][error] $*" >&2
}

matches_all_patterns() {
    local cmd="$1"
    shift
    local pattern
    for pattern in "$@"; do
        if [[ "$cmd" != *"$pattern"* ]]; then
            return 1
        fi
    done
    return 0
}

stop_pid() {
    local pid_file="$1"
    local label="$2"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if [ -z "$pid" ]; then
            log_warn "$label pid file is empty: $pid_file"
            rm -f "$pid_file"
            return
        fi
        if ! kill -0 "$pid" >/dev/null 2>&1; then
            log_warn "$label not running (stale pid $pid)."
            rm -f "$pid_file"
            return
        fi
        log_info "Stopping $label (pid $pid)..."
        kill "$pid" >/dev/null 2>&1 || true
        for _ in {1..10}; do
            if ! kill -0 "$pid" >/dev/null 2>&1; then
                break
            fi
            sleep 0.5
        done
        if kill -0 "$pid" >/dev/null 2>&1; then
            log_warn "$label did not stop gracefully; force killing."
            kill -9 "$pid" >/dev/null 2>&1 || true
        else
            log_info "$label stopped."
        fi
        rm -f "$pid_file"
    else
        log_warn "$label pid file not found: $pid_file"
    fi
}

kill_port_processes() {
    local port="$1"
    local label="$2"
    shift 2
    local patterns=("$@")

    if ! command -v lsof >/dev/null 2>&1; then
        log_warn "lsof not found; cannot check port $port."
        return
    fi

    local pids
    pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -z "$pids" ]; then
        return
    fi

    local pid
    for pid in $pids; do
        local cmd
        cmd=$(ps -p "$pid" -o command= 2>/dev/null || true)
        if [ -z "$cmd" ]; then
            continue
        fi
        if matches_all_patterns "$cmd" "${patterns[@]}"; then
            log_warn "Killing $label on port $port (pid $pid)."
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
        else
            log_warn "Port $port still in use by pid $pid ($cmd). Skipping."
        fi
    done
}

stop_pid "$LOG_DIR/backend.pid" "backend"
stop_pid "$LOG_DIR/frontend.pid" "frontend"

kill_port_processes "$BACKEND_PORT" "backend" "uvicorn" "backend.app.main:app"
kill_port_processes "$FRONTEND_PORT" "frontend" "http.server" "$ROOT_DIR/frontend"
kill_port_processes "$FRONTEND_PORT" "frontend" "frontend-react"

if command -v pg_ctl >/dev/null 2>&1 && [ -s "$PGDATA/PG_VERSION" ]; then
    if [ -f "$POSTGRES_MARKER" ]; then
        log_info "Stopping local PostgreSQL (marker: $POSTGRES_MARKER)."
        pg_ctl -D "$PGDATA" -o "-p $PGPORT" stop -m fast >> "$LOG_DIR/postgres.log" 2>&1 || true
        rm -f "$POSTGRES_MARKER"
    else
        if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
            log_warn "Local PostgreSQL appears running from $PGDATA; stopping."
            pg_ctl -D "$PGDATA" -o "-p $PGPORT" stop -m fast >> "$LOG_DIR/postgres.log" 2>&1 || true
        else
            log_info "No local PostgreSQL to stop."
        fi
    fi
else
    log_warn "pg_ctl not found or PGDATA missing; skipping PostgreSQL stop."
fi

echo "Stopped services."
