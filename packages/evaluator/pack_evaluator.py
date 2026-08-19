"""
ChallengePackEvaluator — top-level evaluator for a complete ChallengePack.

Evaluates an entire set of (Scenario, Trace) pairs and produces a
ChallengePackEvaluationResult with per-scenario results and aggregate statistics.

Critical invariants:
- Each scenario is evaluated independently; one failure does not affect others.
- Execution failures (TIMEOUT/ERROR traces) are counted separately from
  agent behavior failures.
- Evaluator errors are captured and counted separately (never masked as FAIL).
- Scenario ordering in the output matches the input order exactly.
- No direct LLM calls, no external APIs, no sandbox access from this class.

Phase 4B:
- Accepts an optional BaseLLMProvider.  When provided, uses CompositeEvaluator
  internally (deterministic + semantic).  When None, uses DeterministicEvaluator
  only — identical to Phase 4A behaviour.
- Per-scenario metadata records 'evaluation_source' for auditability.
"""

from __future__ import annotations

from uuid import uuid4

from packages.core.models.evaluation import (
    ChallengePackEvaluationResult,
    EvaluationStatus,
    EvaluationVerdict,
    ScenarioEvaluationResult,
)
from packages.core.models.scenario import ChallengePack, Scenario
from packages.core.models.trace import ExecutionStatus, Trace
from packages.core.providers.base import BaseLLMProvider
from packages.evaluator.composite import CompositeEvaluator
from packages.evaluator.deterministic import DeterministicEvaluator


class ChallengePackEvaluator:
    """
    Evaluates a complete ChallengePack execution.

    Input:
        ChallengePack + list of (Scenario, Trace) pairs (in scenario order)

    Output:
        ChallengePackEvaluationResult with:
        - Per-scenario ScenarioEvaluationResult objects
        - Aggregate counts: total, passed, failed, inconclusive
        - Separate counts: execution_failures, evaluation_failures
        - pass_rate property (over evaluated scenarios only)

    The (Scenario, Trace) pairs must be pre-assembled by the caller.
    This evaluator does NOT load traces from disk or interact with the sandbox.

    Phase 4B:
        Pass llm_provider to enable composite (deterministic + semantic)
        evaluation.  Omit it (or pass None) to get pure deterministic behaviour
        — identical to Phase 4A.
    """

    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        if llm_provider is not None:
            # Phase 4B: composite evaluation
            self._evaluator: CompositeEvaluator | DeterministicEvaluator = (
                CompositeEvaluator(llm_provider)
            )
            self._using_composite = True
        else:
            # Phase 4A: pure deterministic
            self._evaluator = DeterministicEvaluator()
            self._using_composite = False

    async def evaluate_pack(
        self,
        pack: ChallengePack,
        scenario_traces: list[tuple[Scenario, Trace]],
        run_id: str | None = None,
    ) -> ChallengePackEvaluationResult:
        """
        Evaluate every (Scenario, Trace) pair in the pack.

        Args:
            pack: The ChallengePack being evaluated.
            scenario_traces: List of (Scenario, Trace) tuples in scenario order.
                             Must have one entry per scenario in the pack.
            run_id: Optional evaluation run identifier. Auto-generated if None.

        Returns:
            ChallengePackEvaluationResult with all scenario results and aggregates.
        """
        if run_id is None:
            run_id = str(uuid4())

        scenario_results: list[ScenarioEvaluationResult] = []
        passed = 0
        failed = 0
        inconclusive = 0
        execution_failures = 0
        evaluation_failures = 0

        for scenario, trace in scenario_traces:
            result = await self._evaluate_one(scenario, trace)
            scenario_results.append(result)

            if result.evaluation_status == EvaluationStatus.NOT_EVALUATED:
                execution_failures += 1
            elif result.evaluation_status == EvaluationStatus.EVALUATION_ERROR:
                evaluation_failures += 1
            else:
                # EVALUATED — count by verdict
                if result.verdict == EvaluationVerdict.PASS:
                    passed += 1
                elif result.verdict == EvaluationVerdict.FAIL:
                    failed += 1
                else:
                    inconclusive += 1

        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=scenario_results,
            total_scenarios=len(scenario_traces),
            passed=passed,
            failed=failed,
            inconclusive=inconclusive,
            execution_failures=execution_failures,
            evaluation_failures=evaluation_failures,
            metadata={
                "pack_name": pack.name,
                "pack_version": pack.version,
                "evaluation_mode": (
                    "composite" if self._using_composite else "deterministic"
                ),
            },
        )

    async def _evaluate_one(
        self,
        scenario: Scenario,
        trace: Trace,
    ) -> ScenarioEvaluationResult:
        """
        Evaluate a single (Scenario, Trace) pair.

        Catches any uncaught exception from the evaluator and records it
        as EVALUATION_ERROR rather than propagating it.
        """
        try:
            return await self._evaluator.evaluate(trace, scenario)
        except Exception as exc:
            severity = (
                scenario.severity.value
                if hasattr(scenario.severity, "value")
                else str(scenario.severity)
            )
            execution_status_str = (
                trace.status.value
                if hasattr(trace.status, "value")
                else str(trace.status)
            )
            return ScenarioEvaluationResult(
                scenario_id=scenario.id,
                trace_id=trace.run_id,
                scenario_name=scenario.name,
                verdict=EvaluationVerdict.INCONCLUSIVE,
                evaluation_status=EvaluationStatus.EVALUATION_ERROR,
                severity=severity,
                findings=[],
                violated_rules=[],
                execution_status=execution_status_str,
                metadata={"error": str(exc)},
            )
