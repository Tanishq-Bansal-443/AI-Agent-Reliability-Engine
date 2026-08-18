"""
GeminiProvider — Gemini implementation of BaseLLMProvider.

This is the PRIMARY LLM provider for the AI Agent Reliability Engine.

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


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini implementation of BaseLLMProvider.

    Uses the google-generativeai SDK (not imported by any core package).

    Requires:
        GEMINI_API_KEY environment variable or explicit api_key argument.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.0-flash",
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initialize the Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai  # type: ignore[import-untyped]
                genai.configure(api_key=self._api_key)
                self._client = genai.GenerativeModel(self._model)
            except ImportError as e:
                raise ImportError(
                    "google-generativeai is not installed. "
                    "Install it with: pip install google-generativeai"
                ) from e
        return self._client

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        """Generate a text completion using Gemini."""
        import asyncio

        client = self._get_client()

        # Convert messages to Gemini format
        gemini_messages = _convert_messages_to_gemini(messages)

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if stop_sequences:
            generation_config["stop_sequences"] = stop_sequences

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.generate_content(
                gemini_messages,
                generation_config=generation_config,
            ),
        )

        content = response.text if hasattr(response, "text") else ""
        return LLMResponse(
            content=content,
            finish_reason="stop",
            model=self._model,
            raw_response={"candidates": str(response.candidates)} if hasattr(response, "candidates") else {},
        )

    async def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a completion with Gemini function calling."""
        import asyncio

        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("google-generativeai is not installed.") from e

        gemini_tools = _convert_tools_to_gemini(tools)
        gemini_messages = _convert_messages_to_gemini(messages)

        model = genai.GenerativeModel(
            model_name=self._model,
            tools=gemini_tools,
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                gemini_messages,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            ),
        )

        # Check for function call in response
        function_call: FunctionCall | None = None
        content: str | None = None

        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        function_call = FunctionCall(
                            name=fc.name,
                            arguments=dict(fc.args),
                        )
                        break
                    if hasattr(part, "text") and part.text:
                        content = part.text

        return LLMResponse(
            content=content,
            function_call=function_call,
            finish_reason="function_call" if function_call else "stop",
            model=self._model,
        )

    async def health_check(self) -> bool:
        """Check whether Gemini is reachable with the configured API key."""
        try:
            response = await self.complete(
                [LLMMessage(role="user", content="Say 'ok'.")],
                max_tokens=10,
            )
            return response.content is not None
        except Exception:
            return False


def _convert_messages_to_gemini(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert BaseLLMProvider messages to Gemini content format."""
    result = []
    for msg in messages:
        if msg.role == "system":
            # Gemini doesn't have a system role — prepend to first user message
            # or use model instructions. For now, treat as user.
            result.append({"role": "user", "parts": [msg.content]})
        elif msg.role == "assistant":
            result.append({"role": "model", "parts": [msg.content]})
        else:
            result.append({"role": "user", "parts": [msg.content]})
    return result


def _convert_tools_to_gemini(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    """Convert ToolSpec list to Gemini function declarations."""
    function_declarations = []
    for tool in tools:
        function_declarations.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        })
    return [{"function_declarations": function_declarations}]
