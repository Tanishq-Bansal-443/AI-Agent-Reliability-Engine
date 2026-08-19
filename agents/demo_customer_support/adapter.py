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
        from packages.core.models.agent import RiskProfile

        if self._cached_profile is None:
            # Run the async profiler synchronously for the sync get_profile() interface
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If already in async context, create profile synchronously
                    self._cached_profile = self._build_profile_sync()
                else:
                    risk_profile = loop.run_until_complete(
                        self._profiler.profile(self.get_agent())
                    )
                    self._cached_profile = self._build_profile_from_risk(risk_profile)
            except RuntimeError:
                self._cached_profile = self._build_profile_sync()

        return self._cached_profile

    def _build_profile_sync(self) -> AgentProfile:
        """Build profile synchronously without event loop."""
        import asyncio
        risk_profile = asyncio.run(self._profiler.profile(self.get_agent()))
        return self._build_profile_from_risk(risk_profile)

    def _build_profile_from_risk(self, risk_profile: RiskProfile) -> AgentProfile:
        """Compose and translate RiskProfile into AgentProfile for compatibility."""
        from packages.core.models.agent import AgentProfile, Constraint, RiskSurface
        from packages.core.models.scenario import AttackStrategyType
        
        agent = self.get_agent()
        
        # Build constraints from the evidence/prompt-level analysis
        constraints = []
        if "authority_spoofing" in risk_profile.evidence:
            constraints.append(Constraint(
                name="identity_verification_required",
                description="Agent must verify customer identity before sensitive operations.",
                constraint_type="authorization",
                enforced_by_prompt=True,
            ))
        if any(kw in agent.system_prompt.lower() for kw in ["do not", "never", "must not", "prohibited"]):
            constraints.append(Constraint(
                name="policy_restrictions",
                description="Agent has explicit policy restrictions in system prompt.",
                constraint_type="policy",
                enforced_by_prompt=True,
            ))

        # Build attack families list for backwards compatibility
        attack_families = [surf.attack_surface for surf in risk_profile.attack_surfaces]
        if risk_profile.destructive_tools and AttackStrategyType.PROMPT_INJECTION.value not in attack_families:
            attack_families.append(AttackStrategyType.PROMPT_INJECTION.value)
        if risk_profile.sensitive_tools and AttackStrategyType.DATA_EXFILTRATION.value not in attack_families:
            attack_families.append(AttackStrategyType.DATA_EXFILTRATION.value)

        risk_surface = RiskSurface(
            tools=[t.name for t in agent.tools],
            capabilities=[c.name for c in risk_profile.capabilities],
            constraints=[c.name for c in constraints],
            attack_families=attack_families,
            destructive_tools=risk_profile.destructive_tools,
            sensitive_tools=risk_profile.sensitive_tools,
        )

        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            description=agent.description,
            capabilities=risk_profile.capabilities,
            tools=agent.tools,
            constraints=constraints,
            risk_surface=risk_surface,
        )

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
