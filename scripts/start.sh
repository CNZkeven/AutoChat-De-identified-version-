#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
PORTS_FILE="$LOG_DIR/compose-ports.env"
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

add_candidate() {
    local value="$1"
    local list_name="$2"
    if [ -z "$value" ]; then
        return 0
    fi
    eval "local existing=(\"\${${list_name}[@]}\")"
    local item
    for item in "${existing[@]}"; do
        if [ "$item" = "$value" ]; then
            return 0
        fi
    done
    eval "${list_name}+=(\"$value\")"
}

find_available_port() {
    local -a candidates=("$@")
    local port
    for port in "${candidates[@]}"; do
        if [ -z "$port" ]; then
            continue
        fi
        if check_port_listening "$port"; then
            continue
        fi
        local status=$?
        if [ "$status" -eq 2 ]; then
            log_warn "无法检查端口 $port（缺少 lsof/nc），尝试继续使用。"
        fi
        echo "$port"
        return 0
    done
    return 1
}

get_compose_port() {
    local service="$1"
    local container_port="$2"
    local mapping
    mapping=$(compose port "$service" "$container_port" 2>/dev/null | head -n1 || true)
    if [ -n "$mapping" ]; then
        echo "${mapping##*:}"
    fi
}

if ! command -v docker >/dev/null 2>&1; then
    log_error "docker 未安装或不可用。请先安装 Docker Desktop。"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    log_error "docker compose 不可用。请升级 Docker Desktop 或安装 Compose v2。"
    exit 1
fi

mkdir -p "$LOG_DIR"

if [ ! -f "$ENV_FILE" ]; then
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    log_info "已从 $EXAMPLE_FILE 创建 $ENV_FILE。"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [ -f "$PORTS_FILE" ]; then
    # shellcheck disable=SC1090
    source "$PORTS_FILE"
fi

DEFAULT_POSTGRES_PORT="${POSTGRES_PORT:-5433}"
DEFAULT_BACKEND_PORT="${BACKEND_PORT:-8000}"
DEFAULT_FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if compose ps --services --status running 2>/dev/null | grep -qx "db"; then
    POSTGRES_PORT="$(get_compose_port db 5432)"
    BACKEND_PORT="$(get_compose_port backend 8000)"
    FRONTEND_PORT="$(get_compose_port frontend 5173)"
fi

if [ -z "${POSTGRES_PORT:-}" ]; then
    candidates=()
    add_candidate "${LAST_POSTGRES_PORT:-}" candidates
    add_candidate "$DEFAULT_POSTGRES_PORT" candidates
    add_candidate "5432" candidates
    add_candidate "15432" candidates
    add_candidate "25432" candidates
    POSTGRES_PORT="$(find_available_port "${candidates[@]}")" || {
        log_error "未找到可用的 Postgres 端口。"
        exit 1
    }
fi

if [ -z "${BACKEND_PORT:-}" ]; then
    candidates=()
    add_candidate "${LAST_BACKEND_PORT:-}" candidates
    add_candidate "$DEFAULT_BACKEND_PORT" candidates
    add_candidate "8001" candidates
    add_candidate "18000" candidates
    BACKEND_PORT="$(find_available_port "${candidates[@]}")" || {
        log_error "未找到可用的后端端口。"
        exit 1
    }
fi

if [ -z "${FRONTEND_PORT:-}" ]; then
    candidates=()
    add_candidate "${LAST_FRONTEND_PORT:-}" candidates
    add_candidate "$DEFAULT_FRONTEND_PORT" candidates
    add_candidate "5174" candidates
    add_candidate "15173" candidates
    FRONTEND_PORT="$(find_available_port "${candidates[@]}")" || {
        log_error "未找到可用的前端端口。"
        exit 1
    }
fi

if check_port_listening "$POSTGRES_PORT" && ! (compose ps --services --status running 2>/dev/null | grep -qx "db"); then
    log_error "端口 $POSTGRES_PORT 已被非本项目进程占用，请更换端口或释放后重试。"
    exit 1
fi

if check_port_listening "$BACKEND_PORT" && ! (compose ps --services --status running 2>/dev/null | grep -qx "backend"); then
    log_error "端口 $BACKEND_PORT 已被非本项目进程占用，请更换端口或释放后重试。"
    exit 1
fi

if check_port_listening "$FRONTEND_PORT" && ! (compose ps --services --status running 2>/dev/null | grep -qx "frontend"); then
    log_error "端口 $FRONTEND_PORT 已被非本项目进程占用，请更换端口或释放后重试。"
    exit 1
fi

export POSTGRES_PORT
export BACKEND_PORT
export FRONTEND_PORT
export VITE_API_URL="http://localhost:${BACKEND_PORT}"

log_info "启动 Docker Compose 全栈服务..."
compose up -d --build

cat > "$PORTS_FILE" <<PORTS
LAST_POSTGRES_PORT=$POSTGRES_PORT
LAST_BACKEND_PORT=$BACKEND_PORT
LAST_FRONTEND_PORT=$FRONTEND_PORT
PORTS

log_info "服务启动完成。"
log_info "Frontend: http://localhost:$FRONTEND_PORT"
log_info "Backend:  http://localhost:$BACKEND_PORT"
log_info "Postgres: localhost:$POSTGRES_PORT"
