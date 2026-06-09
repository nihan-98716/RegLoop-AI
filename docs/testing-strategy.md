# Testing Strategy

## Test Pyramid

- Unit tests for parsing, validation, schemas, and risk helpers.
- Integration tests for API endpoints, database persistence, and exports.
- Workflow tests for the end-to-end review path.
- Manual demo validation with sample PDFs and CSV.

## Backend Tests

Recommended tools:

- `pytest`
- FastAPI test client
- SQLite test database
- Mock LLM provider

Core coverage:

- File validation accepts PDF/CSV and rejects invalid types.
- Upload rules enforce exactly one regulation, one to three policies, and one matrix.
- PDF extraction stores chunks with references.
- CSV parser stores owners.
- LLM JSON schema validation accepts valid output and rejects invalid output.
- Obligations persist with citations and confidence.
- Policy mappings persist with excerpts and confidence.
- Gap analysis persists coverage status, reasoning, and risk.
- Policy PRs are generated only for partial or missing coverage.
- Review actions update PR status and create audit records.
- JSON export includes all workflow artifacts.
- CSV export includes a flattened representation of the same artifacts.

## Frontend Tests

Recommended tools:

- React Testing Library for components
- Playwright for critical workflow tests

Core coverage:

- Upload controls enforce required document groups.
- Analysis button is disabled until required files are present.
- Uploaded file summaries render correctly.
- Obligations table displays source references and confidence.
- Mapping view displays policy excerpts.
- Gap view displays status and risk.
- Policy PR view displays before/after comparison.
- Review actions are available and update visible status.
- Export buttons request JSON and CSV downloads.

## AI Workflow Tests

Use a mock provider with fixed outputs.

Scenarios:

- Valid obligation extraction response.
- Malformed JSON response.
- Obligation missing citation.
- Mapping response with low confidence.
- Gap response for fully covered, partially covered, and not covered cases.
- Policy PR generation with suggested owner.

## Database Tests

Run the same migration/schema tests against:

- SQLite
- PostgreSQL through Docker

Focus:

- UUID portability
- Timestamp defaults
- Foreign key behavior
- Cascade or restricted deletes
- Export query consistency

## Acceptance Test Matrix

| Requirement | Test Type | Required Evidence |
| --- | --- | --- |
| FR-1 Upload Workspace | API, UI, E2E | Valid files shown; missing files block analysis |
| FR-2 Obligation Extraction | Backend, AI mock, UI | Multiple obligations with citations and confidence |
| FR-3 Policy Mapping | Backend, AI mock, UI | Every obligation mapped or marked no-match |
| FR-4 Gap Analysis | Backend, AI mock, UI | Coverage, reasoning, risk, citations |
| FR-5 Policy PR Generator | Backend, UI | Gap PRs with before/after and owner |
| FR-6 Human Review | API, UI, E2E | Approve/reject/modify/escalate persisted |
| FR-7 Audit Memory | Backend, UI | End-to-end audit record exists |
| FR-8 Export | API, E2E | JSON and CSV contain all artifacts |

## Manual Demo Checklist

- Start app through documented commands.
- Upload sample regulation, policies, and matrix.
- Run analysis.
- Show obligations, mappings, gaps, and policy PRs.
- Modify or approve one PR.
- Open audit trail.
- Export JSON and CSV.
