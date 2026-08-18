"""
DemoAgentAdapter — wraps DemoCustomerSupportAgent for evaluation.

The evaluation engine only depends on BaseAgentAdapter.
It never imports DemoAgentAdapter or DemoCustomerSupportAgent directly.

See ADR-008 in DECISIONS.md.
"""

from __future__ import annotations

from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile
from packages.profiler.base import StaticProfiler
from agents.demo_customer_support.agent import DemoCustomerSupportAgent


class DemoAgentAdapter(BaseAgentAdapter):
    """
    Adapter exposing DemoCustomerSupportAgent through the BaseAgentAdapter interface.

    The evaluation engine uses this adapter to:
    - Get the agent's definition and profile
    - Run scenarios against the agent
    - Observe all tool calls via ToolRuntime

    This adapter never makes real external calls.
    """

    def __init__(self, llm_provider: object | None = None) -> None:
        self._agent = DemoCustomerSupportAgent(llm_provider=llm_provider)
        self._profiler = StaticProfiler()
        self._cached_profile: AgentProfile | None = None

    def get_agent(self) -> Agent:
        """Return the canonical agent definition."""
        return self._agent.get_definition()

    def get_profile(self) -> AgentProfile:
        """
        Return the agent's capability profile.

        Uses StaticProfiler to derive the profile from agent metadata.
        The profile is cached after the first call.
        """
        import asyncio

        if self._cached_profile is None:
            # Run the async profiler synchronously for the sync get_profile() interface
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If already in async context, create profile synchronously
                    self._cached_profile = self._build_profile_sync()
                else:
                    self._cached_profile = loop.run_until_complete(
                        self._profiler.profile(self)
                    )
            except RuntimeError:
                self._cached_profile = self._build_profile_sync()

        return self._cached_profile

    def _build_profile_sync(self) -> AgentProfile:
        """Build profile synchronously without event loop."""
        import asyncio
        return asyncio.run(self._profiler.profile(self))

    async def run(
        self,
        agent_input: AgentInput,
        runtime: object,  # ToolRuntime
    ) -> AgentOutput:
        """
        Run the demo agent against a given input.

        All tool calls are routed through the provided ToolRuntime.
        """
        from packages.sandbox.tool_runtime import ToolRuntime
        assert isinstance(runtime, ToolRuntime), (
            f"Expected ToolRuntime, got {type(runtime).__name__}"
        )
        return await self._agent.run(agent_input, runtime)
