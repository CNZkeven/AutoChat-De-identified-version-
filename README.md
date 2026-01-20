# AutoChat

## Overview
AutoChat is a full-stack app with a React (Vite) frontend, a FastAPI backend, and a Postgres database.

## Quick Start (Docker, recommended)
1. Install Docker Desktop.
2. Create a local env file:
   - macOS/Linux: `cp .env.example .env`
   - Windows PowerShell: `Copy-Item .env.example .env`
3. Start the stack:
   - macOS/Linux: `./scripts/start.sh`
   - Windows PowerShell: `.\scripts\dev.ps1`
   - or `docker compose up --build`

After startup:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health
- Postgres: localhost:5433（默认，脚本会自动选择可用端口）

## Daily Development
- Start only Postgres: `docker compose up -d db`
- Rebuild a service: `docker compose build backend`
- View logs: `docker compose logs -f backend`
- Stop services: `./scripts/stop.sh` or `docker compose down`
- 端口自动选择记录在 `.logs/compose-ports.env`

## Database initialization / migrations
- This project does not use Alembic yet.
- Tables are created on backend startup via SQLAlchemy metadata.
- To reset local data: `docker compose down -v` (destroys the Postgres volume).

## Windows troubleshooting
- Port conflicts: update `POSTGRES_PORT`, `BACKEND_PORT`, or `FRONTEND_PORT` in `.env`.
- File sharing/performance: ensure the repo directory is shared in Docker Desktop settings.
- Script execution policy: if PowerShell blocks scripts, run
  `Set-ExecutionPolicy -Scope Process Bypass` and then `.\scripts\dev.ps1`.

## Local development (without Docker)
- 当前推荐使用 Docker Compose；如需本机直跑，请自行配置 `backend/.env` 与依赖版本。

## Developer scripts
- macOS/Linux: `./scripts/dev.sh`
- Windows PowerShell: `.\scripts\dev.ps1`

## Lint / build
- `./scripts/lint.sh`
- `./scripts/build.sh`
