# AutoChat

## Overview
AutoChat is a full-stack app with a React (Vite) frontend, a FastAPI backend, and a Postgres database.

## Quick Start (Docker, recommended)
1. Install Docker Desktop.
2. Create a local env file:
   - macOS/Linux: `cp .env.example .env`
   - Windows PowerShell: `Copy-Item .env.example .env`
3. Start the stack:
   - `docker compose up --build`

After startup:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health

## Daily Development
- Start only Postgres: `docker compose up -d db`
- Rebuild a service: `docker compose build backend`
- View logs: `docker compose logs -f backend`
- Stop services: `docker compose down`

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
- Start everything locally (React + FastAPI + Postgres): `./scripts/start.sh`
- Stop services: `./scripts/stop.sh`
- Backend env file: `backend/.env` (see `backend/.env.example` for a full list).

## Developer scripts
- macOS/Linux: `./scripts/dev.sh`
- Windows PowerShell: `.\scripts\dev.ps1`

## Lint / build
- `./scripts/lint.sh`
- `./scripts/build.sh`
