# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Start all services (PostgreSQL, backend on :8000, frontend on :5173)
./scripts/start.sh

# Stop all services
./scripts/stop.sh

# Lint all code (Python + JavaScript)
./scripts/lint.sh

# Build/verify
./scripts/build.sh

# Lint Python only
python3 -m ruff check backend/app/

# Lint JavaScript only
npm run lint:frontend
```

## Architecture

AutoChat is a multi-agent educational AI chat application.

**Backend** (`backend/app/`):
- FastAPI application with SQLAlchemy ORM
- PostgreSQL database (psycopg driver)
- JWT authentication (python-jose) with bcrypt password hashing
- OpenAI-compatible API client for AI (SiliconFlow with Qwen2.5-7B models)
- SSE streaming responses for real-time chat

**Frontend** (`frontend/`):
- Vanilla HTML/CSS/JavaScript (no framework)
- Each agent has its own HTML page + JS file
- Shared logic in `js/auth.js` (authentication) and `js/chat-common.js` (chat functionality)

**Key Backend Files**:
- `main.py` - FastAPI app, CORS, startup
- `models.py` - SQLAlchemy models (User, Conversation, Message, MemorySummary, UserProfile)
- `security.py` - JWT token creation/validation, password hashing
- `routers/auth.py` - `/api/auth/*` endpoints
- `routers/conversations.py` - `/api/conversations/*` endpoints
- `routers/chat.py` - `/api/agents/{agent}/chat` streaming endpoint
- `services/ai.py` - OpenAI API streaming calls

## Agent Types

Six specialized agents: `ideological`, `evaluation`, `task`, `exploration`, `competition`, `course`

Each agent uses the same fine-tuned model but with different system prompts. Agent config is in `backend/app/routers/chat.py:AGENT_CONFIG`.

## Environment Setup

1. Copy `backend/.env.example` to `backend/.env`
2. Set `OPENAI_API_KEY` (required for AI functionality)
3. Optionally configure `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`

**Requirements**: Python 3.11, Node.js 20, PostgreSQL
