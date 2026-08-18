"""
BaseAgentAdapter abstraction.

The evaluation engine interacts with ALL agents through this interface.
It must never import or depend on any concrete adapter implementation.

See ADR-008 in DECISIONS.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile


class BaseAgentAdapter(ABC):
    """
    Abstract adapter that wraps an agent for evaluation.

    Every agent that participates in the reliability evaluation system
    must be exposed through a concrete implementation of this adapter.

    The evaluation engine, sandbox, and orchestrator only depend on this
    interface — never on the underlying agent implementation.

    Implementations:
        - DemoAgentAdapter: Built-in controllable agent (Phase 0/1)
        - Future: LangChainAgentAdapter, CrewAIAgentAdapter, CustomHTTPAgentAdapter

    See ARCHITECTURE.md §5 for the full adapter architecture.
    """

    @abstractmethod
    def get_agent(self) -> Agent:
        """
        Return the agent definition.

        Returns:
            The Agent model describing this agent's identity, tools, and config.
        """
        ...

    @abstractmethod
    def get_profile(self) -> AgentProfile:
        """
        Return the agent's capability profile.

        The profile is used by the profiler and scenario generator to
        understand what the agent can do and where its risks lie.

        Returns:
            AgentProfile describing capabilities, constraints, and risk surface.
        """
        ...

    @abstractmethod
    async def run(
        self,
        agent_input: AgentInput,
        runtime: "ToolRuntime",  # type: ignore[name-defined]  # avoid circular import
    ) -> AgentOutput:
        """
        Run the agent against a given input.

        The agent must route ALL tool calls through the provided ToolRuntime.
        Direct external calls are prohibited — they would bypass the sandbox.

        Args:
            agent_input: The input to process (messages, conversation_id, metadata).
            runtime: The ToolRuntime through which all tool calls must be routed.

        Returns:
            AgentOutput with the agent's response and a record of tool calls made.
        """
        ...

    @property
    def agent_id(self) -> str:
        """Convenience accessor for the agent ID."""
        return self.get_agent().id

    @property
    def agent_version(self) -> str:
        """Convenience accessor for the agent version."""
        return self.get_agent().version
