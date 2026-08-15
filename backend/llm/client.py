"""Unified LLM client for OpenAI and Anthropic."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load backend/.env when this module is imported (e.g. one-off python -c tests).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

Provider = Literal["openai", "anthropic"]


def openai_base_url() -> str:
    return (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip()


class LLMNotConfiguredError(RuntimeError):
    pass


def _provider_env(name: str, default: str = "openai") -> Provider:
    raw = os.getenv(name, default).strip().lower()
    if raw not in ("openai", "anthropic"):
        raise ValueError(f"Invalid provider in {name}: {raw}")
    return raw  # type: ignore[return-value]


def chat_completion(
    *,
    provider: Provider,
    model: str,
    system: str,
    user: str,
    temperature: float = 0,
    max_tokens: int = 2000,
    extra_messages: list[dict[str, str]] | None = None,
) -> str:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if extra_messages:
        messages.extend(extra_messages)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMNotConfiguredError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=openai_base_url())
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise LLMNotConfiguredError("ANTHROPIC_API_KEY is not set")
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise LLMNotConfiguredError("anthropic package not installed") from exc

    client = Anthropic(api_key=api_key)
    # Anthropic: system separate from messages
    anthropic_messages = [m for m in messages if m["role"] != "system"]
    system_text = system
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
            break

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_text,
        messages=anthropic_messages,  # type: ignore[arg-type]
        temperature=temperature,
    )
    parts = [block.text for block in response.content if hasattr(block, "text")]
    return "".join(parts).strip()


def router_completion(system: str, user: str, extra_messages: list[dict[str, str]] | None = None) -> str:
    provider = _provider_env("ROUTER_PROVIDER", "openai")
    model = os.getenv("ROUTER_MODEL", "gpt-5.4-mini")
    return chat_completion(
        provider=provider,
        model=model,
        system=system,
        user=user,
        temperature=0,
        max_tokens=int(os.getenv("ROUTER_MAX_TOKENS", "1500")),
        extra_messages=extra_messages,
    )


def analyst_completion(system: str, user: str, extra_messages: list[dict[str, str]] | None = None) -> str:
    provider = _provider_env("ANALYST_PROVIDER", "openai")
    model = os.getenv("ANALYST_MODEL", "gpt-5.4-mini")
    return chat_completion(
        provider=provider,
        model=model,
        system=system,
        user=user,
        temperature=0,
        max_tokens=int(os.getenv("ANALYST_MAX_TOKENS", "2000")),
        extra_messages=extra_messages,
    )
