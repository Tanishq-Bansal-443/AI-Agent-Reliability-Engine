"""
BaseScenarioGenerator abstraction.

Phase 0: Interface only.
Phase 3: Full implementation with template-based and LLM-assisted generators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from packages.core.models.agent import Agent, RiskProfile
from packages.core.models.scenario import AttackStrategy, Scenario


class BaseScenarioGenerator(ABC):
    """
    Abstract scenario generator.

    Takes an Agent, a RiskProfile, and an AttackStrategy, and produces a list
    of adversarial Scenarios targeting the agent's risks.

    See ARCHITECTURE.md §7 for the full scenario architecture.
    """

    @abstractmethod
    async def generate(
        self,
        agent: Agent,
        risk_profile: RiskProfile,
        strategy: AttackStrategy,
    ) -> list[Scenario]:
        """
        Generate adversarial Scenarios from Agent, RiskProfile, and AttackStrategy.

        Args:
            agent: The agent to target.
            risk_profile: The agent's risk profile.
            strategy: The attack strategy to apply.

        Returns:
            A list of generated adversarial scenarios.
        """
        ...
