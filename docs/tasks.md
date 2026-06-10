# Task Backlog

## Legend

- `P0`: Required for the prototype to meet the challenge brief
- `P1`: Strongly recommended for demo quality
- `P2`: Nice to have if time remains

## Phase 0: Planning

- [x] P0: Capture project brief
- [x] P0: Define phased implementation plan
- [x] P0: Define architecture draft
- [x] P0: Define data model draft
- [x] P0: Define API contract draft
- [x] P0: Define AI workflow draft
- [x] P0: Define testing strategy
- [x] P0: Define Docker/PostgreSQL plan
- [x] P0: Define Qwen 3 review checklist

## Phase 1: Application Skeleton

- [x] P0: Create frontend Next.js app
- [x] P0: Create backend FastAPI app
- [x] P0: Add common `.env.example`
- [x] P0: Add Docker Compose
- [x] P0: Add backend database settings for SQLite and PostgreSQL
- [x] P0: Add health endpoint
- [x] P1: Add backend structured logging
- [x] P1: Add frontend API client helper

## Phase 2: Upload Workspace

- [ ] P0: Build upload workspace screen
- [ ] P0: Support one regulatory PDF upload
- [ ] P0: Support one to three policy PDF uploads
- [ ] P0: Support one responsibility matrix CSV upload
- [ ] P0: Validate file type and required file counts
- [ ] P0: Persist document metadata
- [ ] P0: Display uploaded file summaries
- [ ] P0: Support remove and replace
- [ ] P0: Disable analysis until required inputs exist

## Phase 3: Document Ingestion

- [ ] P0: Extract text from regulatory PDFs
- [ ] P0: Extract text from policy PDFs
- [ ] P0: Chunk policy text into sections
- [ ] P0: Parse responsibility matrix CSV
- [ ] P0: Persist document chunks and owner rows
- [ ] P1: Capture page numbers and section labels where available
- [ ] P1: Show ingestion status in UI

## Phase 4: Obligation Extraction

- [ ] P0: Create obligation extraction prompt
- [ ] P0: Define obligation output schema
- [ ] P0: Validate LLM output against schema
- [ ] P0: Persist obligations
- [ ] P0: Display obligations table
- [ ] P0: Show citation and confidence per obligation
- [ ] P1: Add retry or repair path for malformed model output

## Phase 5: Policy Mapping

- [ ] P0: Retrieve candidate policy chunks for each obligation
- [ ] P0: Create policy mapping prompt
- [ ] P0: Persist mapping results
- [ ] P0: Display mapped policy sections and excerpts
- [ ] P0: Show mapping confidence
- [ ] P1: Clearly flag no-match or low-confidence mappings

## Phase 6: Gap Analysis

- [ ] P0: Create gap analysis prompt
- [ ] P0: Persist coverage status
- [ ] P0: Persist gap reasoning
- [ ] P0: Persist risk level
- [ ] P0: Display gap results by obligation
- [ ] P1: Add deterministic risk fallback rules

## Phase 7: Policy Pull Requests

- [ ] P0: Generate PRs for partial or missing coverage
- [ ] P0: Include gap description
- [ ] P0: Include proposed amendment
- [ ] P0: Include regulatory citation
- [ ] P0: Include suggested owner
- [ ] P0: Include risk and confidence
- [ ] P0: Include before and after comparison
- [ ] P1: Allow filtering PRs by status, owner, and risk

## Phase 8: Human Review and Audit

- [ ] P0: Implement approve action
- [ ] P0: Implement reject action
- [ ] P0: Implement modify action
- [ ] P0: Implement escalate action
- [ ] P0: Persist review status
- [ ] P0: Record reviewer action events
- [ ] P0: Generate audit records
- [ ] P0: Display audit trail
- [ ] P1: Preserve original recommendation after modification

## Phase 9: Export and Demo

- [ ] P0: Export full review package as JSON
- [ ] P0: Export full review package as CSV
- [ ] P0: Add sample regulatory PDF
- [ ] P0: Add sample policy PDFs
- [ ] P0: Add sample responsibility matrix CSV
- [ ] P0: Write setup instructions
- [ ] P0: Add architecture diagram
- [ ] P1: Write demo video script

## Phase 10: Review Hardening

- [ ] P0: Run unit tests
- [ ] P0: Run backend integration tests
- [ ] P0: Run frontend workflow tests
- [ ] P0: Run export validation tests
- [ ] P0: Complete requirement traceability matrix
- [ ] P0: Complete Qwen 3 review checklist
- [ ] P1: Document known limitations
