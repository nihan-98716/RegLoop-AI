"""Phase 6: Gap analysis integration and unit tests."""

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
from app.services.gap_analysis import (
    GapAnalysisOutput,
    _has_mandatory_language,
    _assess_coverage,
    _escalate_risk_if_mandatory,
    analyse_gap,
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
# Unit tests for the gap analysis service logic
# ---------------------------------------------------------------------------

class _FakeObligation:
    """Lightweight stand-in for Obligation ORM objects in unit tests."""
    def __init__(self, **kwargs):
        defaults = {
            "id": "obl-001",
            "workspace_id": "ws-001",
            "statement": "The institution must report material incidents within 72 hours.",
            "source_document_id": "doc-001",
            "source_reference": "page 1",
            "source_excerpt": "The institution must report material incidents within 72 hours.",
            "compliance_domain": "Reporting",
            "confidence": 88,
            "model_name": "local-rule-extractor-v1",
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class _FakePolicyMapping:
    """Lightweight stand-in for PolicyMapping ORM objects in unit tests."""
    def __init__(self, **kwargs):
        defaults = {
            "id": "map-001",
            "obligation_id": "obl-001",
            "policy_document_id": "doc-002",
            "document_chunk_id": "chunk-001",
            "policy_excerpt": "All security incidents must be reported to the Compliance team.",
            "mapping_rationale": "Matches incident reporting requirement.",
            "confidence": 75,
            "is_no_match": False,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


def _make_obligation(**kwargs):
    return _FakeObligation(**kwargs)


def _make_mapping(**kwargs):
    return _FakePolicyMapping(**kwargs)


def test_mandatory_language_detection() -> None:
    assert _has_mandatory_language("The firm must report incidents.") is True
    assert _has_mandatory_language("It shall be completed.") is True
    assert _has_mandatory_language("This is required.") is True
    assert _has_mandatory_language("The firm may report.") is False
    assert _has_mandatory_language("Optionally, provide notes.") is False


def test_assess_coverage_no_match() -> None:
    mapping = _make_mapping(is_no_match=True, confidence=0, policy_excerpt=None)
    coverage, risk, conf = _assess_coverage(mapping)
    assert coverage == "not_covered"
    assert risk == "high"
    assert conf == 15


def test_assess_coverage_high_confidence() -> None:
    mapping = _make_mapping(is_no_match=False, confidence=75)
    coverage, risk, conf = _assess_coverage(mapping)
    assert coverage == "fully_covered"
    assert risk == "low"
    assert conf == 75


def test_assess_coverage_medium_confidence() -> None:
    mapping = _make_mapping(is_no_match=False, confidence=50)
    coverage, risk, conf = _assess_coverage(mapping)
    assert coverage == "partially_covered"
    assert risk == "medium"
    assert conf == 50


def test_assess_coverage_low_confidence() -> None:
    mapping = _make_mapping(is_no_match=False, confidence=35)
    coverage, risk, conf = _assess_coverage(mapping)
    assert coverage == "not_covered"
    assert risk == "high"
    assert conf == 25


def test_escalate_risk_mandatory_partial_coverage() -> None:
    # Partially covered with mandatory verb -> escalated to high
    statement = "The company must file a report."
    risk = _escalate_risk_if_mandatory(statement, "partially_covered", "medium")
    assert risk == "high"

    # Partially covered, non-mandatory -> stays medium
    statement = "The company may file a report."
    risk = _escalate_risk_if_mandatory(statement, "partially_covered", "medium")
    assert risk == "medium"

    # Fully covered, mandatory -> stays low
    statement = "The company must file a report."
    risk = _escalate_risk_if_mandatory(statement, "fully_covered", "low")
    assert risk == "low"


def test_gap_analysis_output_schema_validation() -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GapAnalysisOutput(
            coverage_status="fully_covered",
            risk_level="low",
            reasoning="   ",  # Blank
            confidence=80,
        )


# ---------------------------------------------------------------------------
# Integration tests against the full API
# ---------------------------------------------------------------------------

async def _setup_workspace_with_mappings(client: AsyncClient) -> str:
    """Creates workspace, uploads files, ingests, extracts obligations, runs mapping."""
    ws_id = (await client.post("/api/workspaces", json={"name": "Gap Integration Test"})).json()["id"]

    regulation = (
        b"%PDF-1.4\nSection 1 Reporting\n"
        b"The institution must report material incidents within 72 hours. "
        b"The company may optionally submit a feedback form."
    )
    policy = (
        b"%PDF-1.4\nINCIDENT REPORTING PROCEDURE\n"
        b"All security incidents must be reported to the Compliance team and the regulator "
        b"within 72 hours of detection. Evidence of the report must be retained. "
    )
    matrix = (
        b"domain,policy_area,owner_name,owner_role,owner_email,notes\n"
        b"Reporting,Incident Reporting,Jordan Lee,Lead,jordan@example.com,Primary\n"
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

    return ws_id


@pytest.mark.asyncio
async def test_run_gap_analysis_success() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_mappings(client)

        run_res = await client.post(f"/api/workspaces/{ws_id}/gap-analysis/run")
        assert run_res.status_code == 200, run_res.text

        run = run_res.json()
        assert run["workspace_id"] == ws_id
        assert run["status"] == "gap_analysis_run"
        assert run["obligation_count"] >= 1
        assert run["model_name"] == "local-gap-analyzer-v1"
        assert "fully_covered" in run
        assert "partially_covered" in run
        assert "not_covered" in run
        assert "high_risk" in run


@pytest.mark.asyncio
async def test_list_gap_analyses_returns_results() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_mappings(client)
        await client.post(f"/api/workspaces/{ws_id}/gap-analysis/run")

        list_res = await client.get(f"/api/workspaces/{ws_id}/gap-analysis")
        assert list_res.status_code == 200

        gaps = list_res.json()
        assert len(gaps) >= 1

        for gap in gaps:
            assert "id" in gap
            assert "obligation_id" in gap
            assert gap["coverage_status"] in ("fully_covered", "partially_covered", "not_covered")
            assert gap["risk_level"] in ("high", "medium", "low")
            assert "reasoning" in gap
            assert gap["reasoning"].strip()
            assert "confidence" in gap
            assert 0 <= gap["confidence"] <= 100


@pytest.mark.asyncio
async def test_run_gap_analysis_requires_mappings() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a workspace, upload all documents, ingest, and extract obligations, but do NOT run mapping
        ws_id = (await client.post("/api/workspaces", json={"name": "No Mappings"})).json()["id"]

        regulation = (
            b"%PDF-1.4\nSection 1 Reporting\n"
            b"The institution must report material incidents within 72 hours. "
        )
        policy = (
            b"%PDF-1.4\nINCIDENT REPORTING PROCEDURE\n"
            b"All security incidents must be reported."
        )
        matrix = (
            b"domain,policy_area,owner_name,owner_role,owner_email,notes\n"
            b"Reporting,Incident Reporting,Jordan Lee,Lead,jordan@example.com,Primary\n"
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

        res = await client.post(f"/api/workspaces/{ws_id}/gap-analysis/run")
        assert res.status_code == 400
        assert "policy mapping" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_run_gap_analysis_is_idempotent() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_mappings(client)

        await client.post(f"/api/workspaces/{ws_id}/gap-analysis/run")
        first_count = len((await client.get(f"/api/workspaces/{ws_id}/gap-analysis")).json())

        await client.post(f"/api/workspaces/{ws_id}/gap-analysis/run")
        second_count = len((await client.get(f"/api/workspaces/{ws_id}/gap-analysis")).json())

        assert first_count == second_count, "Re-running gap analysis should overwrite, not append"
