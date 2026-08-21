"""
Execution domain models.
"""

from __future__ import annotations

from typing import Any
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
