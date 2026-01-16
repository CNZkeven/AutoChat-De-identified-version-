#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
PGDATA="$ROOT_DIR/.pgdata"
PGPORT="${PGPORT:-5432}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
ENV_FILE="$ROOT_DIR/backend/.env"
POSTGRES_MARKER="$LOG_DIR/postgres.local"

log_info() {
    echo "[start] $*"
}

log_warn() {
    echo "[start][warn] $*" >&2
}

log_error() {
    echo "[start][error] $*" >&2
}

check_port_listening() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
        return $?
    fi
    if command -v nc >/dev/null 2>&1; then
        nc -z 127.0.0.1 "$port" >/dev/null 2>&1
        return $?
    fi
    return 2
}

mkdir -p "$LOG_DIR"
touch "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" "$LOG_DIR/postgres.log"
shopt -s nullglob
for log_file in "$LOG_DIR"/*.log; do
    : > "$log_file"
    chmod 644 "$log_file" || true
done
shopt -u nullglob
log_info "Cleared logs under $LOG_DIR."

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    log_info "Loaded environment overrides from $ENV_FILE."
fi

if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Python not found. Install Python 3 to run the backend/frontend." | tee -a "$LOG_DIR/backend.log"
    echo "Python not found. Install Python 3 to run the backend/frontend." | tee -a "$LOG_DIR/frontend.log"
    exit 1
fi
log_info "Using Python binary: $PYTHON_BIN"

port_in_use=false
if check_port_listening "$PGPORT"; then
    port_in_use=true
else
    check_status=$?
    if [ "$check_status" -eq 2 ]; then
        log_warn "Neither lsof nor nc found; cannot check port $PGPORT."
    fi
fi

if [ "$port_in_use" = true ]; then
    echo "Detected PostgreSQL already listening on port $PGPORT; skipping local startup." | tee -a "$LOG_DIR/postgres.log"
    rm -f "$POSTGRES_MARKER"
    log_info "Using existing PostgreSQL on port $PGPORT."
else
    if ! command -v pg_ctl >/dev/null 2>&1; then
        echo "pg_ctl not found. Install PostgreSQL or ensure a service is running on port $PGPORT." | tee -a "$LOG_DIR/postgres.log"
        exit 1
    fi

    if [ ! -s "$PGDATA/PG_VERSION" ]; then
        mkdir -p "$PGDATA"
        initdb -D "$PGDATA" >> "$LOG_DIR/postgres.log" 2>&1
    fi

    if ! pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
        if ! pg_ctl -D "$PGDATA" -l "$LOG_DIR/postgres.log" -o "-p $PGPORT" start >> "$LOG_DIR/postgres.log" 2>&1; then
            echo "Failed to start local PostgreSQL. Check $LOG_DIR/postgres.log or install PostgreSQL." | tee -a "$LOG_DIR/postgres.log"
            exit 1
        fi
    fi
    touch "$POSTGRES_MARKER"
    log_info "Started local PostgreSQL (data dir: $PGDATA, port: $PGPORT)."
fi

if command -v createdb >/dev/null 2>&1; then
    if createdb -p "$PGPORT" autochat >> "$LOG_DIR/postgres.log" 2>&1; then
        log_info "Ensured database 'autochat' exists."
    else
        log_warn "createdb failed (database may already exist or permission denied). See $LOG_DIR/postgres.log."
    fi
else
    log_warn "createdb not found; skipping database creation."
fi

: "${DATABASE_URL:=postgresql+psycopg://localhost:${PGPORT}/autochat}"
export DATABASE_URL
export LOG_DIR
log_info "DATABASE_URL=$DATABASE_URL"

backend_port_in_use=false
if check_port_listening "$BACKEND_PORT"; then
    backend_port_in_use=true
else
    check_status=$?
    if [ "$check_status" -eq 2 ]; then
        log_warn "Cannot verify backend port $BACKEND_PORT (missing lsof/nc)."
    fi
fi

backend_status="skipped"
if [ "$backend_port_in_use" = true ]; then
    if [ -f "$LOG_DIR/backend.pid" ] && kill -0 "$(cat "$LOG_DIR/backend.pid" 2>/dev/null)" >/dev/null 2>&1; then
        log_warn "Backend already running on port $BACKEND_PORT (pid $(cat "$LOG_DIR/backend.pid"))."
        backend_status="already running"
    else
        log_error "Port $BACKEND_PORT already in use; skipping backend start."
        backend_status="port in use"
    fi
else
    log_info "Starting backend on port $BACKEND_PORT..."
    PYTHONPATH="$ROOT_DIR" \
        nohup "$PYTHON_BIN" -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" >> "$LOG_DIR/backend.log" 2>&1 &
    backend_pid=$!
    echo "$backend_pid" > "$LOG_DIR/backend.pid"
    backend_status="running (pid $backend_pid)"
fi

frontend_port_in_use=false
if check_port_listening "$FRONTEND_PORT"; then
    frontend_port_in_use=true
else
    check_status=$?
    if [ "$check_status" -eq 2 ]; then
        log_warn "Cannot verify frontend port $FRONTEND_PORT (missing lsof/nc)."
    fi
fi

frontend_status="skipped"
if [ "$frontend_port_in_use" = true ]; then
    if [ -f "$LOG_DIR/frontend.pid" ] && kill -0 "$(cat "$LOG_DIR/frontend.pid" 2>/dev/null)" >/dev/null 2>&1; then
        log_warn "Frontend already running on port $FRONTEND_PORT (pid $(cat "$LOG_DIR/frontend.pid"))."
        frontend_status="already running"
    else
        log_error "Port $FRONTEND_PORT already in use; skipping frontend start."
        frontend_status="port in use"
    fi
else
    log_info "Starting frontend on port $FRONTEND_PORT..."
    nohup "$PYTHON_BIN" -m http.server "$FRONTEND_PORT" --directory "$ROOT_DIR/frontend" >> "$LOG_DIR/frontend.log" 2>&1 &
    frontend_pid=$!
    echo "$frontend_pid" > "$LOG_DIR/frontend.pid"
    frontend_status="running (pid $frontend_pid)"
fi

echo "Started services:"
echo "  - postgres: port $PGPORT"
echo "  - backend:  $BACKEND_PORT ($backend_status)"
echo "  - frontend: $FRONTEND_PORT ($frontend_status)"
