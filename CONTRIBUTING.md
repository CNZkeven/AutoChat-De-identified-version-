# Contributing

## Branching strategy
- Create feature branches off the default branch.
- Keep branches focused and short-lived.

## Pull request checklist
- Include a clear summary of changes.
- Note any scripts you ran (lint/build).
- Add UI screenshots for frontend changes.

## Local development
- Prefer Docker Compose for a consistent environment: `docker compose up --build`.
- Use `./scripts/start.sh` for non-Docker local runs when needed.

## Code style
- Backend: Ruff rules via `./scripts/lint.sh`.
- Frontend: ESLint via `npm run lint:frontend` or `./scripts/lint.sh`.

## Builds
- `./scripts/build.sh`
