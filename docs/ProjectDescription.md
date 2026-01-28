# AutoChat Project Description

## Overview
AutoChat provides a FastAPI backend with multiple agent chat endpoints and a React frontend in `frontend-react` for interacting with those agents.
Docker Compose is the default dev entrypoint; `scripts/start.sh` wraps `docker compose up` for a consistent stack.

Recent upgrades added a unified orchestrator pipeline (plan → tool execution → synthesis), agent profiles with routing hints,
tool contracts and sanitization, Redis-backed caching for tool reads, and agent run replay logs for audit and evaluation.
Academic data now syncs from Achieve into the local dm schema, and agents read via internal dm tools (no external API calls).
课程/学业查询工具已扩展结构化过滤参数（专业/版本/课程性质/类别/课程名/课程号），并补充学业成绩的 list_scores 能力，
同时完善了工具日志与回放记录的序列化稳定性。
新增管理员用户管理与用户个人中心：支持批量导入、筛选编辑、画像与学业展示，以及用户侧毕业要求与报告生成。

## Docker Compose
- Recommended cross-platform dev entrypoint: `cp .env.example .env` then `./scripts/start.sh` (or `docker compose up --build`).
- Services include Postgres, FastAPI backend, and the Vite React frontend.
- Backend health check endpoint: `GET /health`.
- `scripts/start.sh` 会在 5433-5499 范围内自动选择可用端口并记录到 `.logs/compose-ports.env`。
- 前端端口固定为 5174，若被占用会在启动前清理占用进程。

## React Frontend Notes
- Frontend is implemented only in `frontend-react` (legacy `frontend` directory removed).
- Uses Vite dev server. `VITE_API_URL` points to backend.
- Dev frontend port defaults to 5174 to avoid conflicts with other local services.
- `VITE_ALLOW_GUEST=false` disables guest access.

## Authentication
- Authenticated users get saved conversations and memory summaries.
- Guest mode allows chat without login; guest conversations are not stored in the database or memory.

## Database Merge (Postgres)
- Unified schema now includes knowledge base, courses, and tools tables, plus optional sessions.
- SQLite 迁移脚本已移除；数据维护脚本统一放在 `backend/app/maintenance`。

## Conversation Titles
- Default title is “新对话”.
- After the first assistant reply, titles are auto-generated in Chinese when still using the default.

## Agent Styles
- Each agent exposes two selectable styles in the React UI.
- The style prompt is injected only on the first message or after a style switch.

## Agent Runs & Replay
- Each completed authenticated chat run is recorded in `agent_runs` with plan JSON, tool summary, and final answer.
- Full debug traces are recorded in `agent_run_traces`, including assembled prompts, tool calls, tool results, and final responses.
- Replay data supports evaluation of tool accuracy, groundedness, latency, and cost.
- Logs are written to `.logs/agents.log` for tool calls, plans, and run metadata.

## Admin Debug Console
- Admin UI: React route `/admin` (用户管理 + 智能体调试).
- Admin APIs: `/api/admin/*` provide user/agent listings, conversation runs, and trace details.
- 用户管理新增：批量导入模板下载、学号/姓名搜索、专业/年级/性别筛选、基本信息编辑、密码重置、画像与学业详情。
- Debug run endpoint: `POST /api/admin/debug/run` executes a test command as the selected user and stores a full trace.
- DM 同步触发：`POST /api/admin/dm-sync` 由管理员手动触发 Achieve 同步任务。
- Prompt template location is exposed via admin agent metadata; system prompts live in `backend/app/services/agent_prompts.py`.

## Data Mart (dm) APIs
- `GET /api/dm/me/sections` for the current student's enrolled offerings.
- `GET /api/dm/me/scores` for the current student's scores.
- `GET /api/dm/me/sections/{offering_id}/summary` for enrolled section summaries.
- 用户个人中心 API: `/api/profile/*`（画像、学业列表、课程目标、毕业要求与学业报告）。
- 管理端学业 API: `/api/admin/users/{user_id}/academics` 与 `/api/admin/users/{user_id}/courses/{offering_id}/objectives`。

## Demo Account
- Username: demo
- Password: demo@Just
- Admin: admin / admin@Just

## Environment Variables
- `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`
- Achieve sync: `ACHIEVE_DB_DSN`, `SYNC_TERM_WINDOW`, `SYNC_BATCH_SIZE`, `SYNC_SCHEDULE_CRON`
- Per-agent model credentials: `IDEOLOGICAL_*`, `EVALUATION_*`, `TASK_*`, `EXPLORATION_*`, `COMPETITION_*`, `COURSE_*` (include `*_API_KEY`, `*_BASE_URL`, `*_MODEL`)
- Memory summary credentials: `SUMMARY_API_KEY`, `SUMMARY_BASE_URL`, `SUMMARY_MODEL`
- Profiles: `SYSTEM_PROFILE_API_KEY`, `SYSTEM_PROFILE_BASE_URL`, `SYSTEM_PROFILE_MODEL`, `USER_PROFILE_API_KEY`, `USER_PROFILE_BASE_URL`, `USER_PROFILE_MODEL`
- Reports: `REPORT_API_KEY`, `REPORT_BASE_URL`, `REPORT_MODEL`
- Optional cache: `REDIS_URL` (tool reads with TTL; falls back gracefully when unavailable)
