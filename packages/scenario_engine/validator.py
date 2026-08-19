"""
Structural validator for generated Scenarios in Phase 2B.
"""

from __future__ import annotations

from packages.core.models.agent import Agent
from packages.core.models.scenario import Scenario, AttackStrategyType


def validate_scenario(scenario: Scenario, agent: Agent) -> None:
    """
    Validate a Scenario against the target Agent definition.
    Raises ValueError if validation fails.
    """
    if not scenario.id:
        raise ValueError("Scenario ID is missing")
    if not scenario.name:
        raise ValueError("Scenario name is missing")
    if not scenario.description:
        raise ValueError("Scenario description is missing")
    if not scenario.category:
        raise ValueError("Scenario category is missing")
    
    # 1. Attack strategy must be present
    if not scenario.attack_type:
        raise ValueError("Scenario attack strategy is missing")
    try:
        AttackStrategyType(scenario.attack_type)
    except ValueError:
        raise ValueError(f"Scenario has unknown/invalid attack strategy type: {scenario.attack_type}")

    # 2. Target risk is absent when required
    if not scenario.target_risk:
        raise ValueError("Scenario target risk is absent")

    # 3. There is no user input
    if not scenario.initial_message:
        raise ValueError("Scenario initial message is missing")

    # 4. Expected behavior is missing
    if not scenario.expected_behavior or not scenario.expected_behavior.description:
        raise ValueError("Expected behavior description is missing")

    # 5. Target tool does not exist (if target_tool is defined in metadata)
    target_tool_name = scenario.metadata.get("target_tool")
    agent_tool_names = {t.name for t in agent.tools}
    if target_tool_name and target_tool_name not in agent_tool_names:
        raise ValueError(f"Target tool '{target_tool_name}' does not exist in agent tools")

    # 6. Scenario references invalid tools (forbidden, required, allowed tools must exist)
    eb = scenario.expected_behavior
    all_referenced_tools = set(eb.allowed_tools + eb.forbidden_tools + eb.required_tools)
    for tool_name in all_referenced_tools:
        if tool_name not in agent_tool_names:
            raise ValueError(f"Scenario references invalid tool: '{tool_name}'")

    # 7. Required tool parameters cannot be satisfied
    if target_tool_name:
        target_tool = next(t for t in agent.tools if t.name == target_tool_name)
        tool_params = scenario.metadata.get("target_tool_parameters", {})
        for param in target_tool.parameters:
            if param.required and param.name not in tool_params:
                raise ValueError(f"Required tool parameter '{param.name}' for tool '{target_tool_name}' was not satisfied")

    # 8. Scenario is structurally malformed (e.g. check turn roles)
    for i, turn in enumerate(scenario.turns):
        if turn.role not in ("user", "assistant"):
            raise ValueError(f"Turn {i} has invalid role '{turn.role}'. Role must be 'user' or 'assistant'.")
