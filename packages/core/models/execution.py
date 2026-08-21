"""
Execution domain models.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from packages.core.models.trace import Trace


class ChallengePackExecutionResult(BaseModel):
    """
    Top-level aggregate result for executing a complete ChallengePack.

    Keeps track of:
    - Pack and execution identifiers
    - Scenarios executed (via their traces)
    - Any errors encountered during sandbox execution per scenario
    - Metadata about environment type or execution overrides
    """

    pack_id: str = Field(description="The ChallengePack that was executed.")
    run_id: str = Field(description="Unique identifier for this execution run.")
    agent_id: str = Field(description="The agent that was executed.")
    traces: list[Trace] = Field(
        default_factory=list,
        description="Ordered list of execution traces matching the scenarios in the pack.",
    )
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of scenario_id to error message for scenarios that failed execution.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution metadata.",
    )


from enum import Enum

class ExecutionRunStatus(str, Enum):
    """The status of a complete execution run of a challenge pack."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionRun(BaseModel):
    """
    Metadata and results about a complete execution run of a challenge pack.
    """
    run_id: str = Field(description="Unique identifier for this execution run.")
    challenge_pack_id: str = Field(description="The ChallengePack ID.")
    agent_id: str = Field(description="The agent that was executed.")
    agent_version: str = Field(description="Version of the agent.")
    status: ExecutionRunStatus = Field(
        default=ExecutionRunStatus.PENDING,
        description="Overall execution status of the run."
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When execution started."
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When execution completed."
    )
    duration_ms: int | None = Field(
        default=None,
        description="Total duration in milliseconds."
    )
    scenario_ids: list[str] = Field(
        default_factory=list,
        description="List of scenario IDs executed."
    )
    trace_references: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of scenario_id to trace run_id."
    )
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Summary statistics of the execution run."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution metadata."
    )

