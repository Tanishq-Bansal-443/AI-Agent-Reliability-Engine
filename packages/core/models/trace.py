"""
Trace domain models.

Defines the contracts for execution traces — the ground-truth record of
what happened when an agent ran a scenario.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """
    The type of event captured in a trace step.

    Covers every significant event in the agent execution lifecycle.
    """

    USER_INPUT = "user_input"
    MODEL_CALL = "model_call"
    MODEL_OUTPUT = "model_output"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ENVIRONMENT_CHANGE = "environment_change"
    FINAL_RESPONSE = "final_response"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    """The final status of an agent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"

    # Backwards compatibility
    SUCCESS = "success"
    FAILURE = "failure"


class TraceEvent(BaseModel):
    """
    A single event captured during agent execution.

    Every meaningful step in agent execution is recorded as a TraceEvent.
    Events are ordered by step_index and timestamped.
    """

    step_index: int = Field(description="Sequential index of this event in the trace.")
    type: StepType = Field(description="The type of event.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this event occurred.",
    )
    duration_ms: int = Field(
        default=0,
        description="How long this step took in milliseconds.",
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured input data for this step.",
    )
    output_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured output data from this step.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event-specific metadata.",
    )


class Execution(BaseModel):
    """
    Metadata about one execution run.

    Describes which agent version ran which scenario in which sandbox.
    """

    execution_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique execution identifier.",
    )
    agent_id: str = Field(description="Agent that was executed.")
    agent_version: str = Field(description="Version of the agent.")
    scenario_id: str = Field(description="Scenario that was executed.")
    sandbox_type: str = Field(
        default="local_mock",
        description="Type of sandbox used for this execution.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When execution started.",
    )


class Trace(BaseModel):
    """
    The complete execution trace for one scenario run.

    This is the ground-truth record of everything that happened.
    Traces are serialized to JSON and stored in the traces/ directory.
    """

    run_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique trace/run identifier.",
    )
    agent_id: str = Field(description="Agent that was traced.")
    agent_version: str = Field(description="Agent version at time of execution.")
    scenario_id: str = Field(description="Scenario that was executed.")
    scenario_name: str = Field(default="", description="Human-readable scenario name.")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the trace started.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the trace completed.",
    )
    events: list[TraceEvent] = Field(
        default_factory=list,
        description="Ordered list of all execution events.",
    )
    status: ExecutionStatus = Field(
        default=ExecutionStatus.SUCCESS,
        description="Final execution status.",
    )
    error: str | None = Field(
        default=None,
        description="Error message if status is error or timeout.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata (sandbox type, resource usage, etc.).",
    )

    @property
    def duration_ms(self) -> int | None:
        """Total trace duration in milliseconds."""
        if self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() * 1000)

    @property
    def tool_calls(self) -> list[TraceEvent]:
        """All tool call events in this trace."""
        return [e for e in self.events if e.type == StepType.TOOL_CALL]

    @property
    def tool_names_called(self) -> list[str]:
        """Names of all tools called during execution."""
        return [
            e.input_data.get("tool_name", "unknown")
            for e in self.tool_calls
        ]
