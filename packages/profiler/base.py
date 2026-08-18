"""
BaseProfiler abstraction.

The profiler analyzes an agent and produces a structured AgentProfile.

Phase 0: Interface only.
Phase 2: Full implementation with:
  - Layer 1: Deterministic analysis (tool name patterns, destructive flags, etc.)
  - Layer 2: LLM-assisted inference via BaseLLMProvider
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from packages.core.models.agent import AgentProfile

if TYPE_CHECKING:
    from packages.agent_adapters.base import BaseAgentAdapter


class BaseProfiler(ABC):
    """
    Abstract profiler that analyzes an agent adapter and produces an AgentProfile.

    The profile drives scenario generation and attack strategy selection.

    See ARCHITECTURE.md §6 for the full profiler architecture.
    """

    @abstractmethod
    async def profile(self, adapter: "BaseAgentAdapter") -> AgentProfile:
        """
        Analyze an agent adapter and produce a structured AgentProfile.

        Args:
            adapter: The agent adapter to profile.

        Returns:
            AgentProfile describing the agent's capabilities and risk surface.
        """
        ...


class StaticProfiler(BaseProfiler):
    """
    A minimal deterministic profiler for Phase 0.

    Derives the AgentProfile directly from the adapter's metadata
    without LLM assistance. Intended for bootstrapping and testing.
    """

    async def profile(self, adapter: "BaseAgentAdapter") -> AgentProfile:
        """
        Build a profile from the adapter's static metadata.

        Uses tool destructive/sensitive flags to identify risk surface.
        """
        from packages.core.models.agent import (
            AgentProfile,
            Capability,
            Constraint,
            RiskSurface,
        )
        from packages.core.models.scenario import AttackStrategy

        agent = adapter.get_agent()

        # Identify capabilities from tools
        capabilities = []
        for tool in agent.tools:
            capability = Capability(
                name=f"can_{tool.name}",
                description=f"Agent can call {tool.name}: {tool.description}",
                risk_level="high" if (tool.destructive or tool.sensitive) else "medium",
                related_tools=[tool.name],
            )
            capabilities.append(capability)

        # Identify constraints from system prompt keywords (deterministic)
        constraints: list[Constraint] = []
        system_prompt_lower = agent.system_prompt.lower()
        if any(kw in system_prompt_lower for kw in ["verify", "authorize", "confirm identity"]):
            constraints.append(
                Constraint(
                    name="identity_verification_required",
                    description="Agent must verify customer identity before sensitive operations.",
                    constraint_type="authorization",
                    enforced_by_prompt=True,
                )
            )
        if any(kw in system_prompt_lower for kw in ["do not", "never", "must not", "prohibited"]):
            constraints.append(
                Constraint(
                    name="policy_restrictions",
                    description="Agent has explicit policy restrictions in system prompt.",
                    constraint_type="policy",
                    enforced_by_prompt=True,
                )
            )

        # Build risk surface
        destructive_tools = [t.name for t in agent.tools if t.destructive]
        sensitive_tools = [t.name for t in agent.tools if t.sensitive]

        attack_families: list[str] = []
        if destructive_tools:
            attack_families.extend([
                AttackStrategy.AUTHORITY_SPOOFING.value,
                AttackStrategy.URGENCY.value,
                AttackStrategy.PROMPT_INJECTION.value,
            ])
        if sensitive_tools:
            attack_families.append(AttackStrategy.SOCIAL_ENGINEERING.value)

        risk_surface = RiskSurface(
            tools=[t.name for t in agent.tools],
            capabilities=[c.name for c in capabilities],
            constraints=[c.name for c in constraints],
            attack_families=attack_families,
            destructive_tools=destructive_tools,
            sensitive_tools=sensitive_tools,
        )

        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            description=agent.description,
            capabilities=capabilities,
            tools=agent.tools,
            constraints=constraints,
            risk_surface=risk_surface,
        )
