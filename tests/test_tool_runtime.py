"""
Tests for ToolRuntime and ToolRegistry.

Verifies:
- Tool registration and lookup
- Tool call routing
- Error handling for unknown tools
- Call history recording
"""

import pytest
import pytest_asyncio

from packages.sandbox.tool_runtime import (
    ToolRegistry,
    ToolRuntime,
    ToolRegistrationError,
    ToolNotFoundError,
)


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_lookup(self) -> None:
        registry = ToolRegistry()

        def my_tool(x: int) -> int:
            return x * 2

        registry.register("double", my_tool)
        assert registry.is_registered("double")
        assert registry.get("double") is my_tool

    def test_registered_tools_list(self) -> None:
        registry = ToolRegistry()
        registry.register("tool_a", lambda: None)
        registry.register("tool_b", lambda: None)
        assert set(registry.registered_tools) == {"tool_a", "tool_b"}

    def test_duplicate_registration_raises(self) -> None:
        registry = ToolRegistry()
        registry.register("tool", lambda: None)
        with pytest.raises(ToolRegistrationError):
            registry.register("tool", lambda: None)

    def test_replace_existing_tool(self) -> None:
        registry = ToolRegistry()

        def v1() -> str:
            return "v1"

        def v2() -> str:
            return "v2"

        registry.register("tool", v1)
        registry.replace("tool", v2)
        assert registry.get("tool") is v2

    def test_not_found_raises(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            registry.get("nonexistent")

    def test_is_registered_false_for_unknown(self) -> None:
        registry = ToolRegistry()
        assert not registry.is_registered("unknown")


class TestToolRuntime:
    """Tests for ToolRuntime — explicit tool call routing."""

    @pytest.mark.asyncio
    async def test_execute_registered_sync_tool(self) -> None:
        registry = ToolRegistry()
        registry.register("add", lambda x, y: x + y)

        runtime = ToolRuntime(registry)
        result = await runtime.execute_tool("add", {"x": 3, "y": 4})

        assert result.success is True
        assert result.result == 7
        assert result.tool_name == "add"
        assert result.arguments == {"x": 3, "y": 4}

    @pytest.mark.asyncio
    async def test_execute_registered_async_tool(self) -> None:
        registry = ToolRegistry()

        async def async_tool(name: str) -> str:
            return f"hello {name}"

        registry.register("greet", async_tool)
        runtime = ToolRuntime(registry)
        result = await runtime.execute_tool("greet", {"name": "world"})

        assert result.success is True
        assert result.result == "hello world"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error(self) -> None:
        """Unknown tool must return an error result, not raise an exception."""
        registry = ToolRegistry()
        runtime = ToolRuntime(registry)

        result = await runtime.execute_tool("nonexistent_tool", {})

        assert result.success is False
        assert result.error is not None
        assert "not available" in result.error.lower() or "not registered" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tool_exception_is_captured(self) -> None:
        """Exceptions from tool implementations are captured, not propagated."""
        registry = ToolRegistry()

        def exploding_tool() -> None:
            raise ValueError("Tool exploded!")

        registry.register("explode", exploding_tool)
        runtime = ToolRuntime(registry)
        result = await runtime.execute_tool("explode", {})

        assert result.success is False
        assert "Tool exploded!" in result.error

    @pytest.mark.asyncio
    async def test_call_history_is_recorded(self) -> None:
        registry = ToolRegistry()
        registry.register("tool_a", lambda: "a")
        registry.register("tool_b", lambda: "b")

        runtime = ToolRuntime(registry)
        await runtime.execute_tool("tool_a", {})
        await runtime.execute_tool("tool_b", {})

        history = runtime.call_history
        assert len(history) == 2
        assert history[0].tool_name == "tool_a"
        assert history[1].tool_name == "tool_b"

    @pytest.mark.asyncio
    async def test_history_includes_failed_calls(self) -> None:
        """Even failed calls (unknown tools) are recorded in history."""
        registry = ToolRegistry()
        runtime = ToolRuntime(registry)

        await runtime.execute_tool("missing", {})

        history = runtime.call_history
        assert len(history) == 1
        assert history[0].success is False

    @pytest.mark.asyncio
    async def test_reset_history(self) -> None:
        registry = ToolRegistry()
        registry.register("tool", lambda: None)
        runtime = ToolRuntime(registry)

        await runtime.execute_tool("tool", {})
        assert len(runtime.call_history) == 1

        runtime.reset_history()
        assert len(runtime.call_history) == 0

    @pytest.mark.asyncio
    async def test_duration_is_recorded(self) -> None:
        import asyncio

        registry = ToolRegistry()

        async def slow_tool() -> str:
            await asyncio.sleep(0.01)
            return "done"

        registry.register("slow", slow_tool)
        runtime = ToolRuntime(registry)
        result = await runtime.execute_tool("slow", {})

        assert result.duration_ms >= 10  # at least 10ms

    @pytest.mark.asyncio
    async def test_no_direct_imports_of_unittest_mock(self) -> None:
        """
        Verify that ToolRuntime does not IMPORT unittest.mock.
        This enforces ADR-005.
        """
        import inspect
        from packages.sandbox import tool_runtime

        source = inspect.getsource(tool_runtime)

        # Check that 'import unittest.mock' or 'from unittest.mock import' is not present
        # (mentions in docstrings/comments explaining WHY it's excluded are fine)
        import ast
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "unittest.mock" not in alias.name, (
                        "ToolRuntime must not import unittest.mock (see ADR-005)"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and "unittest.mock" in node.module:
                    pytest.fail(
                        "ToolRuntime must not import unittest.mock (see ADR-005)"
                    )
