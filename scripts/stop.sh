#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
PORTS_FILE="$LOG_DIR/compose-ports.env"

log_info() {
    echo "[stop] $*"
}

log_warn() {
    echo "[stop][warn] $*" >&2
}

log_error() {
    echo "[stop][error] $*" >&2
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
    log_error "docker 未安装或不可用。"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    log_error "docker compose 不可用。"
    exit 1
fi

log_info "停止 Docker Compose 服务..."
compose down --remove-orphans

leftover_containers=$(compose ps -a -q 2>/dev/null || true)
if [ -n "$leftover_containers" ]; then
    log_warn "检测到残留容器，尝试强制清理。"
    compose rm -fsv
fi

if [ -f "$PORTS_FILE" ]; then
    # shellcheck disable=SC1090
    source "$PORTS_FILE"
    for port in "$LAST_POSTGRES_PORT" "$LAST_BACKEND_PORT" "$LAST_FRONTEND_PORT"; do
        if [ -z "$port" ]; then
            continue
        fi
        if check_port_listening "$port"; then
            log_warn "端口 $port 仍被占用，可能由其他进程使用。"
        fi
    done
fi

log_info "服务已停止。"
