"""
ToolRuntime and ToolRegistry.

Explicit tool call routing system. All tool calls from agents must go through
ToolRuntime — never through unittest.mock or direct function interception.

This design allows swapping the underlying tool implementations without
touching the evaluation engine or the agents.

See ADR-005 in DECISIONS.md.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Awaitable
from typing import Any

from pydantic import BaseModel, Field


# A tool implementation is any callable that accepts keyword arguments and
# returns any value (sync or async).
ToolImplementation = Callable[..., Any]


class ToolRegistrationError(Exception):
    """Raised when a tool cannot be registered."""


class ToolNotFoundError(Exception):
    """Raised when a tool call targets an unknown tool."""


class ToolExecutionError(Exception):
    """Raised when a tool implementation raises an exception."""


class ToolCallResult(BaseModel):
    """The result of a single tool invocation via ToolRuntime."""

    tool_name: str = Field(description="Name of the tool that was called.")
    arguments: dict[str, Any] = Field(description="Arguments that were passed.")
    result: Any = Field(default=None, description="Return value from the tool.")
    error: str | None = Field(
        default=None,
        description="Error message if the tool raised an exception.",
    )
    duration_ms: int = Field(
        default=0,
        description="How long the tool call took in milliseconds.",
    )
    success: bool = Field(
        default=True,
        description="Whether the tool call completed without error.",
    )


class ToolRegistry:
    """
    Registry of available tool implementations for a sandbox session.

    Each sandbox creates a ToolRegistry with sandboxed implementations.
    The registry maps tool names to callable implementations.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolImplementation] = {}

    def register(self, name: str, implementation: ToolImplementation) -> None:
        """
        Register a tool implementation by name.

        Args:
            name: The tool name (must match the Tool.name in the agent definition).
            implementation: The callable to invoke when this tool is called.

        Raises:
            ToolRegistrationError: If the name is already registered.
        """
        if name in self._tools:
            raise ToolRegistrationError(
                f"Tool '{name}' is already registered. Use replace() to override."
            )
        self._tools[name] = implementation

    def replace(self, name: str, implementation: ToolImplementation) -> None:
        """
        Replace an existing tool implementation.

        Used when a sandbox needs to override a tool with a scenario-specific mock.
        """
        self._tools[name] = implementation

    def is_registered(self, name: str) -> bool:
        """Return True if a tool with this name is registered."""
        return name in self._tools

    @property
    def registered_tools(self) -> list[str]:
        """List of all registered tool names."""
        return list(self._tools.keys())

    def get(self, name: str) -> ToolImplementation:
        """
        Retrieve a tool implementation by name.

        Raises:
            ToolNotFoundError: If the tool is not registered.
        """
        if name not in self._tools:
            raise ToolNotFoundError(
                f"Tool '{name}' is not registered. "
                f"Available tools: {self.registered_tools}"
            )
        return self._tools[name]


class ToolRuntime:
    """
    Executes tool calls routed through the sandbox.

    Agents call tools by passing the tool name and arguments to
    ToolRuntime.execute_tool(). The runtime looks up the implementation
    in the ToolRegistry and invokes it, recording timing and results.

    This is the ONLY legitimate way for agents to execute tools in the
    evaluation system. Direct function calls bypass the sandbox.

    See ADR-005 in DECISIONS.md.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._call_history: list[ToolCallResult] = []

    @property
    def registry(self) -> ToolRegistry:
        """Access the underlying tool registry."""
        return self._registry

    @property
    def call_history(self) -> list[ToolCallResult]:
        """All tool calls made through this runtime, in order."""
        return list(self._call_history)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolCallResult:
        """
        Execute a tool by name with the given arguments.

        Looks up the implementation in the registry, invokes it,
        records timing and result, and returns a ToolCallResult.

        Args:
            tool_name: The name of the tool to execute.
            arguments: Keyword arguments to pass to the tool.

        Returns:
            ToolCallResult with the result or error information.
        """
        start_time = time.monotonic()

        if not self._registry.is_registered(tool_name):
            error_msg = (
                f"Tool '{tool_name}' is not available in this sandbox. "
                f"Available: {self._registry.registered_tools}"
            )
            result = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                error=error_msg,
                success=False,
                duration_ms=0,
            )
            self._call_history.append(result)
            return result

        implementation = self._registry.get(tool_name)

        try:
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(implementation):
                raw_result = await implementation(**arguments)
            else:
                # Run sync implementations in a thread to avoid blocking
                loop = asyncio.get_event_loop()
                raw_result = await loop.run_in_executor(
                    None, lambda: implementation(**arguments)
                )

            duration_ms = int((time.monotonic() - start_time) * 1000)
            result = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=raw_result,
                success=True,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            result = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                error=str(exc),
                success=False,
                duration_ms=duration_ms,
            )

        self._call_history.append(result)
        return result

    def reset_history(self) -> None:
        """Clear the call history (e.g., between scenario turns)."""
        self._call_history.clear()
