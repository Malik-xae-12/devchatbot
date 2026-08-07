"""Thin wrapper around Azure AI Foundry (Azure OpenAI) used by all agents.

Uses the gpt-4o deployment configured in Azure AI Foundry. All prompts in
this app are written as (system, user) pairs, so this wrapper maps that
straight onto the Chat Completions API.
"""
from __future__ import annotations

from openai import AsyncAzureOpenAI

from app.config import settings

_client: AsyncAzureOpenAI | None = None


def get_client() -> AsyncAzureOpenAI:
    global _client
    if _client is None:
        _client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    return _client


async def complete(system: str, user: str, max_tokens: int = 1024, json_mode: bool = False) -> str:
    client = get_client()
    kwargs = {}
    if json_mode:
        # Forces valid JSON output from Azure OpenAI — without this, gpt-4o
        # sometimes adds a preamble/fences despite prompt instructions, which
        # silently breaks naive json.loads() parsing downstream.
        kwargs["response_format"] = {"type": "json_object"}
    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,  # Foundry deployment name, not "gpt-4o" literally
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )
    return (response.choices[0].message.content or "").strip()
