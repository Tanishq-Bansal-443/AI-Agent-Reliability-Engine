"""
Scenario domain models.

Defines the contracts for scenarios, challenge packs, attack strategies,
and expected behaviors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AttackStrategyType(str, Enum):
    """
    Known attack strategy types used to generate adversarial scenarios.
    """

    AUTHORITY_SPOOFING = "authority_spoofing"
    URGENCY_PRESSURE = "urgency_pressure"
    AUTHORIZATION_BYPASS = "authorization_bypass"
    CONFIRMATION_BYPASS = "confirmation_bypass"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    PROMPT_INJECTION = "prompt_injection"
    INSTRUCTION_CONFLICT = "instruction_conflict"
    AMBIGUITY_EXPLOITATION = "ambiguity_exploitation"
    TOOL_MISUSE = "tool_misuse"
    DATA_EXFILTRATION = "data_exfiltration"
    MULTI_TURN_MANIPULATION = "multi_turn_manipulation"


class RiskLevel(str, Enum):
    """Risk severity levels, ordered from lowest to highest."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScenarioCategory(str, Enum):
    """Taxonomy of scenario categories."""

    TOOL_MISUSE = "tool_misuse"
    PROMPT_INJECTION = "prompt_injection"
    BOUNDARY_VIOLATION = "boundary_violation"
    INSTRUCTION_FOLLOWING = "instruction_following"
    REFUSAL_BYPASS = "refusal_bypass"
    SAFETY_VIOLATION = "safety_violation"
    DATA_EXFILTRATION = "data_exfiltration"
    GOAL_DRIFT = "goal_drift"


class AttackStrategy(BaseModel):
    """
    Detailed model representing an attack strategy definition in the library.
    """

    id: str = Field(description="Unique strategy identifier (matching AttackStrategyType).")
    name: str = Field(description="Short human-readable name of the strategy.")
    description: str = Field(description="Full strategy description.")
    target_risks: list[str] = Field(default_factory=list, description="Targeted risks (e.g. tool classes, policies).")
    target_attack_surfaces: list[str] = Field(default_factory=list, description="Targeted attack surfaces.")
    generation_guidance: str = Field(description="Guidance on how to generate scenarios using this strategy.")
    expected_failure_modes: list[str] = Field(default_factory=list, description="Expected failure modes when strategy succeeds.")
    default_severity: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Default severity if scenario fails.")


class Risk(BaseModel):
    """A specific risk identified in an agent's profile."""

    target: str = Field(description="What is at risk: a tool name, capability, or policy.")
    risk_level: RiskLevel = Field(description="How severe this risk is.")
    description: str = Field(description="Human-readable risk description.")
    attack_families: list[AttackStrategyType] = Field(
        default_factory=list,
        description="Attack strategies most likely to exploit this risk.",
    )


class ConversationTurn(BaseModel):
    """A single turn in a scenario's conversation."""

    role: str = Field(description="Speaker role: 'user' or 'assistant'.")
    content: str = Field(description="Turn content.")


class ResourceLimits(BaseModel):
    """Execution resource limits for a scenario."""

    max_turns: int = Field(default=10, description="Maximum allowed conversation turns.")
    timeout_seconds: int = Field(
        default=30, description="Wall-clock time limit for the scenario."
    )
    max_tool_calls: int = Field(
        default=20, description="Maximum number of tool calls allowed."
    )


class ExpectedBehavior(BaseModel):
    """
    The expected agent behavior for a scenario.

    Used by the evaluator to determine pass/fail.
    """

    description: str = Field(description="Human-readable expected behavior.")
    should_refuse: bool = Field(
        default=False,
        description="Whether the agent should refuse the request.",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Tools the agent is allowed to call. Empty = any tool is allowed.",
    )
    forbidden_tools: list[str] = Field(
        default_factory=list,
        description="Tools the agent must NOT call in this scenario.",
    )
    required_tools: list[str] = Field(
        default_factory=list,
        description="Tools the agent MUST call to pass.",
    )
    validators: list[str] = Field(
        default_factory=list,
        description="Validator identifiers to apply. E.g., 'no_unauthorized_refund'.",
    )
    rules: list[str] = Field(
        default_factory=list,
        description="Structured, strategy-specific expected behavior rules.",
    )


class Scenario(BaseModel):
    """
    A single test scenario.

    The unit of work for the evaluation engine.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique scenario identifier.",
    )
    name: str = Field(description="Short human-readable name.")
    description: str = Field(description="Full scenario description.")
    category: ScenarioCategory = Field(description="Scenario category.")
    attack_type: AttackStrategyType | None = Field(
        default=None,
        description="The attack strategy type used, if this is an adversarial scenario.",
    )
    target_risk: str | None = Field(
        default=None,
        description="The risk target (e.g. tool name or policy) this scenario targets.",
    )
    turns: list[ConversationTurn] = Field(
        default_factory=list,
        description="Pre-defined conversation turns for multi-turn scenarios.",
    )
    initial_message: str = Field(
        default="",
        description="The initial user message that starts the scenario.",
    )
    expected_behavior: ExpectedBehavior = Field(
        description="What the agent should do in this scenario.",
    )
    resource_limits: ResourceLimits = Field(
        default_factory=ResourceLimits,
        description="Execution resource limits.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Arbitrary tags for filtering and grouping.",
    )
    severity: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Expected severity if this scenario fails.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChallengePack(BaseModel):
    """
    A named, versioned collection of scenarios for a specific agent.

    Built by the scenario engine and executed by the sandbox.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique challenge pack identifier.",
    )
    name: str = Field(description="Human-readable pack name.")
    description: str = Field(default="", description="Pack description.")
    agent_id: str = Field(description="The agent this pack targets.")
    scenarios: list[Scenario] = Field(
        default_factory=list,
        description="The scenarios in this pack.",
    )
    resource_limits: ResourceLimits = Field(
        default_factory=ResourceLimits,
        description="Default resource limits for all scenarios in this pack.",
    )
    version: str = Field(default="1.0.0", description="Pack version.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def scenario_count(self) -> int:
        """Total number of scenarios in this pack."""
        return len(self.scenarios)
