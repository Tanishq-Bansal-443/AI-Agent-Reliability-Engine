"""
Reliability assessment artifact models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from packages.core.models.evaluation import ChallengePackEvaluationResult
from packages.core.models.reliability import ReliabilityAssessment
from packages.core.models.regression import RegressionReport
from packages.core.models.adaptive import AdaptiveTestPlan


class ReliabilityAssessmentArtifact(BaseModel):
    """
    A persistent top-level artifact representing one complete reliability assessment.
    
    Contains references to bulky sub-artifacts (like traces and challenge packs)
    to keep the file size clean and avoid duplicating traces.
    """

    assessment_id: str = Field(description="Unique assessment run identifier.")
    agent_id: str = Field(description="Stable agent identifier.")
    agent_version: str = Field(description="Agent version evaluated.")
    challenge_pack_id: str = Field(description="The ChallengePack ID.")
    execution_run_id: str = Field(description="The ExecutionRun ID.")
    trace_ids: list[str] = Field(
        default_factory=list,
        description="References to individual trace IDs."
    )
    
    evaluation_result: ChallengePackEvaluationResult = Field(
        description="Evaluation results."
    )
    reliability_assessment: ReliabilityAssessment = Field(
        description="Reliability assessment details."
    )
    regression_report: RegressionReport | None = Field(
        default=None,
        description="Regression report if regression comparison ran."
    )
    adaptive_test_plan: AdaptiveTestPlan | None = Field(
        default=None,
        description="Adaptive test plan if adaptive planning ran."
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the assessment started."
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the assessment completed."
    )
    
    engine_config: dict[str, Any] = Field(
        default_factory=dict,
        description="The configuration dictionary of the engine."
    )
    
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings produced during the run."
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors produced during the run."
    )
    
    content_hash: str = Field(
        default="",
        description="SHA-256 integrity hash of the assessment data."
    )
    
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance and other metadata."
    )
