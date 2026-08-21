"""
ReliabilityEngine implementation for Phase 6A.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel

from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, RiskProfile
from packages.core.models.scenario import ChallengePack, AttackStrategy, ResourceLimits
from packages.core.models.evaluation import ChallengePackEvaluationResult
from packages.core.models.reliability import ReliabilityAssessment
from packages.core.models.regression import RegressionReport
from packages.core.models.adaptive import AdaptiveTestPlan
from packages.core.models.execution import ChallengePackExecutionResult, ExecutionRun, ExecutionRunStatus
from packages.core.models.trace import Trace, ExecutionStatus
from packages.core.providers.base import BaseLLMProvider
from packages.artifacts import ArtifactStore, ReliabilityAssessmentArtifact

from packages.profiler.orchestrator import AgentProfilerOrchestrator
from packages.profiler.base import StaticProfiler, LLMProfiler
from packages.scenario_engine.attack_strategy import AttackStrategyRegistry
from packages.scenario_engine.builder import ChallengePackBuilder
from packages.evaluator.pack_evaluator import ChallengePackEvaluator
from packages.reliability.scorer import ReliabilityScorer
from packages.regression.analyzer import RegressionAnalyzer
from packages.reliability.closed_loop import ReliabilityClosedLoop
from packages.tracing.recorder import save_trace
from packages.sandbox.base import BaseSandbox
from packages.sandbox.local_mock import LocalMockSandbox

from packages.engine.models import ReliabilityEngineConfig, ReliabilityRunResult

logger = logging.getLogger(__name__)


class ReliabilityEngine:
    """
    Top-level orchestrator for the AI Agent Reliability pipeline.

    Composes existing Phase 0-5 components to execute the complete assessment lifecycle:
    1. Agent Profiling (Static and/or LLM)
    2. Strategy Selection
    3. Challenge Pack Generation
    4. Sandbox Execution (with timeout / limit overrides and isolation)
    5. Evaluation (Deterministic and/or LLM Composite)
    6. Reliability Scoring & Finding extraction
    7. Optional Regression Analysis
    8. Optional Adaptive Test Planning
    """

    def __init__(self, config: ReliabilityEngineConfig | None = None) -> None:
        self.config = config or ReliabilityEngineConfig()

    async def assess(
        self,
        adapter: BaseAgentAdapter,
        *,
        previous_assessment: ReliabilityAssessment | None = None,
        previous_challenge_pack_result: ChallengePackEvaluationResult | None = None,
        llm_provider: BaseLLMProvider | None = None,
        sandbox: BaseSandbox | None = None,
    ) -> ReliabilityRunResult:
        """
        Execute the end-to-end reliability pipeline for the given agent adapter.
        """
        run_id = str(uuid4())
        logger.info(f"Starting reliability assessment run_id={run_id} for agent={adapter.agent_id}")

        # Step 1: Agent Profiling
        agent = adapter.get_agent()
        static_profiler = StaticProfiler()
        llm_profiler = None
        if self.config.llm_profiling_enabled:
            if not llm_provider:
                raise ValueError("An LLM provider must be supplied when llm_profiling_enabled is True.")
            llm_profiler = LLMProfiler(llm_provider)

        profiler_orchestrator = AgentProfilerOrchestrator(
            static_profiler=static_profiler,
            llm_profiler=llm_profiler,
        )
        risk_profile = await profiler_orchestrator.profile_agent(agent)

        # Step 2: Attack Strategy Selection
        relevant_strategies = AttackStrategyRegistry.find_relevant_strategies(risk_profile)
        relevant_strategies = sorted(relevant_strategies, key=lambda s: s.id)

        # Step 3: Challenge Pack Building
        pack_builder = ChallengePackBuilder(config=self.config.challenge_pack_limits)
        challenge_pack = await pack_builder.build(agent, risk_profile)

        # Override scenario resource limits if configured
        if self.config.resource_limits_override is not None:
            for scenario in challenge_pack.scenarios:
                scenario.resource_limits = self.config.resource_limits_override

        # Step 4: Sandbox Execution (Isolation & Fallback)
        sb = sandbox or LocalMockSandbox()
        traces: list[Trace] = []
        execution_errors: dict[str, str] = {}

        for scenario in challenge_pack.scenarios:
            if self.config.execution_timeout is not None:
                scenario.resource_limits.timeout_seconds = int(self.config.execution_timeout)

            try:
                trace = await sb.execute(scenario, adapter)
                traces.append(trace)

                if trace.status != ExecutionStatus.SUCCESS:
                    execution_errors[scenario.id] = (
                        trace.error or f"Scenario failed execution with status {trace.status}"
                    )
                    if self.config.fail_fast:
                        break
            except Exception as exc:
                error_msg = str(exc)
                logger.error(f"Sandbox execution failed for scenario={scenario.id}: {error_msg}")
                execution_errors[scenario.id] = error_msg

                # Synthesize error trace to avoid breaking down-stream evaluation and analysis
                error_trace = Trace(
                    run_id=str(uuid4()),
                    agent_id=agent.id,
                    agent_version=agent.version,
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    events=[],
                    status=ExecutionStatus.ERROR,
                    error=error_msg,
                    metadata={"error_type": "sandbox_exception"},
                )
                traces.append(error_trace)

                if self.config.fail_fast:
                    break

        execution_result = ChallengePackExecutionResult(
            pack_id=challenge_pack.id,
            run_id=run_id,
            agent_id=agent.id,
            traces=traces,
            errors=execution_errors,
            metadata={"sandbox_type": getattr(sb, "sandbox_type", "unknown")},
        )

        # Step 5: Evaluation
        eval_provider = llm_provider if self.config.llm_evaluation_enabled else None
        evaluator = ChallengePackEvaluator(llm_provider=eval_provider)

        scenario_traces = []
        traces_by_scenario_id = {t.scenario_id: t for t in traces}
        for scenario in challenge_pack.scenarios:
            t = traces_by_scenario_id.get(scenario.id)
            if t:
                scenario_traces.append((scenario, t))

        evaluation_result = await evaluator.evaluate_pack(
            pack=challenge_pack,
            scenario_traces=scenario_traces,
            run_id=run_id,
        )

        # Step 6: Scoring
        scorer = ReliabilityScorer()
        reliability_assessment = scorer.score(challenge_pack, evaluation_result, risk_profile)

        # Step 7: Regression Comparison
        regression_report = None
        pipeline_warnings: list[str] = []
        if self.config.regression_enabled:
            if previous_assessment is not None:
                try:
                    analyzer = RegressionAnalyzer()
                    regression_report = analyzer.compare(
                        previous=previous_assessment,
                        current=reliability_assessment,
                        previous_challenge_pack_result=previous_challenge_pack_result,
                        current_challenge_pack_result=evaluation_result,
                    )
                except Exception as exc:
                    err_msg = f"Regression analysis failed: {exc}"
                    logger.warning(err_msg)
                    pipeline_warnings.append(err_msg)
            else:
                pipeline_warnings.append(
                    "Regression comparison requested, but no previous_assessment was supplied."
                )

        # Step 8: Adaptive Closed Loop Planning
        adaptive_test_plan = None
        adaptive_challenge_pack = None
        if self.config.adaptive_enabled:
            try:
                closed_loop = ReliabilityClosedLoop()
                adaptive_test_plan, adaptive_challenge_pack = await closed_loop.plan_next_test_pack(
                    agent=agent,
                    risk_profile=risk_profile,
                    current_assessment=reliability_assessment,
                    regression_report=regression_report,
                    current_evaluation=evaluation_result,
                    current_challenge_pack=challenge_pack,
                )
            except Exception as exc:
                err_msg = f"Adaptive closed loop planning failed: {exc}"
                logger.warning(err_msg)
                pipeline_warnings.append(err_msg)

        # Construct ExecutionRun for persistence and tracking
        execution_started = min((t.started_at for t in traces), default=datetime.now(timezone.utc))
        execution_completed = max((t.completed_at for t in traces if t.completed_at), default=datetime.now(timezone.utc))
        execution_duration_ms = int((execution_completed - execution_started).total_seconds() * 1000)

        execution_run = ExecutionRun(
            run_id=execution_result.run_id,
            challenge_pack_id=challenge_pack.id,
            agent_id=agent.id,
            agent_version=agent.version,
            status=ExecutionRunStatus.COMPLETED if not execution_result.errors else ExecutionRunStatus.FAILED,
            started_at=execution_started,
            completed_at=execution_completed,
            duration_ms=execution_duration_ms,
            scenario_ids=[t.scenario_id for t in traces],
            trace_references={t.scenario_id: t.run_id for t in traces},
            stats={
                "total_scenarios": len(traces),
                "failed_scenarios": len(execution_result.errors),
                "successful_scenarios": len(traces) - len(execution_result.errors),
            },
            metadata=execution_result.metadata,
        )

        # Step 9: Persistence (Selective & Robust)
        if self.config.persistence_enabled:
            try:
                store = ArtifactStore(self.config.output_dir, self.config.traces_dir)

                # 1. Save traces individually using standard trace persistent system
                for trace in traces:
                    save_trace(trace, self.config.traces_dir)

                # 2. Save Challenge Pack
                store.save_artifact(challenge_pack, "challenge_packs", f"{challenge_pack.id}.json")

                # 3. Save ExecutionRun
                store.save_artifact(execution_run, "runs", f"{execution_run.run_id}.json")

                # 4. Save Evaluation result
                store.save_artifact(evaluation_result, "evaluations", f"{evaluation_result.run_id}.json")

                # 5. Save Reliability Assessment
                store.save_artifact(reliability_assessment, "reliability", f"{reliability_assessment.run_id}.json")

                # 6. Save Regression report if computed
                if regression_report:
                    store.save_artifact(regression_report, "regression", f"{reliability_assessment.run_id}.json")

                # 7. Save Adaptive test plan if computed
                if adaptive_test_plan:
                    store.save_artifact(adaptive_test_plan, "adaptive", f"{reliability_assessment.run_id}.json")

                # Save Adaptive challenge pack if computed
                if adaptive_challenge_pack:
                    store.save_artifact(adaptive_challenge_pack, "challenge_packs", f"{adaptive_challenge_pack.id}.json")

                # 8. Save Top-Level Assessment Artifact
                top_level_artifact = ReliabilityAssessmentArtifact(
                    assessment_id=run_id,
                    agent_id=agent.id,
                    agent_version=agent.version,
                    challenge_pack_id=challenge_pack.id,
                    execution_run_id=execution_run.run_id,
                    trace_ids=[t.run_id for t in traces],
                    evaluation_result=evaluation_result,
                    reliability_assessment=reliability_assessment,
                    regression_report=regression_report,
                    adaptive_test_plan=adaptive_test_plan,
                    created_at=execution_started,
                    completed_at=datetime.now(timezone.utc),
                    engine_config=self.config.model_dump(mode="json"),
                    warnings=pipeline_warnings,
                    errors=list(execution_result.errors.values()),
                    metadata={
                        "sandbox_type": execution_result.metadata.get("sandbox_type", "unknown"),
                        "adaptive_challenge_pack_id": adaptive_challenge_pack.id if adaptive_challenge_pack else None,
                    }
                )
                store.save_assessment(top_level_artifact)

            except Exception as exc:
                pipeline_warnings.append(f"Persistence layer failed: {exc}")

        # Build final result contract
        metadata = {
            "warnings": pipeline_warnings,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        return ReliabilityRunResult(
            run_id=run_id,
            agent=agent,
            risk_profile=risk_profile,
            selected_strategies=relevant_strategies,
            challenge_pack=challenge_pack,
            execution_result=execution_result,
            evaluation_result=evaluation_result,
            reliability_assessment=reliability_assessment,
            regression_report=regression_report,
            adaptive_test_plan=adaptive_test_plan,
            adaptive_challenge_pack=adaptive_challenge_pack,
            metadata=metadata,
        )

    def _save_model(self, model: BaseModel, directory: Path, filename: str) -> None:
        """Helper function to serialize and write Pydantic model to a file."""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            filepath = directory / filename
            data = model.model_dump(mode="json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            logger.error(f"Failed to save model {model.__class__.__name__} to {directory}/{filename}: {exc}")
            raise
