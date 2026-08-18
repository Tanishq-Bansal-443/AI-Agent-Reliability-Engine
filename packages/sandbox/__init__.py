"""
Sandbox package.

Contains the execution infrastructure for running agents in isolation.

Key components:
- BaseSandbox: Abstract interface for sandbox implementations
- ToolRuntime + ToolRegistry: Explicit tool call routing (no unittest.mock)
- LocalMockSandbox: In-process sandbox for Phase 0/1

See ADR-004 and ADR-005 in DECISIONS.md.
"""

from packages.sandbox.base import BaseSandbox
from packages.sandbox.tool_runtime import ToolRegistry, ToolRuntime

__all__ = ["BaseSandbox", "ToolRegistry", "ToolRuntime"]
