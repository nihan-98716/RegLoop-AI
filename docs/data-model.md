# Data Model Draft

The schema should support both SQLite and PostgreSQL. Use UUID strings for identifiers to keep portability simple.

## Core Entities

### Workspace

Represents one compliance review package.

Fields:

- `id`
- `name`
- `status`
- `created_at`
- `updated_at`

### Document

Represents an uploaded regulatory PDF, policy PDF, or responsibility matrix CSV.

Fields:

- `id`
- `workspace_id`
- `document_type`: `regulation`, `policy`, `responsibility_matrix`
- `filename`
- `content_type`
- `storage_path`
- `size_bytes`
- `checksum`
- `status`
- `created_at`

### DocumentChunk

Normalized extracted text from a PDF.

Fields:

- `id`
- `document_id`
- `chunk_index`
- `page_number`
- `section_label`
- `text`
- `created_at`

### ResponsibilityOwner

Parsed row from the responsibility matrix.

Fields:

- `id`
- `workspace_id`
- `domain`
- `policy_area`
- `owner_name`
- `owner_role`
- `owner_email`
- `notes`

### Obligation

Structured regulatory obligation extracted by AI.

Fields:

- `id`
- `workspace_id`
- `statement`
- `source_document_id`
- `source_reference`
- `source_excerpt`
- `compliance_domain`
- `confidence`
- `model_name`
- `created_at`

### PolicyMapping

Links an obligation to a policy section or chunk.

Fields:

- `id`
- `obligation_id`
- `policy_document_id`
- `document_chunk_id`
- `policy_excerpt`
- `mapping_rationale`
- `confidence`
- `created_at`

### GapAnalysis

Coverage assessment for an obligation.

Fields:

- `id`
- `obligation_id`
- `coverage_status`: `fully_covered`, `partially_covered`, `not_covered`
- `risk_level`: `high`, `medium`, `low`
- `reasoning`
- `source_citations`
- `confidence`
- `created_at`

### PolicyPullRequest

Reviewable AI-generated policy amendment.

Fields:

- `id`
- `workspace_id`
- `obligation_id`
- `gap_analysis_id`
- `title`
- `gap_description`
- `proposed_amendment`
- `regulatory_citation`
- `suggested_owner_id`
- `risk_level`
- `confidence`
- `before_text`
- `after_text`
- `status`: `pending`, `approved`, `rejected`, `modified`, `escalated`
- `created_at`
- `updated_at`

### ReviewAction

Human action taken on a policy pull request.

Fields:

- `id`
- `policy_pull_request_id`
- `action`: `approve`, `reject`, `modify`, `escalate`
- `reviewer_label`
- `comment`
- `modified_text`
- `created_at`

### AuditRecord

Traceable record of workflow state and final decisions.

Fields:

- `id`
- `workspace_id`
- `obligation_id`
- `policy_mapping_id`
- `gap_analysis_id`
- `policy_pull_request_id`
- `review_action_id`
- `responsible_owner_id`
- `event_type`
- `summary`
- `created_at`

## Export View

The export package should join:

- Workspace metadata
- Documents
- Obligations
- Policy mappings
- Gap analyses
- Policy pull requests
- Review actions
- Audit records
