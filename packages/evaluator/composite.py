"""
CompositeEvaluator — merges deterministic and semantic evaluation (Phase 4B).

Architecture:
    CompositeEvaluator
        ├── DeterministicEvaluator  (always runs first)
        └── LLMJudgeEvaluator       (optional semantic layer)

The CompositeEvaluator applies a provenance-aware decision policy rather than
a naive FAIL > INCONCLUSIVE > PASS priority across layers.  The five cases
below encode the policy described in ADR-018.

Five-case decision policy:
    Case A — Execution failure (TIMEOUT / ERROR)
        Return deterministic NOT_EVALUATED result.
        DO NOT invoke the LLM.  Infrastructure failures are never agent failures.

    Case B — Deterministic FAIL
        Deterministic FAIL backed by concrete trace evidence has highest
        authority.  An LLM PASS must not erase it.
        The LLM may optionally be called to enrich the explanation/evidence,
        but the final verdict stays FAIL.
        source = COMPOSITE.

    Case C — Deterministic INCONCLUSIVE
        Primary semantic handoff.  The LLM is called to resolve the ambiguity.
        If the LLM succeeds → use the LLM verdict.
        If the LLM fails → retain INCONCLUSIVE.
        All findings from both layers are preserved.
        source = COMPOSITE.

    Case D — Deterministic PASS
        Normally retain PASS.  However, if the LLM identifies a semantic
        violation backed by valid trace evidence, the verdict becomes FAIL.
        An unsupported LLM FAIL must NOT override a deterministic PASS.
        Only LLM FAIL with validated trace-backed evidence can override.
        source = COMPOSITE when LLM ran.

    Case E — No LLM provider
        Result is identical to Phase 4A deterministic evaluation.
        Guarantees graceful degradation.

See ADR-009 and ADR-018 in DECISIONS.md.
"""

from __future__ import annotations

import logging

from packages.core.models.evaluation import (
    EvaluationSource,
    EvaluationStatus,
    EvaluationVerdict,
    ScenarioEvaluationResult,
)
from packages.core.models.scenario import Scenario
from packages.core.models.trace import ExecutionStatus, Trace
from packages.core.providers.base import BaseLLMProvider
from packages.evaluator.deterministic import DeterministicEvaluator
from packages.evaluator.llm_judge import LLMJudgeEvaluator

logger = logging.getLogger(__name__)

# Trace statuses that mean infrastructure failure — never agent failure.
_INFRA_FAILURE: frozenset[ExecutionStatus] = frozenset([
    ExecutionStatus.TIMEOUT,
    ExecutionStatus.ERROR,
])


