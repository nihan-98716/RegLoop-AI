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
