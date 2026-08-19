"""
Execution domain models.

Defines the contracts for execution results, statistics, and metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from packages.core.models.trace import ExecutionStatus, Trace


class ScenarioExecutionResult(BaseModel):
    """
    The execution result of a single scenario.
    """

    scenario_id: str = Field(description="ID of the executed scenario.")
    execution_status: ExecutionStatus = Field(description="Final execution status.")
    trace: Trace = Field(description="The complete execution trace.")
    final_response: str | None = Field(default=None, description="The final response from the agent.")
    error: str | None = Field(default=None, description="Error message if execution failed.")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When execution started.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When execution completed.",
    )
    duration_ms: int = Field(default=0, description="Execution duration in milliseconds.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Deterministic metadata.",
    )


class ChallengePackExecutionStats(BaseModel):
    """
    Aggregate execution statistics for a challenge pack execution.
    """

    total_scenarios: int = Field(default=0, description="Total number of scenarios executed.")
    pending_scenarios: int = Field(default=0, description="Number of pending scenarios.")
    running_scenarios: int = Field(default=0, description="Number of running scenarios.")
    completed_scenarios: int = Field(default=0, description="Number of completed scenarios.")
    failed_scenarios: int = Field(default=0, description="Number of failed scenarios.")
    timeout_scenarios: int = Field(default=0, description="Number of scenarios that timed out.")
    error_scenarios: int = Field(default=0, description="Number of scenarios that errored.")
    total_duration_ms: int = Field(
        default=0,
        description="Total execution duration across all scenarios in milliseconds.",
    )


class ChallengePackExecutionResult(BaseModel):
    """
    The execution result of a complete challenge pack.
    """

    challenge_pack_id: str = Field(description="ID of the executed challenge pack.")
    agent_id: str = Field(description="ID of the executed agent.")
    agent_version: str = Field(description="Version of the executed agent.")
    execution_status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING,
        description="Overall execution status.",
    )
    scenario_results: list[ScenarioExecutionResult] = Field(
        default_factory=list,
        description="Results of individual scenario executions.",
    )
    stats: ChallengePackExecutionStats = Field(
        default_factory=ChallengePackExecutionStats,
        description="Aggregate execution statistics.",
    )
    trace_references: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of scenario_id to trace_id.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Deterministic metadata.",
    )
