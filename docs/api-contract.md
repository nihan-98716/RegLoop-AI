# API Contract Draft

Base path: `/api`

## Health

### `GET /health`

Returns backend status and database connectivity.

Response:

```json
{
  "status": "ok",
  "database": "ok"
}
```

## Workspaces

### `POST /workspaces`

Creates a review workspace.

### `GET /workspaces/{workspace_id}`

Returns workspace metadata, uploaded document summaries, and analysis status.

## Uploads

### `POST /workspaces/{workspace_id}/documents`

Multipart upload for one document.

Accepted document types:

- `regulation`
- `policy`
- `responsibility_matrix`

Validation rules:

- Exactly one regulation PDF
- One to three policy PDFs
- Exactly one responsibility matrix CSV

### `DELETE /workspaces/{workspace_id}/documents/{document_id}`

Removes an uploaded document and dependent generated artifacts if analysis has not started.

## Analysis

### `POST /workspaces/{workspace_id}/analysis/start`

Starts ingestion and AI analysis when required inputs are present.

Suggested response:

```json
{
  "workspace_id": "uuid",
  "status": "queued"
}
```

### `GET /workspaces/{workspace_id}/analysis/status`

Returns current stage, progress, and errors.

Stages:

- `not_ready`
- `ready`
- `ingesting`
- `extracting_obligations`
- `mapping_policies`
- `analyzing_gaps`
- `generating_prs`
- `ready_for_review`
- `completed`
- `failed`

## Obligations

### `GET /workspaces/{workspace_id}/obligations`

Returns extracted obligations.

## Policy Mappings

### `GET /workspaces/{workspace_id}/policy-mappings`

Returns obligation-to-policy mapping results.

## Gap Analysis

### `GET /workspaces/{workspace_id}/gaps`

Returns coverage status, reasoning, citations, and risk level.

## Policy Pull Requests

### `GET /workspaces/{workspace_id}/policy-pull-requests`

Returns generated policy pull requests.

### `POST /policy-pull-requests/{pr_id}/review`

Records a human review action.

Request:

```json
{
  "action": "approve",
  "reviewer_label": "Compliance Analyst",
  "comment": "Looks correct",
  "modified_text": null
}
```

Allowed actions:

- `approve`
- `reject`
- `modify`
- `escalate`

## Audit

### `GET /workspaces/{workspace_id}/audit`

Returns end-to-end audit records.

## Export

### `GET /workspaces/{workspace_id}/export.json`

Downloads full review package as JSON.

### `GET /workspaces/{workspace_id}/export.csv`

Downloads a flattened CSV export suitable for spreadsheet review.
