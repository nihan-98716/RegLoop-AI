# RegLoop AI

RegLoop AI is a single-user prototype for turning regulatory change into a structured compliance review package.

Target workflow:

1. Upload one regulatory PDF, one to three internal policy PDFs, and one responsibility matrix CSV.
2. Extract structured regulatory obligations with citations and confidence scores.
3. Map obligations to relevant internal policy sections.
4. Detect coverage gaps and assign risk ratings.
5. Generate reviewable policy pull requests for gaps.
6. Route recommendations through human review.
7. Preserve an audit trail.
8. Export the full review package as JSON and CSV.

This repository currently contains project planning documentation only. Implementation should proceed in the phases defined in [docs/implementation-plan.md](docs/implementation-plan.md).

## Proposed Stack

- Frontend: Next.js, React, TypeScript
- Backend: Python, FastAPI
- Database: SQLite for local quick-start, PostgreSQL through Docker for production-like runs
- AI layer: OpenAI, Claude, or Gemini through a provider abstraction
- File processing: PDF text extraction and CSV parsing on the backend

## Planning Docs

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

## Current Boundary

No application source code has been generated yet. The next step is to review these docs, then begin Phase 1 implementation only after approval.
