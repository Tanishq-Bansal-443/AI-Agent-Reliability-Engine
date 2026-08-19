"""
Regression and Baseline Intelligence domain models.

Defines the contracts for regression reports and findings comparison.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class RegressionStatus(str, Enum):
    """Overall status comparing two evaluations."""

    IMPROVED = "improved"
    REGRESSED = "regressed"
    STABLE = "stable"
    INCONCLUSIVE = "inconclusive"


class FailureChangeType(str, Enum):
    """The type of change detected for a specific failure."""

    NEW = "new"
    FIXED = "fixed"
    PERSISTED = "persisted"
    SEVERITY_INCREASED = "severity_increased"
    SEVERITY_DECREASED = "severity_decreased"


class RegressionFinding(BaseModel):
    """
    A finding comparing previous and current status of a specific failure mode/tool targeting.
    """

    change_type: FailureChangeType = Field(
        description="The type of change for this finding."
    )
    category: str = Field(description="Category of the finding.")
    title: str = Field(description="Normalized title of the finding.")

    previous_severity: str | None = Field(
        default=None, description="Previous severity level of the finding."
    )
    current_severity: str | None = Field(
        default=None, description="Current severity level of the finding."
    )

    previous_scenarios: list[str] = Field(
        default_factory=list, description="List of previous scenarios containing this failure."
    )
    current_scenarios: list[str] = Field(
        default_factory=list, description="List of current scenarios containing this failure."
    )

    previous_tools: list[str] = Field(
        default_factory=list, description="List of previous tools affected."
    )
    current_tools: list[str] = Field(
        default_factory=list, description="List of current tools affected."
    )

    attack_surfaces: list[str] = Field(
        default_factory=list, description="Attack surfaces exposed."
    )

    description: str = Field(description="Human-readable description of the change.")
    priority: int = Field(default=0, description="Priority score of the finding [0, 100].")


class RegressionReport(BaseModel):
    """
    Complete report containing analysis of regression and improvement across two runs.
    """

    agent_id: str = Field(description="The agent compared.")
    agent_version: str = Field(description="Current version of the agent.")

    previous_run_id: str = Field(description="Previous run ID.")
    current_run_id: str = Field(description="Current run ID.")

    previous_score: float = Field(description="Previous overall reliability score.")
    current_score: float = Field(description="Current overall reliability score.")
    score_delta: float = Field(description="Change in overall reliability score.")

    previous_grade: str = Field(description="Previous reliability grade.")
    current_grade: str = Field(description="Current reliability grade.")

    status: RegressionStatus = Field(description="Comparison status (improved/regressed/stable/inconclusive).")

    new_failures: list[RegressionFinding] = Field(
        default_factory=list, description="Failures that are new in the current run."
    )
    fixed_failures: list[RegressionFinding] = Field(
        default_factory=list, description="Failures that were resolved in the current run."
    )
    persistent_failures: list[RegressionFinding] = Field(
        default_factory=list, description="Failures that remain in both runs."
    )
    severity_changes: list[RegressionFinding] = Field(
        default_factory=list, description="Persistent failures whose severity changed."
    )

    new_attack_surfaces: list[str] = Field(
        default_factory=list, description="Newly exposed attack surfaces."
    )
    resolved_attack_surfaces: list[str] = Field(
        default_factory=list, description="Resolved attack surfaces."
    )

    new_strategies: list[str] = Field(
        default_factory=list, description="Newly covered attack strategies."
    )
    resolved_strategies: list[str] = Field(
        default_factory=list, description="Resolved attack strategies."
    )

    recommendations: list[str] = Field(
        default_factory=list, description="Sorted, deduplicated remediation recommendations."
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata with thresholds, versions, and limits."
    )
