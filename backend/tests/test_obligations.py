"""Phase 4 obligation extraction tests."""

import os
import shutil
import tempfile
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.services.obligations import (
    parse_obligation_provider_output,
    validate_obligation_payload,
)

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
async def test_extract_obligations_after_ingestion() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "Phase 4"})).json()["id"]

        regulation = (
            b"%PDF-1.4\nSection 1 Reporting\n"
            b"The institution must report material incidents within 72 hours. "
            b"The institution shall retain evidence for seven years. "
            b"Background text without an obligation."
        )
        policy = b"%PDF-1.4\nINCIDENT POLICY\nIncidents are escalated internally."
        matrix = (
            b"domain,policy_area,owner_name,owner_role,owner_email,notes\n"
            b"Reporting,Incident Reporting,Jordan Lee,Lead,jordan@example.com,Owner\n"
        )

        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.pdf", regulation, "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "policy"},
            files={"file": ("policy.pdf", policy, "application/pdf")},
        )
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "responsibility_matrix"},
            files={"file": ("matrix.csv", matrix, "text/csv")},
        )
        assert (await client.post(f"/api/workspaces/{ws_id}/ingestion")).status_code == 200

        extract_res = await client.post(f"/api/workspaces/{ws_id}/obligations/extract")
        assert extract_res.status_code == 200
        run = extract_res.json()
        assert run["status"] == "obligations_extracted"
        assert run["obligation_count"] >= 2
        assert run["model_name"] == "local-rule-extractor-v1"

        list_res = await client.get(f"/api/workspaces/{ws_id}/obligations")
        assert list_res.status_code == 200
        obligations = list_res.json()
        assert any("report material incidents" in item["statement"] for item in obligations)
        assert any("retain evidence" in item["statement"] for item in obligations)
        assert all(item["source_reference"] for item in obligations)
        assert all(0 <= item["confidence"] <= 100 for item in obligations)


@pytest.mark.asyncio
async def test_extract_obligations_requires_ingestion() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "No Ingestion"})).json()["id"]
        await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.pdf", b"%PDF-1.4\nThe firm must report incidents.", "application/pdf")},
        )

        response = await client.post(f"/api/workspaces/{ws_id}/obligations/extract")

    assert response.status_code == 400
    assert "Run document ingestion" in response.json()["detail"]


def test_obligation_schema_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        validate_obligation_payload(
            {
                "obligations": [
                    {
                        "statement": "The firm must report incidents.",
                        "source_reference": "page 1",
                        "source_excerpt": "The firm must report incidents.",
                        "confidence": 101,
                    }
                ]
            }
        )


def test_obligation_provider_output_repairs_fenced_top_level_list() -> None:
    parsed = parse_obligation_provider_output(
        """```json
        [
          {
            "statement": "The firm must report material incidents.",
            "source_reference": "page 1",
            "source_excerpt": "The firm must report material incidents.",
            "confidence": 90,
            "compliance_domain": "Reporting"
          }
        ]
        ```"""
    )

    assert len(parsed.obligations) == 1
    assert parsed.obligations[0].source_reference == "page 1"
