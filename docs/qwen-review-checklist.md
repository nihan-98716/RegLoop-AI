# Qwen 3 Review Checklist

Use this checklist before sending the project through Qwen 3 or another external model review.

## Scope Check

- [ ] README explains the project goal and setup clearly.
- [ ] Functional requirements FR-1 through FR-8 are traceable to implementation.
- [ ] Implementation phases are reflected in completed code.
- [ ] Known limitations are documented.
- [ ] No hidden authentication requirement is introduced.

## Architecture Check

- [ ] Frontend, backend, database, AI provider, and file storage boundaries are clear.
- [ ] Docker/PostgreSQL setup works from a fresh clone.
- [ ] SQLite fallback is documented and tested where claimed.
- [ ] Architecture diagram matches actual implementation.

## AI Reliability Check

- [ ] LLM prompts are stored or documented.
- [ ] AI outputs are schema-validated.
- [ ] Citations and confidence scores are shown.
- [ ] Human review is required before recommendations are accepted.
- [ ] Original AI recommendations are preserved after human modification.

## Compliance Traceability Check

- [ ] Every obligation links to a regulatory source.
- [ ] Every policy mapping links to a policy excerpt.
- [ ] Every gap analysis links to an obligation.
- [ ] Every policy PR links to a gap and citation.
- [ ] Every review action creates or updates audit history.
- [ ] Export includes all major artifacts.

## Test Check

- [ ] Backend unit tests pass.
- [ ] Backend integration tests pass.
- [ ] Frontend workflow tests pass.
- [ ] Export tests pass.
- [ ] PostgreSQL path has been tested through Docker.
- [ ] Sample-data demo path has been tested end to end.

## Security and Privacy Check

- [ ] Uploaded files are validated by type and count.
- [ ] Secrets are not committed.
- [ ] `.env.example` uses placeholders only.
- [ ] LLM provider keys are read from environment variables.
- [ ] Local development credentials are clearly marked as local-only.

## Demo Readiness Check

- [ ] Sample files are included or generation instructions are documented.
- [ ] Demo script fits within 3 to 5 minutes.
- [ ] Screens show all required workflow artifacts.
- [ ] JSON and CSV exports open successfully.
