"""Phase 3 document ingestion tests."""

import os
import shutil
import tempfile
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import Base, engine
from app.main import app

TEMP_UPLOAD_DIR = tempfile.mkdtemp()
settings.upload_dir = TEMP_UPLOAD_DIR


@pytest.fixture(scope="module", autouse=True)
def cleanup_uploads() -> Generator[None, None, None]:
    yield
    if os.path.exists(TEMP_UPLOAD_DIR):
        shutil.rmtree(TEMP_UPLOAD_DIR)


@pytest.fixture(autouse=True)
async def reset_db() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_ingestion_extracts_chunks_and_responsibility_owners() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "Phase 3"})).json()["id"]

        reg_pdf = b"%PDF-1.4\nSection 1 Reporting\nThe institution must report material incidents within 72 hours."
        policy_pdf = (
            b"%PDF-1.4\nINCIDENT REPORTING POLICY\nMaterial incidents are escalated to Compliance.\n"
            b"Records are retained for audit review."
        )
        matrix_csv = (
            b"domain,policy_area,owner_name,owner_role,owner_email,notes\n"
            b"Reporting,Incident Reporting,Jordan Lee,Regulatory Reporting Lead,jordan@example.com,Owns regulator notices\n"
        )

        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.pdf", reg_pdf, "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "policy"},
            files={"file": ("policy.pdf", policy_pdf, "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "responsibility_matrix"},
            files={"file": ("matrix.csv", matrix_csv, "text/csv")},
        )

        ingestion_res = await client.post(f"/api/workspaces/{ws_id}/ingestion")
        assert ingestion_res.status_code == 200
        ingestion = ingestion_res.json()
        assert ingestion["status"] == "ingested"
        assert ingestion["document_count"] == 3
        assert ingestion["chunk_count"] >= 2
        assert ingestion["owner_count"] == 1

        status_res = await client.get(f"/api/workspaces/{ws_id}/ingestion")
        assert status_res.status_code == 200
        status = status_res.json()
        assert status["status"] == "ingested"
        assert any("72 hours" in chunk["text"] for chunk in status["chunks"])
        assert any(chunk["section_label"] for chunk in status["chunks"])
        assert status["responsibility_owners"][0]["owner_name"] == "Jordan Lee"
        assert status["responsibility_owners"][0]["policy_area"] == "Incident Reporting"


@pytest.mark.asyncio
async def test_ingestion_requires_ready_workspace() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "Not Ready"})).json()["id"]
        response = await client.post(f"/api/workspaces/{ws_id}/ingestion")

    assert response.status_code == 400
    assert "Workspace must include" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingestion_rejects_matrix_missing_required_columns() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "Bad Matrix"})).json()["id"]
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.pdf", b"%PDF-1.4\nRegulatory text", "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "policy"},
            files={"file": ("policy.pdf", b"%PDF-1.4\nPolicy text", "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "responsibility_matrix"},
            files={"file": ("matrix.csv", b"domain,owner_name\nReporting,Jordan Lee\n", "text/csv")},
        )

        response = await client.post(f"/api/workspaces/{ws_id}/ingestion")

    assert response.status_code == 422
    assert "missing columns" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingestion_rollback_on_pdf_parse_error() -> None:
    """Test that a failed ingestion rolls back the DB and does not leave partial chunks.

    Simulates a corrupt/unreadable PDF to verify the transaction rollback path
    in run_ingestion and ensures no orphaned DocumentChunk rows are written.
    """
    from unittest.mock import patch
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "Rollback Test"})).json()["id"]
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.pdf", b"%PDF-1.4\nsome content", "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "policy"},
            files={"file": ("policy.pdf", b"%PDF-1.4\nsome policy", "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "responsibility_matrix"},
            files={"file": ("matrix.csv", b"domain,policy_area,owner_name,owner_role,owner_email,notes\nData,Privacy,Jane,DPO,j@e.com,\n", "text/csv")},
        )

        # Simulate a crash during chunking
        with patch(
            "app.routers.ingestion.chunk_pdf_document",
            side_effect=RuntimeError("Simulated PDF parse failure"),
        ):
            response = await client.post(f"/api/workspaces/{ws_id}/ingestion")

        # Server should return 500, not silently succeed
        assert response.status_code == 500

        # Verify no chunks were persisted (rollback succeeded)
        status = await client.get(f"/api/workspaces/{ws_id}/ingestion")
        assert status.json()["chunks"] == []


@pytest.mark.asyncio
async def test_audit_log_endpoint_returns_ordered_events() -> None:
    """Test that the audit log endpoint returns events in chronological order.

    Verifies that after running the ingestion step, the audit log includes
    a 'document_uploaded' event and an 'ingestion_run' event in the correct order.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "Audit Test"})).json()["id"]
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.pdf", b"%PDF-1.4\nThe firm must report incidents.", "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "policy"},
            files={"file": ("policy.pdf", b"%PDF-1.4\nPolicy text.", "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "responsibility_matrix"},
            files={"file": ("matrix.csv", b"domain,policy_area,owner_name,owner_role,owner_email,notes\nData,Privacy,Jane,DPO,j@e.com,\n", "text/csv")},
        )
        await client.post(f"/api/workspaces/{ws_id}/ingestion")

        audit_res = await client.get(f"/api/workspaces/{ws_id}/audit")
        assert audit_res.status_code == 200
        events = audit_res.json()

        # Must have at least document upload + ingestion events
        assert len(events) >= 2

        # Events must be returned in chronological order
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps), "Audit events are not in chronological order"

        # Must contain expected event types
        event_types = [e["event_type"] for e in events]
        assert "document_uploaded" in event_types
        assert "ingestion_run" in event_types
