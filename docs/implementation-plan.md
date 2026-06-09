# Implementation Plan

## Guiding Principles

- Build a working end-to-end prototype before optimizing internals.
- Preserve human approval and traceability at every AI-generated decision point.
- Treat LLM outputs as structured recommendations, not authoritative compliance decisions.
- Keep database access portable between SQLite and PostgreSQL.
- Use Docker for PostgreSQL and local service orchestration.
- Keep the AI layer provider-neutral so the prototype can run with OpenAI, Claude, or Gemini.

## Phase 0: Planning and Project Scaffold

Goal: Convert the challenge brief into an implementation-ready plan.

Deliverables:

- README
- Project brief
- Phased implementation plan
- Task backlog
- Architecture notes
- Data model draft
- API contract draft
- AI workflow design
- Testing strategy
- Docker/PostgreSQL plan
- Qwen 3 review checklist

Exit criteria:

- Planning docs are internally consistent.
- All functional requirements FR-1 through FR-8 are mapped to tasks and tests.
- No application implementation has started.

## Phase 1: Application Skeleton

Goal: Create a runnable full-stack baseline.

Deliverables:

- Next.js frontend app scaffold
- FastAPI backend scaffold
- Shared environment configuration
- Docker Compose with backend, frontend, and PostgreSQL services
- SQLite fallback for local backend tests
- Basic health endpoints and landing workspace route

Exit criteria:

- Frontend starts locally.
- Backend starts locally.
- Backend can connect to SQLite and PostgreSQL.
- Health check passes.

## Phase 2: Upload Workspace

Goal: Implement FR-1.

Deliverables:

- Upload UI for regulatory PDF, policy PDFs, and responsibility matrix CSV
- Backend upload endpoints
- File validation
- Document metadata persistence
- Remove and replace behavior
- Analysis readiness state

Exit criteria:

- Analysis cannot begin until all required inputs are present.
- Uploaded file summaries are visible.
- Invalid file type and invalid count errors are handled.

## Phase 3: Document Ingestion

Goal: Convert uploaded documents into normalized text units.

Deliverables:

- PDF text extraction
- Policy document section chunking
- Regulatory document citation extraction strategy
- Responsibility matrix CSV parsing
- Ingestion status tracking

Exit criteria:

- Regulatory and policy text can be retrieved by document, page, section, and chunk.
- CSV owners can be matched by domain, policy, or responsibility keyword.

## Phase 4: Obligation Extraction

Goal: Implement FR-2.

Deliverables:

- LLM prompt for structured obligation extraction
- JSON schema validation for extracted obligations
- Obligation persistence
- Obligation table in UI
- Confidence and citation display

Exit criteria:

- Multiple obligations are extracted from sample regulatory PDFs.
- Invalid LLM JSON is rejected or repaired safely.
- Every obligation has a source reference.

## Phase 5: Policy Mapping

Goal: Implement FR-3.

Deliverables:

- Policy section retrieval strategy
- LLM prompt for obligation-to-policy mapping
- Mapping result persistence
- UI display of mapped excerpts and confidence

Exit criteria:

- Every obligation receives a mapping attempt.
- Supporting policy excerpts are visible.
- Low-confidence or missing mappings are clearly marked.

## Phase 6: Gap Analysis

Goal: Implement FR-4.

Deliverables:

- LLM prompt for coverage assessment
- Coverage statuses: Fully Covered, Partially Covered, Not Covered
- Risk rating logic
- Gap reasoning persistence and UI

Exit criteria:

- Every obligation has a coverage status.
- Gap reasoning includes source-aware explanation.
- Risk ratings are present for partial or missing coverage.

## Phase 7: Policy Pull Request Generator

Goal: Implement FR-5.

Deliverables:

- Policy PR generation prompt
- Suggested owner lookup from responsibility matrix
- Before and after comparison model
- Review package UI

Exit criteria:

- Policy PRs are generated only for detected gaps.
- Each PR includes amendment text, citation, owner, risk, confidence, and before/after comparison.

## Phase 8: Human Review Workflow and Audit Memory

Goal: Implement FR-6 and FR-7.

Deliverables:

- Approve, reject, modify, and escalate actions
- Review status persistence
- Reviewer action log
- Audit trail generation
- Audit history UI

Exit criteria:

- Review actions persist after refresh.
- Audit records connect source regulation to final decision.
- Modified recommendations preserve original AI suggestion.

## Phase 9: Export and Demo Readiness

Goal: Implement FR-8 and prepare final deliverables.

Deliverables:

- JSON export
- CSV export
- Seed/sample input data
- Setup instructions
- Architecture diagram
- Demo script for 3 to 5 minute video

Exit criteria:

- Export contains obligations, mappings, gaps, policy PRs, review decisions, and audit records.
- Fresh setup can run from documented commands.
- Demo flow uses sample data end to end.

## Phase 10: Hardening and Qwen 3 Review

Goal: Prepare for external AI/code review.

Deliverables:

- Requirement traceability check
- Test result summary
- Known limitations
- Security and privacy notes
- Qwen 3 review checklist completion

Exit criteria:

- Qwen 3 can evaluate the repository from docs, code, tests, and setup instructions.
- Any known gaps are explicitly documented.
