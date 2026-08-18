"""
OpenAIProvider — OpenAI implementation of BaseLLMProvider.

This is the SECONDARY LLM provider for the AI Agent Reliability Engine.

Provider-specific code is isolated here. Core packages must never import
this module directly — they depend on BaseLLMProvider only.

See ADR-003 in DECISIONS.md.
"""

from __future__ import annotations

import os
from typing import Any

from packages.core.providers.base import (
    BaseLLMProvider,
    FunctionCall,
    LLMMessage,
    LLMResponse,
    ToolSpec,
)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI implementation of BaseLLMProvider.

    Uses the openai SDK (not imported by any core package).

    Requires:
        OPENAI_API_KEY environment variable or explicit api_key argument.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model

    def _get_client(self) -> Any:
        """Initialize the OpenAI client."""
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]
            return AsyncOpenAI(api_key=self._api_key)
        except ImportError as e:
            raise ImportError(
                "openai is not installed. "
                "Install it with: pip install openai"
            ) from e

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a text completion using OpenAI."""
        client = self._get_client()

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop_sequences:
            kwargs["stop"] = stop_sequences

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            model=self._model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

    async def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a completion with OpenAI function calling."""
        import json

        client = self._get_client()

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

        response = await client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            tools=openai_tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        function_call: FunctionCall | None = None
        content: str | None = None

        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            try:
                arguments = json.loads(tool_call.function.arguments)
            except (json.JSONDecodeError, AttributeError):
                arguments = {}
            function_call = FunctionCall(
                name=tool_call.function.name,
                arguments=arguments,
            )
        else:
            content = choice.message.content or ""

        return LLMResponse(
            content=content,
            function_call=function_call,
            finish_reason=choice.finish_reason or "stop",
            model=self._model,
        )

    async def health_check(self) -> bool:
        """Check whether OpenAI is reachable with the configured API key."""
        try:
            response = await self.complete(
                [LLMMessage(role="user", content="Say 'ok'.")],
                max_tokens=10,
            )
            return response.content is not None
        except Exception:
            return False
