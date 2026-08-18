"""
BaseSandbox abstraction.

All agent execution goes through this interface.
Sandbox implementations are pluggable — replacing LocalMockSandbox
with DockerSandbox or E2BSandbox must not require changes to the
evaluation engine or orchestrator.

See ADR-004 in DECISIONS.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from packages.core.models.scenario import Scenario
from packages.core.models.trace import Trace

if TYPE_CHECKING:
    from packages.agent_adapters.base import BaseAgentAdapter


class BaseSandbox(ABC):
    """
    Abstract sandbox for isolated agent execution.

    The sandbox is responsible for:
    1. Setting up an isolated execution environment.
    2. Providing mock/sandboxed tool implementations via ToolRuntime.
    3. Running the agent adapter against a scenario.
    4. Capturing a complete execution trace.
    5. Resetting state between runs.

    Constraint: LocalMockSandbox is NOT a security boundary.
    It exists for development, testing, and the MVP.
    Real isolation requires DockerSandbox or E2BSandbox (Phase 4+).

    See ADR-004 in DECISIONS.md.
    """

    @abstractmethod
    async def execute(
        self,
        scenario: Scenario,
        adapter: "BaseAgentAdapter",
    ) -> Trace:
        """
        Execute one scenario against one agent adapter.

        The sandbox must:
        - Set up the isolated environment for this scenario.
        - Create a ToolRuntime with sandboxed tool implementations.
        - Pass the runtime to the adapter.
        - Capture all events into a Trace.
        - Enforce resource limits from the scenario.

        Args:
            scenario: The scenario to execute.
            adapter: The agent adapter to run.

        Returns:
            A complete Trace of the execution.
        """
        ...

    @abstractmethod
    async def reset(self) -> None:
        """
        Reset the sandbox state to a clean starting point.

        Must be called between scenario executions when reusing a sandbox.
        """
        ...

    @property
    @abstractmethod
    def sandbox_type(self) -> str:
        """Human-readable sandbox type identifier, e.g. 'local_mock'."""
        ...
