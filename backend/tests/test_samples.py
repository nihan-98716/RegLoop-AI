"""Phase 9 Integration tests for sample data package and exports validation."""

import os
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"


@pytest.mark.asyncio
async def test_sample_files_workflow_and_export() -> None:
    # Verify that the samples directory and files exist
    assert SAMPLES_DIR.exists()
    regulation_path = SAMPLES_DIR / "regulation.pdf"
    monitoring_path = SAMPLES_DIR / "compliance_monitoring_policy.pdf"
    reporting_path = SAMPLES_DIR / "incident_reporting_policy.pdf"
    records_path = SAMPLES_DIR / "records_and_audit_policy.pdf"
    matrix_path = SAMPLES_DIR / "responsibility_matrix.csv"

    for path in [regulation_path, monitoring_path, reporting_path, records_path, matrix_path]:
        assert path.exists(), f"Sample file {path.name} is missing"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create workspace
        ws_res = await client.post("/api/workspaces", json={"name": "Sample Data Demo Workspace"})
        assert ws_res.status_code in (200, 201)
        ws_id = ws_res.json()["id"]

        # 2. Upload sample files
        with open(regulation_path, "rb") as f:
            res = await client.post(
                f"/api/workspaces/{ws_id}/documents",
                data={"document_type": "regulation"},
                files={"file": (regulation_path.name, f.read(), "application/pdf")},
            )
            assert res.status_code in (200, 201)

        with open(monitoring_path, "rb") as f:
            res = await client.post(
                f"/api/workspaces/{ws_id}/documents",
                data={"document_type": "policy"},
                files={"file": (monitoring_path.name, f.read(), "application/pdf")},
            )
            assert res.status_code in (200, 201)

        with open(reporting_path, "rb") as f:
            res = await client.post(
                f"/api/workspaces/{ws_id}/documents",
                data={"document_type": "policy"},
                files={"file": (reporting_path.name, f.read(), "application/pdf")},
            )
            assert res.status_code in (200, 201)

        with open(records_path, "rb") as f:
            res = await client.post(
                f"/api/workspaces/{ws_id}/documents",
                data={"document_type": "policy"},
                files={"file": (records_path.name, f.read(), "application/pdf")},
            )
            assert res.status_code in (200, 201)

        with open(matrix_path, "rb") as f:
            res = await client.post(
                f"/api/workspaces/{ws_id}/documents",
                data={"document_type": "responsibility_matrix"},
                files={"file": (matrix_path.name, f.read(), "text/csv")},
            )
            assert res.status_code in (200, 201)

        # Verify readiness check
        detail_res = await client.get(f"/api/workspaces/{ws_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["ready_for_analysis"] is True

        # 3. Run Ingestion
        ingest_res = await client.post(f"/api/workspaces/{ws_id}/ingestion")
        assert ingest_res.status_code == 200
        assert ingest_res.json()["status"] == "ingested"

        # 4. Extract Obligations
        extract_res = await client.post(f"/api/workspaces/{ws_id}/obligations/extract")
        assert extract_res.status_code == 200
        assert extract_res.json()["obligation_count"] == 5

        # Fetch the obligations list
        list_obl_res = await client.get(f"/api/workspaces/{ws_id}/obligations")
        assert list_obl_res.status_code == 200
        obligations = list_obl_res.json()
        assert len(obligations) == 5, f"Expected 5 obligations, got {len(obligations)}"

        # 5. Run Mapping
        map_res = await client.post(f"/api/workspaces/{ws_id}/mappings/run")
        assert map_res.status_code == 200

        # 6. Run Gap Analysis
        gap_res = await client.post(f"/api/workspaces/{ws_id}/gap-analysis/run")
        assert gap_res.status_code == 200
        
        # Fetch the gap analysis list
        list_gap_res = await client.get(f"/api/workspaces/{ws_id}/gap-analysis")
        assert list_gap_res.status_code == 200
        gaps = list_gap_res.json()

        # Check coverage outcomes
        coverage_statuses = [g["coverage_status"] for g in gaps]
        assert "fully_covered" in coverage_statuses, "Should contain at least one fully covered obligation"
        assert "partially_covered" in coverage_statuses, "Should contain at least one partially covered obligation"
        assert "not_covered" in coverage_statuses, "Should contain at least one not covered obligation"

        # 7. Generate Policy Pull Requests
        prs_res = await client.post(f"/api/workspaces/{ws_id}/policy-pull-requests/run")
        assert prs_res.status_code == 200
        
        # Fetch the pull requests list
        list_prs_res = await client.get(f"/api/workspaces/{ws_id}/policy-pull-requests")
        assert list_prs_res.status_code == 200
        prs = list_prs_res.json()
        assert len(prs) >= 2, f"Expected at least 2 PRs, got {len(prs)}"

        # Check that we have at least one suggested owner
        owners = [pr["suggested_owner"] for pr in prs if pr["suggested_owner"] is not None]
        assert len(owners) >= 1, "Should have at least one suggested owner from the matrix"

        # 8. Human Review Action
        test_pr_id = prs[0]["id"]
        review_payload = {
            "action": "modify",
            "reviewer_label": "Senior Compliance Officer",
            "comment": "Adjusted formatting to align with internal standard.",
            "modified_text": "MODIFIED VERSION: " + prs[0]["proposed_amendment"]
        }
        review_res = await client.post(
            f"/api/policy-pull-requests/{test_pr_id}/review",
            json=review_payload
        )
        assert review_res.status_code == 200
        pr_after_review = review_res.json()
        assert pr_after_review["status"] == "modified"
        assert len(pr_after_review["review_actions"]) >= 1
        assert pr_after_review["review_actions"][-1]["action"] == "modify"

        # 9. Audit Trail Endpoint Verification
        audit_res = await client.get(f"/api/workspaces/{ws_id}/audit")
        assert audit_res.status_code == 200
        audit_records = audit_res.json()
        assert len(audit_records) > 0
        event_types = [rec["event_type"] for rec in audit_records]
        assert "document_uploaded" in event_types
        assert "ingestion_run" in event_types
        assert "pr_reviewed" in event_types

        # 10. Export Packages Verification
        # JSON Export
        json_export_res = await client.get(f"/api/workspaces/{ws_id}/export.json")
        assert json_export_res.status_code == 200
        export_data = json_export_res.json()
        assert "workspace" in export_data
        assert "documents" in export_data
        assert "obligations" in export_data
        assert "policy_mappings" in export_data
        assert "gap_analyses" in export_data
        assert "policy_pull_requests" in export_data
        assert "attachment; filename=" in json_export_res.headers["content-disposition"]

        # CSV Export
        csv_export_res = await client.get(f"/api/workspaces/{ws_id}/export.csv")
        assert csv_export_res.status_code == 200
        assert csv_export_res.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment; filename=" in csv_export_res.headers["content-disposition"]
        csv_text = csv_export_res.text
        # Verify CSV column headers are present
        assert "Obligation ID,Obligation Statement" in csv_text
        assert "Latest Reviewer Action,Latest Reviewer Comment" in csv_text
        # Verify reviewed comment and modification is present in CSV
        assert "Adjusted formatting to align with internal standard." in csv_text
