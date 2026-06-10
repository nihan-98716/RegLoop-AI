"""Phase 7: Policy pull request integration and unit tests."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.services.pull_request import (
    find_suggested_owner,
    generate_pr_for_gap,
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


# ---------------------------------------------------------------------------
# Unit tests for the suggested owner lookup and generation logic
# ---------------------------------------------------------------------------

class _FakeObligation:
    def __init__(self, **kwargs):
        defaults = {
            "id": "obl-001",
            "workspace_id": "ws-001",
            "statement": "The institution must report security breaches within 72 hours.",
            "source_reference": "Article 4",
            "source_excerpt": "Security breaches must be reported.",
            "compliance_domain": "Reporting",
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class _FakeOwner:
    def __init__(self, **kwargs):
        defaults = {
            "id": "owner-001",
            "workspace_id": "ws-001",
            "domain": "Reporting",
            "policy_area": "Incident Response",
            "owner_name": "Jordan Lee",
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


def test_find_suggested_owner_exact_match() -> None:
    obl = _FakeObligation(compliance_domain="Reporting")
    owner1 = _FakeOwner(id="o1", domain="Reporting")
    owner2 = _FakeOwner(id="o2", domain="Security")
    res = find_suggested_owner(obl, [owner2, owner1])
    assert res is not None
    assert res.id == "o1"


def test_find_suggested_owner_substring_match() -> None:
    obl = _FakeObligation(compliance_domain="Data Reporting Compliance")
    owner = _FakeOwner(id="o1", domain="Reporting")
    res = find_suggested_owner(obl, [owner])
    assert res is not None
    assert res.id == "o1"


def test_find_suggested_owner_keyword_match() -> None:
    obl = _FakeObligation(statement="The company must implement strict encryption.")
    owner = _FakeOwner(id="o1", domain="IT", policy_area="encryption")
    res = find_suggested_owner(obl, [owner])
    assert res is not None
    assert res.id == "o1"


def test_find_suggested_owner_fallback() -> None:
    obl = _FakeObligation(compliance_domain="Unknown", statement="Random text.")
    owner1 = _FakeOwner(id="o1", domain="A")
    owner2 = _FakeOwner(id="o2", domain="B")
    res = find_suggested_owner(obl, [owner1, owner2])
    assert res is not None
    assert res.id == "o1"


# ---------------------------------------------------------------------------
# Integration tests against the full API
# ---------------------------------------------------------------------------

async def _setup_workspace_with_gaps(client: AsyncClient) -> str:
    """Creates workspace, uploads files, ingests, extracts obligations, runs mapping, and gap analysis."""
    ws_id = (await client.post("/api/workspaces", json={"name": "PR Integration Test"})).json()["id"]

    regulation = (
        b"%PDF-1.4\nSection 1 Reporting\n"
        b"The institution must report material incidents within 72 hours. "
        b"The firm shall retain all evidence for seven years."
    )
    policy = (
        b"%PDF-1.4\nINCIDENT REPORTING PROCEDURE\n"
        b"All security incidents must be reported to the Compliance team."
        # No retention section to trigger a gap!
    )
    matrix = (
        b"domain,policy_area,owner_name,owner_role,owner_email,notes\n"
        b"Reporting,Incident Reporting,Jordan Lee,Lead,jordan@example.com,Primary\n"
        b"Records,Data Retention,Alex Smith,Manager,alex@example.com,Secondary\n"
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

    await client.post(f"/api/workspaces/{ws_id}/ingestion")
    await client.post(f"/api/workspaces/{ws_id}/obligations/extract")
    await client.post(f"/api/workspaces/{ws_id}/mappings/run")
    await client.post(f"/api/workspaces/{ws_id}/gap-analysis/run")

    return ws_id


@pytest.mark.asyncio
async def test_run_pull_requests_success() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_gaps(client)

        run_res = await client.post(f"/api/workspaces/{ws_id}/policy-pull-requests/run")
        assert run_res.status_code == 200, run_res.text

        run = run_res.json()
        assert run["workspace_id"] == ws_id
        assert run["status"] == "prs_generated"
        assert run["pr_count"] >= 1

        # Check list endpoint
        list_res = await client.get(f"/api/workspaces/{ws_id}/policy-pull-requests")
        assert list_res.status_code == 200
        prs = list_res.json()
        assert len(prs) == run["pr_count"]

        for pr in prs:
            assert pr["status"] == "pending"
            assert pr["proposed_amendment"].strip()
            assert pr["before_text"] is not None
            assert pr["after_text"].strip()
            assert pr["risk_level"] in ("high", "medium", "low")
            assert pr["suggested_owner"] is not None


@pytest.mark.asyncio
async def test_list_pull_requests_filtering() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_gaps(client)
        await client.post(f"/api/workspaces/{ws_id}/policy-pull-requests/run")

        # Retrieve all
        all_prs = (await client.get(f"/api/workspaces/{ws_id}/policy-pull-requests")).json()
        assert len(all_prs) >= 1

        owner_id = all_prs[0]["suggested_owner_id"]
        risk = all_prs[0]["risk_level"]

        # Filter by owner_id
        owner_res = await client.get(
            f"/api/workspaces/{ws_id}/policy-pull-requests",
            params={"owner_id": owner_id},
        )
        assert owner_res.status_code == 200
        for pr in owner_res.json():
            assert pr["suggested_owner_id"] == owner_id

        # Filter by risk_level
        risk_res = await client.get(
            f"/api/workspaces/{ws_id}/policy-pull-requests",
            params={"risk_level": risk},
        )
        assert risk_res.status_code == 200
        for pr in risk_res.json():
            assert pr["risk_level"] == risk


@pytest.mark.asyncio
async def test_review_action_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_gaps(client)
        await client.post(f"/api/workspaces/{ws_id}/policy-pull-requests/run")

        prs = (await client.get(f"/api/workspaces/{ws_id}/policy-pull-requests")).json()
        pr_id = prs[0]["id"]

        # 1. Approve
        app_res = await client.post(
            f"/api/policy-pull-requests/{pr_id}/review",
            json={
                "action": "approve",
                "reviewer_label": "Legal Counsel",
                "comment": "Satisfies GDPR requirement.",
            },
        )
        assert app_res.status_code == 200
        pr = app_res.json()
        assert pr["status"] == "approved"
        assert len(pr["review_actions"]) == 1
        assert pr["review_actions"][0]["action"] == "approve"
        assert pr["review_actions"][0]["reviewer_label"] == "Legal Counsel"

        # 2. Modify (should fail if modified_text is missing)
        mod_fail = await client.post(
            f"/api/policy-pull-requests/{pr_id}/review",
            json={
                "action": "modify",
                "reviewer_label": "Legal Counsel",
            },
        )
        assert mod_fail.status_code == 400

        # 3. Modify (success)
        mod_success = await client.post(
            f"/api/policy-pull-requests/{pr_id}/review",
            json={
                "action": "modify",
                "reviewer_label": "Legal Counsel",
                "modified_text": "Custom policy text here.",
                "comment": "Tweaked wording.",
            },
        )
        assert mod_success.status_code == 200
        pr = mod_success.json()
        assert pr["status"] == "modified"
        assert pr["after_text"] == "Custom policy text here."


@pytest.mark.asyncio
async def test_run_pull_requests_is_idempotent() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_gaps(client)

        await client.post(f"/api/workspaces/{ws_id}/policy-pull-requests/run")
        first_count = len((await client.get(f"/api/workspaces/{ws_id}/policy-pull-requests")).json())

        await client.post(f"/api/workspaces/{ws_id}/policy-pull-requests/run")
        second_count = len((await client.get(f"/api/workspaces/{ws_id}/policy-pull-requests")).json())

        assert first_count == second_count, "Running PR generator twice should overwrite, not duplicate"


@pytest.mark.asyncio
async def test_run_pull_requests_requires_gap_analysis() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create workspace, ingest, extract obligations, but do NOT run gap analysis
        ws_id = (await client.post("/api/workspaces", json={"name": "No Gaps"})).json()["id"]
        res = await client.post(f"/api/workspaces/{ws_id}/policy-pull-requests/run")
        assert res.status_code == 400
        assert "gap analysis" in res.json()["detail"].lower()
