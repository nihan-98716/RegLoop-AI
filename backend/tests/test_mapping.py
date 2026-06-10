"""Phase 5: Policy mapping integration tests."""

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
from app.services.mapping import (
    MappingOutput,
    _score_chunk,
    retrieve_candidate_chunks,
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
# Unit tests for the mapping service
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


class _FakeChunk:
    """Lightweight stand-in for DocumentChunk ORM objects in unit tests."""
    def __init__(self, **kwargs):
        defaults = {
            "id": "chunk-001",
            "document_id": "doc-002",
            "chunk_index": 0,
            "page_number": 1,
            "section_label": "Incident Reporting Procedure",
            "text": "The organisation must report all security incidents to the regulator within 72 hours of detection.",
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# Convenience aliases so test bodies read clearly
def _make_obligation(**kwargs):  # type: ignore[return]
    return _FakeObligation(**kwargs)


def _make_chunk(**kwargs):  # type: ignore[return]
    return _FakeChunk(**kwargs)


def test_score_chunk_high_overlap() -> None:
    obl = _make_obligation()
    chunk = _make_chunk()
    score = _score_chunk(obl, chunk)
    assert score >= 40, f"Expected high score for closely matching text, got {score}"


def test_score_chunk_no_overlap() -> None:
    obl = _make_obligation()
    chunk = _make_chunk(
        text="Employees are entitled to annual leave and flexible working arrangements."
    )
    score = _score_chunk(obl, chunk)
    assert score == 0, f"Expected zero score for unrelated text, got {score}"


def test_retrieve_candidate_chunks_ordering() -> None:
    obl = _make_obligation()
    relevant = _make_chunk(id="c1", text="Incidents must be reported to the regulator within 72 hours.")
    irrelevant = _make_chunk(id="c2", text="All employees shall take mandatory training annually.")
    candidates = retrieve_candidate_chunks(obl, [irrelevant, relevant], top_k=5)
    assert candidates[0][0].id == "c1", "Relevant chunk should rank first"
    assert candidates[0][1] > candidates[1][1], "Relevant chunk should have higher score"


def test_mapping_output_schema_rejects_blank_rationale() -> None:
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MappingOutput(
            document_chunk_id=None,
            policy_excerpt=None,
            mapping_rationale="   ",
            confidence=10,
            is_no_match=True,
        )


def test_mapping_output_schema_rejects_out_of_range_confidence() -> None:
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MappingOutput(
            document_chunk_id=None,
            policy_excerpt=None,
            mapping_rationale="No match found.",
            confidence=101,
            is_no_match=True,
        )


# ---------------------------------------------------------------------------
# Integration tests against the full API
# ---------------------------------------------------------------------------

async def _setup_workspace_with_ingestion_and_obligations(client: AsyncClient) -> str:
    """Create workspace, upload all documents, ingest, extract obligations. Returns workspace id."""
    ws_id = (await client.post("/api/workspaces", json={"name": "Phase 5 Test"})).json()["id"]

    regulation = (
        b"%PDF-1.4\nSection 1 Reporting\n"
        b"The institution must report material incidents within 72 hours. "
        b"The institution shall retain all evidence for seven years. "
        b"The firm must notify the regulator of any data breach immediately."
    )
    policy = (
        b"%PDF-1.4\nINCIDENT REPORTING PROCEDURE\n"
        b"All security incidents must be reported to the Compliance team and the regulator "
        b"within 72 hours of detection. Evidence of the report must be retained. "
        b"DATA RETENTION POLICY\n"
        b"All records and evidence shall be retained for a minimum of seven years "
        b"in accordance with regulatory requirements."
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

    ingest_res = await client.post(f"/api/workspaces/{ws_id}/ingestion")
    assert ingest_res.status_code == 200

    extract_res = await client.post(f"/api/workspaces/{ws_id}/obligations/extract")
    assert extract_res.status_code == 200

    return ws_id


@pytest.mark.asyncio
async def test_run_policy_mapping_success() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_ingestion_and_obligations(client)

        run_res = await client.post(f"/api/workspaces/{ws_id}/mappings/run")
        assert run_res.status_code == 200, run_res.text

        run = run_res.json()
        assert run["status"] == "mappings_run"
        assert run["obligation_count"] >= 2
        assert run["mapping_count"] == run["obligation_count"], "One mapping per obligation"
        assert run["model_name"] == "local-keyword-mapper-v1"
        assert 0 <= run["no_match_count"] <= run["mapping_count"]


@pytest.mark.asyncio
async def test_list_policy_mappings_returns_results() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_ingestion_and_obligations(client)

        await client.post(f"/api/workspaces/{ws_id}/mappings/run")

        list_res = await client.get(f"/api/workspaces/{ws_id}/mappings")
        assert list_res.status_code == 200

        mappings = list_res.json()
        assert len(mappings) >= 2

        for m in mappings:
            assert "obligation_id" in m
            assert "confidence" in m
            assert 0 <= m["confidence"] <= 100
            assert "is_no_match" in m
            assert "mapping_rationale" in m
            assert m["mapping_rationale"].strip()

            # Matched mappings should have an excerpt; no-match should not
            if not m["is_no_match"]:
                assert m["policy_excerpt"] is not None
                assert m["document_chunk_id"] is not None
            else:
                assert m["policy_excerpt"] is None


@pytest.mark.asyncio
async def test_run_mapping_produces_matched_and_flagged_results() -> None:
    """At least one mapping should match; structure should be valid for all."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_ingestion_and_obligations(client)
        await client.post(f"/api/workspaces/{ws_id}/mappings/run")

        mappings = (await client.get(f"/api/workspaces/{ws_id}/mappings")).json()
        matched = [m for m in mappings if not m["is_no_match"]]
        assert len(matched) >= 1, "At least one obligation should match a policy chunk"

        for m in matched:
            assert m["confidence"] >= 30, "Matched mappings should have confidence >= threshold"


@pytest.mark.asyncio
async def test_run_mapping_requires_obligations() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = (await client.post("/api/workspaces", json={"name": "No Obligations"})).json()["id"]

        res = await client.post(f"/api/workspaces/{ws_id}/mappings/run")
        assert res.status_code == 400
        assert "obligation extraction" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_run_mapping_is_idempotent() -> None:
    """Running mappings twice should replace old results, not duplicate them."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_ingestion_and_obligations(client)

        await client.post(f"/api/workspaces/{ws_id}/mappings/run")
        first_count = len((await client.get(f"/api/workspaces/{ws_id}/mappings")).json())

        await client.post(f"/api/workspaces/{ws_id}/mappings/run")
        second_count = len((await client.get(f"/api/workspaces/{ws_id}/mappings")).json())

        assert first_count == second_count, "Re-running mapping should replace, not append"


@pytest.mark.asyncio
async def test_list_mappings_empty_before_run() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ws_id = await _setup_workspace_with_ingestion_and_obligations(client)

        list_res = await client.get(f"/api/workspaces/{ws_id}/mappings")
        assert list_res.status_code == 200
        assert list_res.json() == []


@pytest.mark.asyncio
async def test_list_mappings_returns_404_for_unknown_workspace() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/workspaces/nonexistent-ws/mappings")
        assert res.status_code == 404
