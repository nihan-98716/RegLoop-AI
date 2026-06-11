"""Unit tests for multi-provider LLM fallback and prompt engineering effectiveness."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.services.llm import (
    call_anthropic_api,
    call_gemini_api,
    call_llm_api,
    call_openai_api,
)
from app.services.mapping import POLICY_MAPPING_PROMPT
from app.services.obligations import OBLIGATION_EXTRACTION_PROMPT


@pytest.mark.anyio
async def test_prompt_engineering_effectiveness() -> None:
    """Verify that our prompts explicitly enforce structured JSON formatting and key fields."""
    # Obligation extraction prompt checks
    assert "json" in OBLIGATION_EXTRACTION_PROMPT.lower()
    assert "statement" in OBLIGATION_EXTRACTION_PROMPT
    assert "source_reference" in OBLIGATION_EXTRACTION_PROMPT
    assert "confidence" in OBLIGATION_EXTRACTION_PROMPT
    assert "compliance_domain" in OBLIGATION_EXTRACTION_PROMPT

    # Policy mapping prompt checks
    assert "json" in POLICY_MAPPING_PROMPT.lower()
    assert "document_chunk_id" in POLICY_MAPPING_PROMPT
    assert "policy_excerpt" in POLICY_MAPPING_PROMPT
    assert "confidence" in POLICY_MAPPING_PROMPT
    assert "is_no_match" in POLICY_MAPPING_PROMPT


@pytest.mark.anyio
async def test_llm_fallback_routing_openai_to_anthropic() -> None:
    """Test that unified call_llm_api routes and falls back if OpenAI fails but Anthropic is configured."""
    original_provider = settings.llm_provider
    original_openai = settings.openai_api_key
    original_anthropic = settings.anthropic_api_key
    original_google = settings.google_api_key

    settings.llm_provider = "openai"
    settings.openai_api_key = "fake-openai-key"
    settings.anthropic_api_key = "fake-anthropic-key"
    settings.google_api_key = ""

    try:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # First response (OpenAI) fails with 429
            mock_resp_openai = AsyncMock()
            mock_resp_openai.status_code = 429
            mock_resp_openai.text = "Too Many Requests"

            # Second response (Anthropic) succeeds with 200
            mock_resp_anthropic = AsyncMock()
            mock_resp_anthropic.status_code = 200
            from unittest.mock import MagicMock
            mock_resp_anthropic.json = MagicMock(return_value={
                "content": [{"text": '{"result": "success-anthropic"}'}]
            })

            mock_client.post.side_effect = [mock_resp_openai, mock_resp_anthropic]

            res = await call_llm_api("sys", "user", response_json=True)
            assert res == '{"result": "success-anthropic"}'
            
            # Assert both endpoints were called in fallback order
            assert mock_client.post.call_count == 2
    finally:
        settings.llm_provider = original_provider
        settings.openai_api_key = original_openai
        settings.anthropic_api_key = original_anthropic
        settings.google_api_key = original_google


@pytest.mark.anyio
async def test_llm_fallback_routing_all_fail() -> None:
    """Test that call_llm_api returns None if all providers fail."""
    original_provider = settings.llm_provider
    original_openai = settings.openai_api_key
    original_anthropic = settings.anthropic_api_key
    original_google = settings.google_api_key

    settings.llm_provider = "openai"
    settings.openai_api_key = "fake-openai-key"
    settings.anthropic_api_key = ""
    settings.google_api_key = ""

    try:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_resp = AsyncMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_client.post.return_value = mock_resp

            res = await call_llm_api("sys", "user", response_json=True)
            assert res is None
    finally:
        settings.llm_provider = original_provider
        settings.openai_api_key = original_openai
        settings.anthropic_api_key = original_anthropic
        settings.google_api_key = original_google
