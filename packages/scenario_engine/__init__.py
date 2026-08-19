"""
Scenario engine package.

Generates Scenario and ChallengePack objects from AgentProfile.
Phase 0: Interface definitions only.
Phase 3: Full adversarial scenario generation.
"""

from packages.scenario_engine.base import BaseScenarioGenerator
from packages.scenario_engine.attack_strategy import AttackStrategyRegistry
from packages.scenario_engine.generator import DeterministicScenarioGenerator
from packages.scenario_engine.validator import validate_scenario

__all__ = [
    "BaseScenarioGenerator",
    "AttackStrategyRegistry",
    "DeterministicScenarioGenerator",
    "validate_scenario",
]
