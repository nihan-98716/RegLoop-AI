"""File upload validation and storage helpers."""

import hashlib
import os
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.logging_config import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "regulation": {".pdf"},
    "policy": {".pdf"},
    "responsibility_matrix": {".csv"},
}

ALLOWED_CONTENT_TYPES: dict[str, set[str]] = {
    "regulation": {"application/pdf"},
    "policy": {"application/pdf"},
    "responsibility_matrix": {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "text/plain",  # some browsers send CSV as text/plain
    },
}

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_POLICY_COUNT = 3
VALID_TYPES = set(ALLOWED_EXTENSIONS.keys())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_document_type(document_type: str) -> None:
    if document_type not in VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid document_type '{document_type}'. "
                f"Must be one of: {sorted(VALID_TYPES)}"
            ),
        )


def validate_file_extension(file: UploadFile, document_type: str) -> None:
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    allowed = ALLOWED_EXTENSIONS[document_type]
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File '{filename}' has extension '{ext}' which is not allowed "
                f"for document_type '{document_type}'. Expected: {sorted(allowed)}"
            ),
        )


def validate_count_rules(existing_types: list[str], new_type: str) -> None:
    """Enforce per-type upload count limits before accepting a new file."""
    counts = {t: existing_types.count(t) for t in VALID_TYPES}

    if new_type == "regulation" and counts["regulation"] >= 1:
        raise HTTPException(
            status_code=400,
            detail="Only one regulation document is allowed. Remove the existing one first.",
        )
    if new_type == "policy" and counts["policy"] >= MAX_POLICY_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_POLICY_COUNT} policy documents are allowed.",
        )
    if new_type == "responsibility_matrix" and counts["responsibility_matrix"] >= 1:
        raise HTTPException(
            status_code=400,
            detail="Only one responsibility matrix is allowed. Remove the existing one first.",
        )


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


async def save_upload(file: UploadFile, workspace_id: str, document_id: str) -> tuple[str, int, str]:
    """Stream-save an upload and return (storage_path, size_bytes, sha256_hex)."""
    dest_dir = Path(settings.upload_dir) / workspace_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{document_id}_{Path(file.filename or 'file').name}"
    dest = dest_dir / safe_name

    hasher = hashlib.sha256()
    size = 0

    try:
        with open(dest, "wb") as fh:
            while True:
                chunk = await file.read(65_536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_SIZE_BYTES:
                    fh.close()
                    os.unlink(dest)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {MAX_SIZE_BYTES // 1_048_576} MB size limit.",
                    )
                fh.write(chunk)
                hasher.update(chunk)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        if dest.exists():
            os.unlink(dest)
        log.error("upload.save_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.") from exc

    log.info("upload.saved", path=str(dest), size=size)
    return str(dest), size, hasher.hexdigest()


def delete_stored_file(storage_path: str) -> None:
    """Remove a stored file. Silently ignores missing files."""
    try:
        if os.path.exists(storage_path):
            os.unlink(storage_path)
            log.info("upload.deleted", path=storage_path)
    except OSError as exc:
        log.warning("upload.delete_failed", path=storage_path, error=str(exc))


# ---------------------------------------------------------------------------
# Readiness check
# ---------------------------------------------------------------------------


def is_ready_for_analysis(documents: list) -> bool:
    """Return True when all required document types are present and valid."""
    types = [d.document_type for d in documents if d.status == "uploaded"]
    return (
        types.count("regulation") == 1
        and 1 <= types.count("policy") <= MAX_POLICY_COUNT
        and types.count("responsibility_matrix") == 1
    )
