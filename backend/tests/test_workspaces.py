"""Workspaces integration tests."""

import os
import shutil
import tempfile
from collections.abc import Generator
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

# Keep track of a temp directory for uploads in tests
TEMP_UPLOAD_DIR = tempfile.mkdtemp()
settings.upload_dir = TEMP_UPLOAD_DIR


@pytest.fixture(scope="module", autouse=True)
def cleanup_uploads() -> Generator[None, None, None]:
    yield
    if os.path.exists(TEMP_UPLOAD_DIR):
        shutil.rmtree(TEMP_UPLOAD_DIR)


@pytest.mark.asyncio
async def test_workspace_lifecycle() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 1. Create workspace
        create_res = await client.post("/api/workspaces", json={"name": "Test Workspace"})
        assert create_res.status_code == 201
        ws = create_res.json()
        ws_id = ws["id"]
        assert ws["name"] == "Test Workspace"
        assert ws["status"] == "active"

        # 2. Get workspace detail (empty)
        detail_res = await client.get(f"/api/workspaces/{ws_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == ws_id
        assert detail["documents"] == []
        assert detail["ready_for_analysis"] is False

        # 3. Upload regulation PDF
        reg_pdf = b"%PDF-1.4 test regulation"
        upload_reg_res = await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.pdf", reg_pdf, "application/pdf")},
        )
        assert upload_reg_res.status_code == 201
        doc_reg = upload_reg_res.json()
        assert doc_reg["document_type"] == "regulation"
        assert doc_reg["original_filename"] == "regulation.pdf"

        # Try to upload another regulation PDF (should fail count rules)
        fail_reg_res = await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("another_regulation.pdf", reg_pdf, "application/pdf")},
        )
        assert fail_reg_res.status_code == 400
        assert "Only one regulation document is allowed" in fail_reg_res.json()["detail"]

        # Try to upload invalid extension (should fail type check)
        fail_ext_res = await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "regulation"},
            files={"file": ("regulation.txt", b"invalid txt", "text/plain")},
        )
        assert fail_ext_res.status_code == 400
        assert "has extension" in fail_ext_res.json()["detail"]

        # 4. Upload policy PDF
        policy_pdf = b"%PDF-1.4 test policy"
        upload_policy_res = await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "policy"},
            files={"file": ("policy1.pdf", policy_pdf, "application/pdf")},
        )
        assert upload_policy_res.status_code == 201
        doc_pol1 = upload_policy_res.json()
        assert doc_pol1["document_type"] == "policy"

        # Check detail again, still not ready (needs matrix)
        detail_res = await client.get(f"/api/workspaces/{ws_id}")
        assert detail_res.json()["ready_for_analysis"] is False

        # 5. Upload responsibility matrix CSV
        matrix_csv = b"domain,policy_area,owner_name,owner_role,owner_email,notes\nSecurity,Data Protection,Alice,CISO,alice@company.com,notes\n"
        upload_matrix_res = await client.post(
            f"/api/workspaces/{ws_id}/documents",
            data={"document_type": "responsibility_matrix"},
            files={"file": ("matrix.csv", matrix_csv, "text/csv")},
        )
        assert upload_matrix_res.status_code == 201
        doc_matrix = upload_matrix_res.json()
        assert doc_matrix["document_type"] == "responsibility_matrix"

        # Check detail, now it should be ready for analysis!
        detail_res = await client.get(f"/api/workspaces/{ws_id}")
        detail = detail_res.json()
        assert detail["ready_for_analysis"] is True
        assert len(detail["documents"]) == 3

        # 6. Delete policy and verify readiness is false
        del_res = await client.delete(f"/api/workspaces/{ws_id}/documents/{doc_pol1['id']}")
        assert del_res.status_code == 204

        detail_res = await client.get(f"/api/workspaces/{ws_id}")
        detail = detail_res.json()
        assert detail["ready_for_analysis"] is False
        assert len(detail["documents"]) == 2


@pytest.mark.asyncio
async def test_workspace_exports() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_res = await client.post("/api/workspaces", json={"name": "Export Test Workspace"})
        ws_id = create_res.json()["id"]

        # JSON export
        json_res = await client.get(f"/api/workspaces/{ws_id}/export.json")
        assert json_res.status_code == 200
        data = json_res.json()
        assert "workspace" in data
        assert data["workspace"]["id"] == ws_id
        assert "documents" in data
        assert "obligations" in data
        assert "policy_mappings" in data
        assert "gap_analyses" in data
        assert "policy_pull_requests" in data
        assert "attachment; filename=" in json_res.headers["content-disposition"]

        # CSV export
        csv_res = await client.get(f"/api/workspaces/{ws_id}/export.csv")
        assert csv_res.status_code == 200
        assert csv_res.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment; filename=" in csv_res.headers["content-disposition"]
        csv_text = csv_res.text
        assert "Obligation ID,Obligation Statement" in csv_text
