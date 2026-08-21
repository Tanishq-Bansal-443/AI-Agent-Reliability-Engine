"""
Configuration and run result models for the ReliabilityEngine.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from packages.core.models.agent import Agent, RiskProfile
from packages.core.models.scenario import ChallengePack, AttackStrategy, ResourceLimits
from packages.core.models.evaluation import ChallengePackEvaluationResult
from packages.core.models.reliability import ReliabilityAssessment
from packages.core.models.regression import RegressionReport
from packages.core.models.adaptive import AdaptiveTestPlan
from packages.core.models.execution import ChallengePackExecutionResult
from packages.scenario_engine.builder import ChallengePackConfig


class ReliabilityEngineConfig(BaseModel):
    """
    Configuration model for ReliabilityEngine orchestration.
    """

    llm_profiling_enabled: bool = Field(
        default=False,
        description="Whether LLM profiling is enabled.",
    )
    llm_evaluation_enabled: bool = Field(
        default=False,
        description="Whether LLM evaluation is enabled.",
    )
    challenge_pack_limits: ChallengePackConfig = Field(
        default_factory=ChallengePackConfig,
        description="Limits for challenge pack generation (e.g. max scenarios).",
    )
    resource_limits_override: ResourceLimits | None = Field(
        default=None,
        description="Optional resource limits to override in each generated scenario.",
    )
    execution_timeout: float | None = Field(
        default=None,
        description="Optional timeout in seconds to override scenario resource limits.",
    )
    fail_fast: bool = Field(
        default=False,
        description="Whether to halt execution/assessment upon the first scenario execution failure.",
    )
    persistence_enabled: bool = Field(
        default=True,
        description="Whether to persist intermediate artifacts (traces, evaluations, assessments).",
    )
    regression_enabled: bool = Field(
        default=True,
        description="Whether regression analysis is enabled.",
    )
    adaptive_enabled: bool = Field(
        default=True,
        description="Whether adaptive closed-loop planning is enabled.",
    )
    output_dir: str = Field(
        default="data",
        description="Base directory for writing evaluations, assessments, regression reports, and adaptive plans.",
    )
    traces_dir: str = Field(
        default="traces",
        description="Directory to write execution trace files into.",
    )


class ReliabilityRunResult(BaseModel):
    """
    Top-level structured result representing the outcome of a reliability assessment run.
    """

    run_id: str = Field(description="Unique identifier for this engine assessment run.")
    agent: Agent = Field(description="The target agent definition.")
    risk_profile: RiskProfile = Field(description="The produced/used RiskProfile for the agent.")
    selected_strategies: list[AttackStrategy] = Field(
        description="Strategies selected for testing based on the RiskProfile."
    )
    challenge_pack: ChallengePack = Field(description="The ChallengePack generated for testing.")
    execution_result: ChallengePackExecutionResult = Field(
        description="Results of running the challenge pack in the sandbox."
    )
    evaluation_result: ChallengePackEvaluationResult = Field(
        description="Aggregated and per-scenario evaluation outcomes."
    )
    reliability_assessment: ReliabilityAssessment = Field(
        description="The final computed reliability score, findings, and recommendations."
    )
    regression_report: RegressionReport | None = Field(
        default=None,
        description="Comparison results against the previous run, if regression comparison was enabled and ran.",
    )
    adaptive_test_plan: AdaptiveTestPlan | None = Field(
        default=None,
        description="The adaptive test plan generated for the next assessment, if adaptive planning was enabled and ran.",
    )
    adaptive_challenge_pack: ChallengePack | None = Field(
        default=None,
        description="The next adaptive challenge pack, if adaptive planning was enabled and ran.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution and system metadata.",
    )
