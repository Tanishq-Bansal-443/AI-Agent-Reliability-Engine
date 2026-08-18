"""
BaseLLMProvider abstraction.

All LLM access in the system goes through this interface.
No core package may import Gemini, OpenAI, or any other provider SDK directly.

See ADR-003 in DECISIONS.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """A message in an LLM conversation."""

    role: str = Field(description="Message role: system, user, or assistant.")
    content: str = Field(description="Message content.")


class FunctionCall(BaseModel):
    """A function/tool call requested by the model."""

    name: str = Field(description="Name of the function to call.")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the function call.",
    )


class LLMResponse(BaseModel):
    """The response from an LLM completion."""

    content: str | None = Field(
        default=None,
        description="Text content of the response. None when a function call is made.",
    )
    function_call: FunctionCall | None = Field(
        default=None,
        description="Function call requested by the model, if any.",
    )
    finish_reason: str = Field(
        default="stop",
        description="Why the model stopped: stop, function_call, length, error.",
    )
    model: str = Field(
        default="unknown",
        description="Model identifier used for this completion.",
    )
    usage: dict[str, int] = Field(
        default_factory=dict,
        description="Token usage: prompt_tokens, completion_tokens, total_tokens.",
    )
    raw_response: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider response for debugging. Not used in business logic.",
    )


class ToolSpec(BaseModel):
    """A tool specification passed to the LLM for function calling."""

    name: str = Field(description="Tool name.")
    description: str = Field(description="Tool description.")
    parameters: dict[str, Any] = Field(
        description="JSON Schema object describing parameters.",
    )


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    The evaluation engine, agents, and core packages only depend on this
    interface. Provider-specific implementations live in the providers/
    directory and must never be imported by core packages.

    See ADR-003 in DECISIONS.md.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'gemini' or 'openai'."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The specific model being used, e.g. 'gemini-2.0-flash'."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """
        Generate a completion for the given messages.

        Args:
            messages: Conversation history.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum number of tokens to generate.
            stop_sequences: Optional stop sequences.

        Returns:
            LLMResponse with the model's completion.
        """
        ...

    @abstractmethod
    async def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        Generate a completion with function-calling support.

        The model may return a function_call instead of text content.

        Args:
            messages: Conversation history.
            tools: Available tools the model can call.
            temperature: Sampling temperature.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            LLMResponse with either content or a function_call.
        """
        ...

    async def health_check(self) -> bool:
        """
        Check whether the provider is reachable.

        Returns True if healthy, False otherwise.
        Implementations should catch all exceptions and return False.
        """
        return True
