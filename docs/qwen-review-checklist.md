# Qwen 3 Review Checklist

Use this checklist before sending the project through Qwen 3 or another external model review.

## Scope Check

- [x] README explains the project goal and setup clearly.
- [x] Functional requirements FR-1 through FR-8 are traceable to implementation.
- [x] Implementation phases are reflected in completed code.
- [x] Known limitations are documented.
- [x] No hidden authentication requirement is introduced.

## Architecture Check

- [x] Frontend, backend, database, AI provider, and file storage boundaries are clear.
- [x] Docker/PostgreSQL setup works from a fresh clone.
- [x] SQLite fallback is documented and tested where claimed.
- [x] Architecture diagram matches actual implementation.

## AI Reliability Check

- [x] LLM prompts are stored or documented.
- [x] AI outputs are schema-validated.
- [x] Citations and confidence scores are shown.
- [x] Human review is required before recommendations are accepted.
- [x] Original AI recommendations are preserved after human modification.

## Compliance Traceability Check

- [x] Every obligation links to a regulatory source.
- [x] Every policy mapping links to a policy excerpt.
- [x] Every gap analysis links to an obligation.
- [x] Every policy PR links to a gap and citation.
- [x] Every review action creates or updates audit history.
- [x] Export includes all major artifacts.

## Test Check

- [x] Backend unit tests pass.
- [x] Backend integration tests pass.
- [x] Frontend workflow tests pass.
- [x] Export tests pass.
- [x] PostgreSQL path has been tested through Docker.
- [x] Sample-data demo path has been tested end to end.

## Security and Privacy Check

- [x] Uploaded files are validated by type and count.
- [x] Secrets are not committed.
- [x] `.env.example` uses placeholders only.
- [x] LLM provider keys are read from environment variables.
- [x] Local development credentials are clearly marked as local-only.

## Demo Readiness Check

- [x] Sample files are included or generation instructions are documented.
- [x] Demo script fits within 3 to 5 minutes.
- [x] Screens show all required workflow artifacts.
- [x] JSON and CSV exports open successfully.
