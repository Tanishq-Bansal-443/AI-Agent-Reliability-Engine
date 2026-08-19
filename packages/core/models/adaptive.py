"""
Adaptive Regression Intelligence domain models.

Defines the contracts for adaptive prioritizing, recommendations, and plans.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from packages.core.models.scenario import RiskLevel


class AdaptivePriority(BaseModel):
    """
    Represents the prioritized score and risk level for a single attack strategy.
    """

    strategy_id: str = Field(description="The unique identifier of the attack strategy.")
    priority_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Deterministic priority score clamped to [0, 100].",
    )
    risk_level: RiskLevel = Field(description="Determined RiskLevel for the strategy.")
    reason: str = Field(description="Explanatory text for why this priority was computed.")
    evidence: list[str] = Field(
        default_factory=list,
        description="List of specific trace/finding evidence leading to this priority.",
    )
    recommended_scenario_count: int = Field(
        description="Number of scenarios allocated under the current budget.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional additional context.",
    )


class AdaptiveRecommendation(BaseModel):
    """
    Represents an actionable recommendation for future testing.
    """

    id: str = Field(description="Deterministic recommendation ID (e.g. hashed content).")
    strategy_id: str | None = Field(
        default=None,
        description="The targeted strategy ID, if applicable.",
    )
    target_tool: str | None = Field(
        default=None,
        description="The targeted tool name, if applicable.",
    )
    title: str = Field(description="Short title summarizing the recommendation.")
    description: str = Field(description="Detailed explanation of the risk.")
    priority: float = Field(
        ge=0.0,
        le=100.0,
        description="Priority of the recommendation.",
    )
    reason: str = Field(description="Explicit reasoning for this recommendation.")
    recommended_action: str = Field(description="Actionable instruction on how to remediate/test.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional additional metadata.",
    )


class AdaptiveTestPlan(BaseModel):
    """
    Represents the final testing plan produced by the adaptive engine.
    """

    agent_id: str = Field(description="The agent that is being planned for.")
    agent_version: str = Field(description="The version of the agent.")
    source_run_id: str | None = Field(
        default=None,
        description="The evaluation run ID that served as the primary input.",
    )
    prior_run_id: str | None = Field(
        default=None,
        description="The baseline run ID compared against.",
    )
    budget: int = Field(description="The total scenario budget allocated.")
    selected_strategies: list[str] = Field(
        default_factory=list,
        description="List of strategy IDs selected for the next challenge pack.",
    )
    strategy_priorities: list[AdaptivePriority] = Field(
        default_factory=list,
        description="Prioritized list of strategies with detail.",
    )
    recommendations: list[AdaptiveRecommendation] = Field(
        default_factory=list,
        description="Actionable, prioritized recommendations.",
    )
    coverage_gaps: list[str] = Field(
        default_factory=list,
        description="Coverage gaps identified across strategies, risks, surfaces, and regression status.",
    )
    reasoning_summary: str = Field(
        description="Human-readable summary explaining the overall planning decisions.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary execution metadata.",
    )
