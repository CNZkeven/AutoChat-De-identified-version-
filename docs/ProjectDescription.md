# AutoChat Project Description

## Overview
AutoChat provides a FastAPI backend with multiple agent chat endpoints and a static frontend for interacting with those agents.

## Authentication
- Authenticated users get saved conversations and memory summaries.
- Guest mode allows chat without login; guest conversations are not stored in the database or memory.

## Demo Account
- Username: demo
- Password: demo@Just

## Environment Variables
- `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`
- Per-agent model credentials: `IDEOLOGICAL_*`, `EVALUATION_*`, `TASK_*`, `EXPLORATION_*`, `COMPETITION_*`, `COURSE_*` (include `*_API_KEY`, `*_BASE_URL`, `*_MODEL`)
- Memory summary credentials: `SUMMARY_API_KEY`, `SUMMARY_BASE_URL`, `SUMMARY_MODEL`
