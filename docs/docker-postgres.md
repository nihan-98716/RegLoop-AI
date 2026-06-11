# Docker and PostgreSQL Plan

## Goal

Use Docker to run PostgreSQL for production-like local development while preserving SQLite as a lightweight test/local option.

## Services

Planned Docker Compose services:

- `postgres`: PostgreSQL database
- `backend`: FastAPI application
- `frontend`: Next.js application
- optional `adminer`: browser-based database inspection

## Environment Variables

Suggested variables:

```env
DATABASE_URL=postgresql+asyncpg://regloop:regloop@postgres:5432/regloop
SQLITE_DATABASE_URL=sqlite:///./regloop.db
UPLOAD_DIR=./storage/uploads
LLM_PROVIDER=openai
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
```

## PostgreSQL Defaults

Suggested local defaults:

- Database: `regloop`
- User: `regloop`
- Password: `regloop`
- Port: `5432`

These values are for local development only and should be changed for deployed environments.

## Database Compatibility

Implementation should avoid database features that make SQLite and PostgreSQL diverge unnecessarily.

Use:

- SQLAlchemy models
- Alembic migrations
- UUIDs stored as strings if portability becomes easier
- UTC timestamps
- Explicit foreign keys

Avoid for the prototype:

- PostgreSQL-only JSONB requirements unless hidden behind compatibility logic
- Database-specific full-text search as a core dependency
- Unportable migration defaults

## Planned Commands

Final setup docs should include commands similar to:

```bash
docker compose up --build
```

Backend-only local development may use SQLite:

```bash
uvicorn app.main:app --reload
```

These commands are placeholders until the application scaffold exists.
