#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
EXAMPLE_FILE="$ROOT_DIR/.env.example"

log_info() {
    echo "[start] $*"
}

log_warn() {
    echo "[start][warn] $*" >&2
}

log_error() {
    echo "[start][error] $*" >&2
}

compose() {
    (cd "$ROOT_DIR" && docker compose "$@")
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

if ! command -v docker >/dev/null 2>&1; then
    log_error "docker 未安装或不可用。请先安装 Docker Desktop。"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    log_error "docker compose 不可用。请升级 Docker Desktop 或安装 Compose v2。"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    log_info "已从 $EXAMPLE_FILE 创建 $ENV_FILE。"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

POSTGRES_PORT="${POSTGRES_PORT:-5433}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

port_in_use=false
if check_port_listening "$POSTGRES_PORT"; then
    port_in_use=true
else
    check_status=$?
    if [ "$check_status" -eq 2 ]; then
        log_warn "无法检查端口 $POSTGRES_PORT（缺少 lsof/nc）。"
    fi
fi

if [ "$port_in_use" = true ]; then
    if compose ps --services --status running 2>/dev/null | grep -qx "db"; then
        log_warn "端口 $POSTGRES_PORT 已被当前项目占用，先停止旧容器。"
        compose down
    else
        log_error "端口 $POSTGRES_PORT 已被非本项目进程占用，请先释放该端口后重试。"
        exit 1
    fi
fi

log_info "启动 Docker Compose 全栈服务..."
compose up -d --build

log_info "服务启动完成。"
log_info "Frontend: http://localhost:$FRONTEND_PORT"
log_info "Backend:  http://localhost:$BACKEND_PORT"
log_info "Postgres: localhost:$POSTGRES_PORT"
