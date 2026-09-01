from __future__ import annotations

"""Single-provider DeepSeek V4 Flash client used by all LLM features.

Specialized computer-vision, statistics and optimization engines remain local.
This client is only for semantic/text reasoning, query expansion and explanation.
"""

import json
from typing import Any

import requests

from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_SEND_SAMPLE_VALUES,
    DEEPSEEK_SEND_DOCUMENT_TEXT,
    DEEPSEEK_SEND_STRUCTURED_EVIDENCE,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_ENABLED,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS,
)


class DeepSeekError(RuntimeError):
    pass


def available() -> bool:
    return bool(DEEPSEEK_ENABLED and DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL)


def status() -> dict[str, Any]:
    return {
        "enabled": bool(DEEPSEEK_ENABLED),
        "configured": bool(DEEPSEEK_API_KEY),
        "available": available(),
        "provider": "DeepSeek",
        "model": DEEPSEEK_MODEL,
        "base_url": DEEPSEEK_BASE_URL,
        "send_sample_values": bool(DEEPSEEK_SEND_SAMPLE_VALUES),
        "send_document_text": bool(DEEPSEEK_SEND_DOCUMENT_TEXT),
        "send_structured_evidence": bool(DEEPSEEK_SEND_STRUCTURED_EVIDENCE),
    }


def _call(
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
    thinking: bool = False,
    reasoning_effort: str = "low",
    max_tokens: int = 2400,
    temperature: float = 0.1,
) -> str:
    if not available():
        raise DeepSeekError("DeepSeek Flash is not configured. Set DEEPSEEK_API_KEY in .env.local or the process environment.")

    payload: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "thinking": {"type": "enabled" if thinking else "disabled"},
        "reasoning_effort": reasoning_effort,
    }
    if not thinking:
        payload["temperature"] = temperature
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            },
            json=payload,
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        text = str(body["choices"][0]["message"].get("content") or "").strip()
        if not text:
            raise DeepSeekError("DeepSeek returned empty content")
        return text
    except DeepSeekError:
        raise
    except Exception as exc:
        # Never include headers or the API key in raised errors.
        raise DeepSeekError(f"DeepSeek request failed: {type(exc).__name__}: {exc}") from exc


def chat(
    *,
    system: str,
    user: str,
    thinking: bool = False,
    reasoning_effort: str = "low",
    max_tokens: int = 2400,
    temperature: float = 0.1,
) -> str:
    return _call(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def json_chat(
    *,
    system: str,
    user: str,
    thinking: bool = False,
    reasoning_effort: str = "low",
    max_tokens: int = 2400,
) -> dict[str, Any]:
    text = _call(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_mode=True,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    try:
        obj = json.loads(text)
    except Exception as exc:
        raise DeepSeekError("DeepSeek JSON response could not be parsed") from exc
    if not isinstance(obj, dict):
        raise DeepSeekError("DeepSeek JSON response was not an object")
    return obj
