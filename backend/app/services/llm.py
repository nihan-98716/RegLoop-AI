"""Remote LLM API integration service supporting multiple providers with fallback logic."""

import httpx
from app.config import settings
from app.logging_config import get_logger

log = get_logger(__name__)


async def call_openai_api(
    system_prompt: str,
    user_prompt: str,
    response_json: bool = True,
    model: str = "gpt-4o",
) -> str | None:
    """API call to OpenAI Chat Completions endpoint.
    
    If the OpenAI API key is missing or calls fail, it falls back to other configured providers.
    """
    # Route to unified call function to handle robust multi-provider fallback
    return await call_llm_api(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_json=response_json,
        model=model,
    )


async def call_anthropic_api(
    system_prompt: str,
    user_prompt: str,
    response_json: bool = True,
) -> str | None:
    """API call to Anthropic Claude messages endpoint."""
    if not settings.anthropic_api_key:
        log.debug("llm.anthropic_disabled", reason="Anthropic API key is missing")
        return None

    headers = {
        "x-api-key": settings.anthropic_api_key.strip(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Anthropic doesn't support a standard response_format="json_object",
    # but we instruct it via prompts. We append a reminder for JSON formatting if required.
    adjusted_user_prompt = user_prompt
    if response_json and "json" not in user_prompt.lower():
        adjusted_user_prompt += "\n\nReturn the result as a raw JSON object."

    payload = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 4000,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": adjusted_user_prompt}
        ],
        "temperature": 0.0,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            if response.status_code != 200:
                log.error(
                    "llm.anthropic_error",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None

            data = response.json()
            return data["content"][0]["text"]
    except Exception as exc:
        log.error("llm.anthropic_exception", error=str(exc))
        return None


async def call_gemini_api(
    system_prompt: str,
    user_prompt: str,
    response_json: bool = True,
) -> str | None:
    """API call to Google Gemini generateContent endpoint."""
    if not settings.google_api_key:
        log.debug("llm.gemini_disabled", reason="Google API key is missing")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.google_api_key.strip()}"
    headers = {"Content-Type": "application/json"}

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"System Instructions:\n{system_prompt}\n\nUser Prompt:\n{user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
        }
    }

    if response_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            if response.status_code != 200:
                log.error(
                    "llm.gemini_error",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None

            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        log.error("llm.gemini_exception", error=str(exc))
        return None


async def call_llm_api(
    system_prompt: str,
    user_prompt: str,
    response_json: bool = True,
    model: str | None = None,
) -> str | None:
    """Unified LLM call routing with fallback configuration to support extensibility.
    
    Tries the configured provider first, and falls back to other available providers 
    with valid keys if the selected provider fails or is unconfigured.
    """
    provider = settings.llm_provider.lower().strip()
    
    # 1. Prioritize providers to try based on user config
    providers_to_try = [provider]
    all_providers = ["openai", "anthropic", "gemini"]
    for p in all_providers:
        if p not in providers_to_try:
            providers_to_try.append(p)

    # 2. Attempt each provider in priority order
    for p in providers_to_try:
        if p == "openai" and settings.openai_api_key:
            log.info("llm.routing", provider="openai")
            
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key.strip()}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model or "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
            }
            if response_json:
                payload["response_format"] = {"type": "json_object"}

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30.0,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        log.warn(
                            "llm.openai_failed_falling_back",
                            status_code=response.status_code,
                            response_text=response.text,
                        )
            except Exception as exc:
                log.warn("llm.openai_exception_falling_back", error=str(exc))

        elif p == "anthropic" and settings.anthropic_api_key:
            log.info("llm.routing", provider="anthropic")
            res = await call_anthropic_api(system_prompt, user_prompt, response_json)
            if res:
                return res

        elif p == "gemini" and settings.google_api_key:
            log.info("llm.routing", provider="gemini")
            res = await call_gemini_api(system_prompt, user_prompt, response_json)
            if res:
                return res

    log.warn("llm.all_providers_failed", message="No LLM provider calls succeeded.")
    return None
