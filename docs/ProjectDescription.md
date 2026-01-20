# AutoChat Project Description

## Overview
AutoChat provides a FastAPI backend with multiple agent chat endpoints and a static frontend for interacting with those agents.
Docker Compose is the default dev entrypoint; `scripts/start.sh` wraps `docker compose up` for a consistent stack.

Recent upgrades added a unified orchestrator pipeline (plan → tool execution → synthesis), agent profiles with routing hints,
tool contracts and sanitization, Redis-backed caching for tool reads, and agent run replay logs for audit and evaluation.

## Docker Compose
- Recommended cross-platform dev entrypoint: `cp .env.example .env` then `./scripts/start.sh` (or `docker compose up --build`).
- Services include Postgres, FastAPI backend, and the Vite React frontend.
- Backend health check endpoint: `GET /health`.
- `scripts/start.sh` 会自动选择可用端口并记录到 `.logs/compose-ports.env`。

## React Frontend Notes
- Uses Vite dev server. `VITE_API_URL` points to backend.
- `VITE_ALLOW_GUEST=false` disables guest access.

## Authentication
- Authenticated users get saved conversations and memory summaries.
- Guest mode allows chat without login; guest conversations are not stored in the database or memory.

## Database Merge (Postgres)
- Unified schema now includes knowledge base, courses, and tools tables, plus optional sessions.
- Migration helper: `scripts/migrate_sqlite_to_postgres.py` (reads `database/agent_db.sqlite`).
- Default migration agent for historical chat sessions: `task`.

## Conversation Titles
- Default title is “新对话”.
- After the first assistant reply, titles are auto-generated in Chinese when still using the default.

## Agent Styles
- Each agent exposes two selectable styles in the React UI.
- The style prompt is injected only on the first message or after a style switch.

## Agent Runs & Replay
- Each completed authenticated chat run is recorded in `agent_runs` with plan JSON, tool summary, and final answer.
- Replay data supports evaluation of tool accuracy, groundedness, latency, and cost.
- Logs are written to `.logs/agents.log` for tool calls, plans, and run metadata.

## Demo Account
- Username: demo
- Password: demo@Just

## Environment Variables
- `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`
- Per-agent model credentials: `IDEOLOGICAL_*`, `EVALUATION_*`, `TASK_*`, `EXPLORATION_*`, `COMPETITION_*`, `COURSE_*` (include `*_API_KEY`, `*_BASE_URL`, `*_MODEL`)
- Memory summary credentials: `SUMMARY_API_KEY`, `SUMMARY_BASE_URL`, `SUMMARY_MODEL`
- Optional cache: `REDIS_URL` (tool reads with TTL; falls back gracefully when unavailable)
