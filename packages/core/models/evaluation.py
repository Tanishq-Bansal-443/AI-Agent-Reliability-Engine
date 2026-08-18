"""
Evaluation domain models.

Defines the contracts for evaluation results, failure details,
and failure taxonomy.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity of a discovered failure."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureCategory(str, Enum):
    """
    Taxonomy of agent failure modes.

    Based on the failure categories in ARCHITECTURE.md.
    """

    TOOL_MISUSE = "TOOL_MISUSE"
    REFUSAL_FAILURE = "REFUSAL_FAILURE"
    INSTRUCTION_VIOLATION = "INSTRUCTION_VIOLATION"
    GOAL_DRIFT = "GOAL_DRIFT"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    DATA_EXPOSURE = "DATA_EXPOSURE"
    LOOP_FAILURE = "LOOP_FAILURE"
    FORMAT_FAILURE = "FORMAT_FAILURE"
    HALLUCINATION = "HALLUCINATION"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    AUTHORIZATION_BYPASS = "AUTHORIZATION_BYPASS"
    TIMEOUT = "TIMEOUT"


class Failure(BaseModel):
    """
    A single failure discovered during evaluation.

    Contains enough context to understand what went wrong,
    why it matters, and how to fix it.
    """

    type: FailureCategory = Field(description="Category of failure.")
    severity: Severity = Field(description="How severe this failure is.")
    description: str = Field(description="Human-readable description of what went wrong.")
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence from the trace that supports this failure (quotes, tool names, etc.).",
    )
    expected_behavior: str = Field(
        description="What the agent should have done.",
    )
    actual_behavior: str = Field(
        description="What the agent actually did.",
    )
    root_cause: str | None = Field(
        default=None,
        description="Root cause analysis (populated by the diagnoser).",
    )
    recommended_fix: str | None = Field(
        default=None,
        description="Recommended remediation (populated by the diagnoser).",
    )
    step_index: int | None = Field(
        default=None,
        description="Index of the trace event where this failure occurred.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """
    The result of evaluating a trace against a scenario's expected behavior.

    Produced by an evaluator and consumed by the scorer/diagnoser.
    """

    trace_id: str = Field(description="The trace that was evaluated.")
    scenario_id: str = Field(description="The scenario that was run.")
    passed: bool = Field(description="Whether the agent passed this scenario.")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized score between 0.0 (complete failure) and 1.0 (perfect).",
    )
    failures: list[Failure] = Field(
        default_factory=list,
        description="All failures discovered during evaluation.",
    )
    evaluator_type: str = Field(
        default="deterministic",
        description="Type of evaluator that produced this result.",
    )
    reasoning: str | None = Field(
        default=None,
        description="Human-readable evaluation reasoning (from LLM judge or deterministic checks).",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def critical_failures(self) -> list[Failure]:
        """All critical-severity failures."""
        return [f for f in self.failures if f.severity == Severity.CRITICAL]

    @property
    def has_critical_failure(self) -> bool:
        """Whether any critical failures were found."""
        return len(self.critical_failures) > 0
