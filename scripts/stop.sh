#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log_info() {
    echo "[stop] $*"
}

log_error() {
    echo "[stop][error] $*" >&2
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
(
    cd "$ROOT_DIR"
    docker compose down
)

log_info "服务已停止。"
