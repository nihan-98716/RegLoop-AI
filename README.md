# RegLoop AI

RegLoop AI is a single-user prototype for turning regulatory change into a structured compliance review package.

## Workflow

1. Upload one regulatory PDF, one to three internal policy PDFs, and one responsibility matrix CSV.
2. Extract structured regulatory obligations with citations and confidence scores.
3. Map obligations to relevant internal policy sections.
4. Detect coverage gaps and assign risk ratings.
5. Generate reviewable policy pull requests for gaps.
6. Route recommendations through human review.
7. Preserve an audit trail.
8. Export the full review package as JSON and CSV.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React, TypeScript |
| Backend | Python 3.12, FastAPI |
| Database | SQLite (local) / PostgreSQL (Docker) |
| ORM | SQLAlchemy 2 + Alembic |
| AI Layer | OpenAI / Claude / Gemini (provider abstraction) |

## Quick Start — Local Development

### Prerequisites

- Node.js 20+
- Python 3.12+
- npm

### Backend (SQLite, no Docker)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env      # edit if needed
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
cp ../.env.example .env.local   # or create with NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

## Docker Compose (PostgreSQL)

```bash
cp .env.example .env    # fill in API keys
docker compose up --build
```

Services:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Adminer | http://localhost:8080 (run with `--profile tools`) |

## Environment Variables

See [`.env.example`](.env.example) for all configuration options.

## Project Docs

- [Project brief](docs/project-brief.md)
- [Implementation plan](docs/implementation-plan.md)
- [Task backlog](docs/tasks.md)
- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [API contract](docs/api-contract.md)
- [AI workflow](docs/ai-workflow.md)
- [Testing strategy](docs/testing-strategy.md)
- [Docker and PostgreSQL plan](docs/docker-postgres.md)
- [Sample data plan](docs/sample-data-plan.md)
- [Qwen 3 review checklist](docs/qwen-review-checklist.md)
- [Setup instructions](docs/setup-instructions.md)
- [Demo video script](docs/demo-script.md)
