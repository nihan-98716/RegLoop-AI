# Known Limitations

This document outlines the known constraints and design boundaries of the RegLoop AI prototype. These limitations are intentional and align with the prototype's scope as a single-user proof of concept.

## 1. Single-User / Local Scope
* **No Authentication / RBAC**: The system does not enforce user login, OAuth, or Role-Based Access Control. Anyone with network access to the port can perform reviews or edit pull requests.
* **Workspace Identifiers**: Workspaces are initialized on the client side and saved in the browser's `localStorage`. Clearing browser data will lose access to past local workspaces (though they remain in the SQLite/Postgres database).

## 2. Document Processing and Chunking
* **Keyword Matching Limits**: The deterministic mapping fallback relies on tokenized term overlaps. For very large policies, this can lead to lower precision compared to semantic vector embeddings.
* **Basic PDF Extraction**: PDF parsing is done using standard layout text extraction. PDFs with complex multi-column grid layouts, scanned images (without OCR), or heavy tables may experience text ordering issues.
* **Size Constraints**: The system is tuned for typical compliance excerpts (1–3 policies under 20 pages each). Processing massive regulatory textbooks (>200 pages) is not recommended without scaling the ingestion logic.

## 3. Database & Concurrency
* **SQLite Locking**: The local default database is SQLite. While using `aiosqlite` allows async operations, concurrent writes during heavy import/analysis tasks can occasionally trigger database lock exceptions. 
* **Production Recommendation**: For concurrent or shared usage, switch to the PostgreSQL configuration available in the Docker Compose setup.

## 4. UI Interaction
* **Polled Status**: Analysis pipelines run asynchronously, but progress updates on the frontend are checked via workspace status checks rather than WebSockets.
* **No Direct Git Integration**: Although the system generates "Pull Requests" showing before-and-after policy changes, it does not commit files or push actual branches to GitHub/GitLab. PRs are kept as internal database objects for compliance review.
