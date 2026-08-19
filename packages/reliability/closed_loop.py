"""
Reliability Closed-Loop Orchestrator.
"""

from __future__ import annotations

from packages.core.models.agent import Agent, RiskProfile
from packages.core.models.scenario import ChallengePack
from packages.core.models.evaluation import ChallengePackEvaluationResult
from packages.core.models.reliability import ReliabilityAssessment
from packages.core.models.regression import RegressionReport
from packages.core.models.adaptive import AdaptiveTestPlan
from packages.regression.analyzer import RegressionAnalyzer
from packages.regression.adaptive import AdaptiveRegressionAnalyzer
from packages.scenario_engine.builder import AdaptiveChallengePackBuilder


class ReliabilityClosedLoop:
    """
    Orchestrates the closed-loop reliability process by running regression analysis,
    generating an adaptive test plan, and constructing the next adaptive challenge pack.
    """

    def __init__(
        self,
        regression_analyzer: RegressionAnalyzer | None = None,
        adaptive_analyzer: AdaptiveRegressionAnalyzer | None = None,
        adaptive_pack_builder: AdaptiveChallengePackBuilder | None = None,
    ) -> None:
        self.regression_analyzer = regression_analyzer or RegressionAnalyzer()
        self.adaptive_analyzer = adaptive_analyzer or AdaptiveRegressionAnalyzer()
        self.adaptive_pack_builder = adaptive_pack_builder or AdaptiveChallengePackBuilder()

    async def plan_next_test_pack(
        self,
        agent: Agent,
        risk_profile: RiskProfile,
        current_assessment: ReliabilityAssessment,
        regression_report: RegressionReport | None = None,
        current_evaluation: ChallengePackEvaluationResult | None = None,
        current_challenge_pack: ChallengePack | None = None,
        budget: int = 10,
    ) -> tuple[AdaptiveTestPlan, ChallengePack]:
        """
        Executes the closed-loop pipeline to plan and build the next ChallengePack.
        Does not execute the challenge pack.
        """
        # Build AdaptiveTestPlan using AdaptiveRegressionAnalyzer
        adaptive_plan = self.adaptive_analyzer.build_test_plan(
            current_assessment=current_assessment,
            regression_report=regression_report,
            current_evaluation=current_evaluation,
            challenge_pack=current_challenge_pack,
            budget=budget,
        )

        # Build the adaptive ChallengePack using AdaptiveChallengePackBuilder
        challenge_pack = await self.adaptive_pack_builder.build(
            agent=agent,
            risk_profile=risk_profile,
            adaptive_plan=adaptive_plan,
        )

        return adaptive_plan, challenge_pack