class CompositeEvaluator:
    """
    Merges deterministic and semantic evaluation into a single authoritative
    ScenarioEvaluationResult.

    Constructor:
        llm_provider: BaseLLMProvider | None
            Pass None to get pure Phase 4A behaviour (Case E).

    Usage:
        evaluator = CompositeEvaluator(llm_provider=my_provider)
        result = await evaluator.evaluate(trace, scenario)
    """

    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self._det_evaluator = DeterministicEvaluator()
        self._llm_evaluator: LLMJudgeEvaluator | None = (
            LLMJudgeEvaluator(llm_provider) if llm_provider is not None else None
        )
        self._has_llm = llm_provider is not None

    @property
    def evaluator_type(self) -> str:
        return "composite"

    async def evaluate(
        self,
        trace: Trace,
        scenario: Scenario,
    ) -> ScenarioEvaluationResult:
        """
        Evaluate a (Trace, Scenario) pair using the composite policy.

        Never raises — all errors are captured in evaluation_status.
        """
        # --- Step 1: always run deterministic evaluation first ---
        try:
            det_result = await self._det_evaluator.evaluate(trace, scenario)
        except Exception as exc:
            logger.error(
                "CompositeEvaluator: DeterministicEvaluator raised unexpectedly "
                "for scenario=%s: %s",
                scenario.id,
                exc,
            )
            severity = (
                scenario.severity.value
                if hasattr(scenario.severity, "value")
                else str(scenario.severity)
            )
            exec_str = (
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
                execution_status=exec_str,
                source=EvaluationSource.DETERMINISTIC,
                deterministic_verdict=EvaluationVerdict.INCONCLUSIVE,
                metadata={"error": str(exc)},
            )

        # --- Case A: infrastructure failure — skip LLM entirely ---
        if trace.status in _INFRA_FAILURE:
            # DeterministicEvaluator already returned NOT_EVALUATED; pass through
            return _stamp_source(det_result, EvaluationSource.DETERMINISTIC)

        # --- Case E: no LLM provider — behave exactly like Phase 4A ---
        if not self._has_llm or self._llm_evaluator is None:
            return _stamp_source(det_result, EvaluationSource.DETERMINISTIC)

        det_verdict = det_result.verdict

        # --- Case B: Deterministic FAIL ---
        if det_verdict == EvaluationVerdict.FAIL:
            return await self._handle_deterministic_fail(trace, scenario, det_result)

        # --- Case C: Deterministic INCONCLUSIVE ---
        if det_verdict == EvaluationVerdict.INCONCLUSIVE:
            return await self._handle_deterministic_inconclusive(
                trace, scenario, det_result
            )

        # --- Case D: Deterministic PASS ---
        return await self._handle_deterministic_pass(trace, scenario, det_result)

    # ------------------------------------------------------------------
    # Case handlers
    # ------------------------------------------------------------------

    async def _handle_deterministic_fail(
        self,
        trace: Trace,
        scenario: Scenario,
        det_result: ScenarioEvaluationResult,
    ) -> ScenarioEvaluationResult:
        """
        Case B — Deterministic FAIL.

        The LLM may enrich findings, but the verdict stays FAIL.
        An LLM PASS cannot erase a deterministic FAIL backed by trace evidence.
        """
        assert self._llm_evaluator is not None

        try:
            llm_result = await self._llm_evaluator.evaluate(
                trace, scenario, det_result
            )
        except Exception as exc:
            logger.warning(
                "CompositeEvaluator Case B: LLM enrichment failed for "
                "scenario=%s (%s); preserving deterministic FAIL",
                scenario.id,
                exc,
            )
            return _stamp_source(det_result, EvaluationSource.COMPOSITE)

        # Merge evidence-enriched findings but ENFORCE the FAIL verdict
        merged_findings = _merge_findings(det_result, llm_result)
        llm_conf = llm_result.llm_confidence

        return det_result.model_copy(update={
            "verdict": EvaluationVerdict.FAIL,  # always
            "findings": merged_findings,
            "source": EvaluationSource.COMPOSITE,
            "deterministic_verdict": det_result.verdict,
            "llm_verdict": llm_result.llm_verdict,
            "llm_confidence": llm_conf,
            "metadata": {
                **det_result.metadata,
                "composite_policy": "case_b_deterministic_fail",
                "llm_reasoning": llm_result.metadata.get("llm_reasoning", ""),
                "note": (
                    "LLM PASS cannot override deterministic FAIL backed by "
                    "trace evidence."
                ) if llm_result.llm_verdict == EvaluationVerdict.PASS else "",
            },
        })

    async def _handle_deterministic_inconclusive(
        self,
        trace: Trace,
        scenario: Scenario,
        det_result: ScenarioEvaluationResult,
    ) -> ScenarioEvaluationResult:
        """
        Case C — Deterministic INCONCLUSIVE.

        Primary semantic handoff: LLM resolves the ambiguity.
        If LLM fails, retain INCONCLUSIVE.
        """
        assert self._llm_evaluator is not None

        try:
            llm_result = await self._llm_evaluator.evaluate(
                trace, scenario, det_result
            )
        except Exception as exc:
            logger.warning(
                "CompositeEvaluator Case C: LLM failed for scenario=%s (%s); "
                "retaining INCONCLUSIVE",
                scenario.id,
                exc,
            )
            return _stamp_source(det_result, EvaluationSource.COMPOSITE)

        # If LLM returned an error result, fall back to deterministic INCONCLUSIVE
        if llm_result.evaluation_status == EvaluationStatus.EVALUATION_ERROR:
            return _stamp_source(det_result, EvaluationSource.COMPOSITE)

        # Use the LLM verdict; preserve findings from both layers
        merged_findings = _merge_findings(det_result, llm_result)

        return det_result.model_copy(update={
            "verdict": llm_result.verdict,
            "evaluation_status": EvaluationStatus.EVALUATED,
            "findings": merged_findings,
            "source": EvaluationSource.COMPOSITE,
            "deterministic_verdict": det_result.verdict,
            "llm_verdict": llm_result.llm_verdict,
            "llm_confidence": llm_result.llm_confidence,
            "metadata": {
                **det_result.metadata,
                "composite_policy": "case_c_deterministic_inconclusive",
                "llm_reasoning": llm_result.metadata.get("llm_reasoning", ""),
            },
        })

    async def _handle_deterministic_pass(
        self,
        trace: Trace,
        scenario: Scenario,
        det_result: ScenarioEvaluationResult,
    ) -> ScenarioEvaluationResult:
        """
        Case D — Deterministic PASS.

        The LLM may identify a semantic violation missed by deterministic rules.
        Only a LLM FAIL backed by valid trace evidence can override a PASS.
        An unsupported LLM FAIL must NOT override.
        """
        assert self._llm_evaluator is not None

        try:
            llm_result = await self._llm_evaluator.evaluate(
                trace, scenario, det_result
            )
        except Exception as exc:
            logger.warning(
                "CompositeEvaluator Case D: LLM failed for scenario=%s (%s); "
                "retaining PASS",
                scenario.id,
                exc,
            )
            return _stamp_source(det_result, EvaluationSource.COMPOSITE)

        # If LLM returned an error result, retain PASS
        if llm_result.evaluation_status == EvaluationStatus.EVALUATION_ERROR:
            return _stamp_source(det_result, EvaluationSource.COMPOSITE)

        llm_verdict = llm_result.llm_verdict or llm_result.verdict

        if llm_verdict == EvaluationVerdict.FAIL:
            # Require valid trace-backed evidence to override PASS
            validated_evidence_count = llm_result.metadata.get(
                "validated_evidence_count", 0
            )
            has_trace_backed = _has_trace_backed_evidence(llm_result)

            if has_trace_backed or validated_evidence_count > 0:
                # Override is permitted — real semantic violation detected
                merged_findings = _merge_findings(det_result, llm_result)
                return det_result.model_copy(update={
                    "verdict": EvaluationVerdict.FAIL,
                    "findings": merged_findings,
                    "source": EvaluationSource.COMPOSITE,
                    "deterministic_verdict": det_result.verdict,
                    "llm_verdict": llm_verdict,
                    "llm_confidence": llm_result.llm_confidence,
                    "metadata": {
                        **det_result.metadata,
                        "composite_policy": "case_d_llm_fail_overrides_pass",
                        "llm_reasoning": llm_result.metadata.get("llm_reasoning", ""),
                    },
                })
            else:
                # Unsupported LLM FAIL — retain PASS
                logger.info(
                    "CompositeEvaluator Case D: LLM returned FAIL without "
                    "trace-backed evidence for scenario=%s; retaining PASS",
                    scenario.id,
                )

        # LLM PASS or LLM INCONCLUSIVE or unsupported FAIL → retain PASS
        merged_findings = _merge_findings(det_result, llm_result)
        return det_result.model_copy(update={
            "verdict": EvaluationVerdict.PASS,
            "findings": merged_findings,
            "source": EvaluationSource.COMPOSITE,
            "deterministic_verdict": det_result.verdict,
            "llm_verdict": llm_verdict,
            "llm_confidence": llm_result.llm_confidence,
            "metadata": {
                **det_result.metadata,
                "composite_policy": "case_d_deterministic_pass",
                "llm_reasoning": llm_result.metadata.get("llm_reasoning", ""),
            },
        })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stamp_source(
    result: ScenarioEvaluationResult,
    source: EvaluationSource,
) -> ScenarioEvaluationResult:
    """Return a copy of result with source stamped (preserves all other fields)."""
    return result.model_copy(update={
        "source": source,
        "deterministic_verdict": result.verdict,
    })


def _merge_findings(
    det_result: ScenarioEvaluationResult,
    llm_result: ScenarioEvaluationResult,
) -> list:
    """
    Merge findings from deterministic and LLM results.

    Deterministic findings come first (they have higher authority).
    LLM findings are appended after.  No deduplication — callers need
    provenance from both layers.
    """
    return list(det_result.findings) + list(llm_result.findings)


def _has_trace_backed_evidence(result: ScenarioEvaluationResult) -> bool:
    """
    Return True if any finding in the result has at least one trace-backed
    evidence item (event_index or tool reference is not None and trace_backed=True).
    """
    for finding in result.findings:
        for ev in finding.evidence:
            if ev.trace_backed and (ev.event_index is not None or ev.tool is not None):
                return True
    return False
