"""
Base abstractions for ScenarioExecutor and ExecutionRunner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.core.models.scenario import Scenario, ChallengePack
    from packages.agent_adapters.base import BaseAgentAdapter
    from packages.core.models.execution import ScenarioExecutionResult, ChallengePackExecutionResult


class BaseScenarioExecutor(ABC):
    """
    Abstract base class for executing a single scenario.
    """

    @abstractmethod
    async def execute(
        self,
        scenario: Scenario,
        adapter: BaseAgentAdapter,
    ) -> ScenarioExecutionResult:
        """
        Execute a single scenario against an agent adapter.

        Args:
            scenario: The scenario to run.
            adapter: The agent adapter to run the scenario against.

        Returns:
            A ScenarioExecutionResult containing trace and execution status.
        """
        ...


class BaseExecutionRunner(ABC):
    """
    Abstract base class for executing a complete ChallengePack.
    """

    @abstractmethod
    async def run(
        self,
        challenge_pack: ChallengePack,
        adapter: BaseAgentAdapter,
    ) -> ChallengePackExecutionResult:
        """
        Execute a challenge pack against an agent adapter.

        Args:
            challenge_pack: The ChallengePack to execute.
            adapter: The agent adapter to run.

        Returns:
            A ChallengePackExecutionResult.
        """
        ...
