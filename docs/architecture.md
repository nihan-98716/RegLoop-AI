# Architecture

## System Context

RegLoop AI is a local/prototype web application with a Next.js frontend, FastAPI backend, relational database, local file storage, and an LLM provider.

![RegLoop AI System Architecture Diagram](file:///C:/Users/Public/Projects/RegLoop%20AI/docs/architecture_diagram.png)

```mermaid
flowchart LR
    Analyst[Compliance Analyst] --> UI[Next.js UI]
    UI --> API[FastAPI Backend]
    API --> DB[(SQLite or PostgreSQL)]
    API --> Files[(Uploaded Files)]
    API --> LLM[LLM Provider]
    API --> Export[JSON and CSV Export]
```

## Backend Modules

- Uploads: validates PDFs and CSV, stores metadata, supports replacement.
- Ingestion: extracts PDF text, parses CSV, chunks policy text.
- AI Orchestration: calls LLM providers and validates structured outputs.
- Obligations: persists extracted regulatory obligations.
- Mapping: maps obligations to policy sections.
- Gap Analysis: evaluates coverage and risk.
- Policy PRs: generates reviewable policy amendments.
- Review: persists human decisions and modifications.
- Audit: creates traceable history records.
- Export: produces JSON and CSV review packages.

## Frontend Screens

- Workspace: upload required inputs and show readiness.
- Analysis Progress: show current processing stage and errors.
- Obligations: table of extracted obligations.
- Policy Mapping: obligation-by-obligation policy matches.
- Gap Analysis: coverage and risk view.
- Policy Pull Requests: reviewable before/after recommendations.
- Human Review: approve, reject, modify, escalate.
- Audit Trail: end-to-end traceability.
- Export: download JSON or CSV package.

## Data Flow

```mermaid
flowchart TD
    A[Upload inputs] --> B[Validate files]
    B --> C[Extract text and parse CSV]
    C --> D[Extract obligations]
    D --> E[Map policies]
    E --> F[Analyze gaps]
    F --> G[Generate policy PRs]
    G --> H[Human review]
    H --> I[Audit trail]
    I --> J[Export package]
```

## Deployment Shape

Development can run with local processes and SQLite. Production-like demo runs should use Docker Compose with PostgreSQL:

- `frontend`: Next.js app
- `backend`: FastAPI app
- `postgres`: PostgreSQL database
- optional `adminer` or similar database inspection service

## Key Design Decisions

- No authentication because the challenge specifies a single-user prototype.
- Use relational persistence for traceability and export consistency.
- Store uploaded files separately from extracted normalized text.
- Validate all model outputs against explicit schemas before persisting.
- Keep LLM provider integration behind a small interface.
