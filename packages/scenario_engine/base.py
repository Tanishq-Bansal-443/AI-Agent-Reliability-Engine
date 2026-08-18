"""
BaseScenarioGenerator abstraction.

Phase 0: Interface only.
Phase 3: Full implementation with template-based and LLM-assisted generators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from packages.core.models.agent import AgentProfile
from packages.core.models.scenario import ChallengePack


class BaseScenarioGenerator(ABC):
    """
    Abstract scenario generator.

    Takes an AgentProfile and produces a ChallengePack containing
    adversarial scenarios targeting the agent's risk surface.

    Phase 3 will implement:
    - TemplateScenarioGenerator: Deterministic, template-based generation
    - LLMScenarioGenerator: LLM-assisted adversarial generation
    - CompositeScenarioGenerator: Combines both

    See ARCHITECTURE.md §7 for the full scenario architecture.
    """

    @abstractmethod
    async def generate(
        self,
        profile: AgentProfile,
        pack_name: str = "Challenge Pack",
    ) -> ChallengePack:
        """
        Generate a ChallengePack from an AgentProfile.

        Args:
            profile: The agent profile to target.
            pack_name: Human-readable name for the challenge pack.

        Returns:
            A ChallengePack with adversarial scenarios.
        """
        ...
