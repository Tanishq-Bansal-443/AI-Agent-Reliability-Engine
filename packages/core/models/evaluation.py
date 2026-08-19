"""
Evaluation domain models.

Defines the contracts for evaluation results, failure details,
and failure taxonomy.

Phase 4A adds:
- EvidenceItem: machine-readable trace-backed evidence unit
- EvaluationVerdict: PASS | FAIL | INCONCLUSIVE taxonomy
- EvaluationStatus: EVALUATED | NOT_EVALUATED | EVALUATION_ERROR
- EvaluationFinding: per-validator structured finding
- ScenarioEvaluationResult: authoritative Phase 4A per-scenario result
- ChallengePackEvaluationResult: top-level aggregate across all scenarios

Phase 4B adds:
- EvaluationSource: DETERMINISTIC | LLM | COMPOSITE provenance enum
- LLMJudgeResult: validated structured output from the LLM semantic judge
- ScenarioEvaluationResult provenance fields: source, deterministic_verdict,
  llm_verdict, llm_confidence

The existing EvaluationResult (score-based float) is preserved
unchanged for backward compatibility.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Existing Phase 0 models — preserved exactly
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Severity of a discovered failure."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureCategory(str, Enum):
    """
    Taxonomy of agent failure modes.

    Based on the failure categories in ARCHITECTURE.md.
    """

    TOOL_MISUSE = "TOOL_MISUSE"
    REFUSAL_FAILURE = "REFUSAL_FAILURE"
    INSTRUCTION_VIOLATION = "INSTRUCTION_VIOLATION"
    GOAL_DRIFT = "GOAL_DRIFT"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    DATA_EXPOSURE = "DATA_EXPOSURE"
    LOOP_FAILURE = "LOOP_FAILURE"
    FORMAT_FAILURE = "FORMAT_FAILURE"
    HALLUCINATION = "HALLUCINATION"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    AUTHORIZATION_BYPASS = "AUTHORIZATION_BYPASS"
    TIMEOUT = "TIMEOUT"


class Failure(BaseModel):
    """
    A single failure discovered during evaluation.

    Contains enough context to understand what went wrong,
    why it matters, and how to fix it.
    """

    type: FailureCategory = Field(description="Category of failure.")
    severity: Severity = Field(description="How severe this failure is.")
    description: str = Field(description="Human-readable description of what went wrong.")
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence from the trace that supports this failure (quotes, tool names, etc.).",
    )
    expected_behavior: str = Field(
        description="What the agent should have done.",
    )
    actual_behavior: str = Field(
        description="What the agent actually did.",
    )
    root_cause: str | None = Field(
        default=None,
        description="Root cause analysis (populated by the diagnoser).",
    )
    recommended_fix: str | None = Field(
        default=None,
        description="Recommended remediation (populated by the diagnoser).",
    )
    step_index: int | None = Field(
        default=None,
        description="Index of the trace event where this failure occurred.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """
    The result of evaluating a trace against a scenario's expected behavior.

    Produced by an evaluator and consumed by the scorer/diagnoser.
    """

    trace_id: str = Field(description="The trace that was evaluated.")
    scenario_id: str = Field(description="The scenario that was run.")
    passed: bool = Field(description="Whether the agent passed this scenario.")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized score between 0.0 (complete failure) and 1.0 (perfect).",
    )
    failures: list[Failure] = Field(
        default_factory=list,
        description="All failures discovered during evaluation.",
    )
    evaluator_type: str = Field(
        default="deterministic",
        description="Type of evaluator that produced this result.",
    )
    reasoning: str | None = Field(
        default=None,
        description="Human-readable evaluation reasoning (from LLM judge or deterministic checks).",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def critical_failures(self) -> list[Failure]:
        """All critical-severity failures."""
        return [f for f in self.failures if f.severity == Severity.CRITICAL]

    @property
    def has_critical_failure(self) -> bool:
        """Whether any critical failures were found."""
        return len(self.critical_failures) > 0


# ---------------------------------------------------------------------------
# Phase 4A — new evaluation contracts
# ---------------------------------------------------------------------------

class EvaluationVerdict(str, Enum):
    """
    The three-value verdict taxonomy for Phase 4A.

    Aggregation priority: FAIL > INCONCLUSIVE > PASS
    A PASS from one validator must never override FAIL or INCONCLUSIVE
    from another validator.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvaluationStatus(str, Enum):
    """
    Status of the evaluation process itself.

    Separates infrastructure/execution failures from agent behavior failures.
    A sandbox timeout must never appear as a security FAIL.
    """

    EVALUATED = "EVALUATED"
    NOT_EVALUATED = "NOT_EVALUATED"   # trace.status is TIMEOUT or ERROR
    EVALUATION_ERROR = "EVALUATION_ERROR"  # evaluator itself raised an exception


class EvaluationSource(str, Enum):
    """
    Provenance of the final verdict in a ScenarioEvaluationResult.

    Phase 4B adds a semantic layer (LLM) on top of the deterministic layer.
    This enum records which layer(s) contributed to the final verdict so that
    consumers can distinguish pure deterministic results from composite ones.

    DETERMINISTIC — only the DeterministicEvaluator ran (Phase 4A behaviour).
    LLM           — only the LLMJudgeEvaluator ran (unusual; kept for clarity).
    COMPOSITE     — both layers ran and were merged by CompositeEvaluator.
    """

    DETERMINISTIC = "deterministic"
    LLM = "llm"
    COMPOSITE = "composite"


class EvidenceItem(BaseModel):
    """
    A single machine-readable piece of evidence backing a finding.

    Always references a real TraceEvent when available.
    Evidence items that cannot be trace-backed are marked with
    trace_backed=False so consumers know they are inferred.
    """

    event_index: int | None = Field(
        default=None,
        description="step_index of the TraceEvent this evidence references.",
    )
    tool: str | None = Field(
        default=None,
        description="Tool name if this evidence is about a tool call.",
    )
    content: str = Field(
        description="Human-readable content of this evidence.",
    )
    reason: str = Field(
        description="Why this event/content is evidence for the verdict.",
    )
    trace_backed: bool = Field(
        default=True,
        description="Whether this evidence item references a real TraceEvent.",
    )


class LLMJudgeResult(BaseModel):
    """
    Validated, structured output from the LLM semantic judge.

    Produced by parsing + validating the raw JSON returned by the LLM provider.
    Only instances of this model that pass Pydantic validation are used;
    invalid LLM output is discarded and the system falls back to the
    deterministic result.

    Confidence is constrained to [0.0, 1.0].  Any value outside this range
    causes the entire result to be treated as invalid and discarded.
    """

    verdict: EvaluationVerdict = Field(
        description="The semantic verdict: PASS | FAIL | INCONCLUSIVE.",
    )
    confidence: float = Field(
        description="Confidence score in the verdict, must be in [0.0, 1.0].",
    )
    reasoning: str = Field(
        description="Human-readable reasoning from the LLM judge.",
    )
    findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="Per-aspect findings from the semantic evaluation.",
    )
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Evidence items cited by the LLM judge.",
    )

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"LLMJudgeResult.confidence must be in [0.0, 1.0], got {v}"
            )
        return v


class EvaluationFinding(BaseModel):
    """
    A structured finding produced by a single validator.

    Every FAIL or INCONCLUSIVE finding must carry at least one EvidenceItem
    with trace_backed=True where the trace contains sufficient data.
    A finding without trace-backed evidence must set trace_backed=False
    on all its evidence items — never invent events.
    """

    requirement: str = Field(
        description="What rule or requirement was evaluated (human-readable).",
    )
    verdict: EvaluationVerdict = Field(
        description="PASS | FAIL | INCONCLUSIVE for this specific check.",
    )
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Trace-backed evidence items supporting this verdict.",
    )
    rule: str | None = Field(
        default=None,
        description="The rule identifier that produced this finding (e.g., 'forbidden_tools').",
    )
    category: FailureCategory | None = Field(
        default=None,
        description="Failure category if verdict is FAIL.",
    )
    validator: str = Field(
        description="Name of the validator that produced this finding.",
    )


class ScenarioEvaluationResult(BaseModel):
    """
    The authoritative Phase 4A result for evaluating one scenario.

    Produced by DeterministicEvaluator. Consumed by ChallengePackEvaluator
    and future LLM judge layers.

    Evaluation flow:
        Scenario + Trace → DeterministicEvaluator → ScenarioEvaluationResult

    Verdict aggregation rule (strictly enforced):
        FAIL > INCONCLUSIVE > PASS
    """

    scenario_id: str = Field(description="The scenario that was evaluated.")
    trace_id: str = Field(description="The trace that was consumed.")
    scenario_name: str = Field(default="", description="Human-readable scenario name.")

    verdict: EvaluationVerdict = Field(
        description="Aggregated verdict: PASS | FAIL | INCONCLUSIVE.",
    )
    evaluation_status: EvaluationStatus = Field(
        description="Status of the evaluation process itself.",
    )

    # Severity comes from the scenario definition, not invented by the evaluator.
    severity: str = Field(
        description="Severity level from the scenario (RiskLevel value).",
    )

    findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="Per-validator findings, in validator execution order.",
    )
    violated_rules: list[str] = Field(
        default_factory=list,
        description="Identifiers of rules that were violated (e.g., 'forbidden_tools', 'should_refuse').",
    )

    # Preserve the execution status from the trace for audit purposes.
    execution_status: str = Field(
        description="ExecutionStatus from the trace (success | timeout | error | failure).",
    )

    # ---------------------------------------------------------------------------
    # Phase 4B provenance fields — all optional, default None for backward compat
    # ---------------------------------------------------------------------------

    source: EvaluationSource | None = Field(
        default=None,
        description=(
            "Which evaluation layer(s) produced this result. "
            "None = legacy / pre-Phase-4B result."
        ),
    )
    deterministic_verdict: EvaluationVerdict | None = Field(
        default=None,
        description="The verdict from the DeterministicEvaluator before LLM merging.",
    )
    llm_verdict: EvaluationVerdict | None = Field(
        default=None,
        description="The verdict returned by the LLM judge, if it ran.",
    )
    llm_confidence: float | None = Field(
        default=None,
        description="Confidence score from the LLM judge (0.0–1.0), if it ran.",
    )

    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True iff verdict is PASS."""
        return self.verdict == EvaluationVerdict.PASS

    @property
    def failed(self) -> bool:
        """True iff verdict is FAIL."""
        return self.verdict == EvaluationVerdict.FAIL

    @property
    def inconclusive(self) -> bool:
        """True iff verdict is INCONCLUSIVE."""
        return self.verdict == EvaluationVerdict.INCONCLUSIVE

    @property
    def fail_findings(self) -> list[EvaluationFinding]:
        """All findings with FAIL verdict."""
        return [f for f in self.findings if f.verdict == EvaluationVerdict.FAIL]

    @property
    def was_evaluated(self) -> bool:
        """True iff the evaluator actually ran (execution was not a failure)."""
        return self.evaluation_status == EvaluationStatus.EVALUATED


class ChallengePackEvaluationResult(BaseModel):
    """
    Top-level aggregate result for evaluating a complete ChallengePack execution.

    Input: ExecutionRun + ChallengePack + persisted Traces
    Output: ChallengePackEvaluationResult

    Critical distinction tracked here:
        execution_failures: sandbox/infra failures (NOT agent reliability failures)
        evaluation_failures: evaluator errors (should be zero in production)
        passed/failed/inconclusive: agent behavior verdicts only
    """

    pack_id: str = Field(description="The ChallengePack that was evaluated.")
    run_id: str = Field(description="Unique identifier for this evaluation run.")
    agent_id: str = Field(description="The agent that was evaluated.")

    scenario_results: list[ScenarioEvaluationResult] = Field(
        default_factory=list,
        description="Per-scenario results in scenario order.",
    )

    # Aggregate counts
    total_scenarios: int = Field(description="Total number of scenarios attempted.")
    passed: int = Field(description="Scenarios where agent behavior was PASS.")
    failed: int = Field(description="Scenarios where agent behavior was FAIL.")
    inconclusive: int = Field(description="Scenarios where evidence was insufficient.")
    execution_failures: int = Field(
        default=0,
        description="Scenarios not evaluated due to sandbox/execution failures (TIMEOUT/ERROR).",
    )
    evaluation_failures: int = Field(
        default=0,
        description="Scenarios where the evaluator itself raised an error.",
    )

    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def evaluated_count(self) -> int:
        """Scenarios that were actually evaluated (excludes execution/evaluator failures)."""
        return self.passed + self.failed + self.inconclusive

    @property
    def pass_rate(self) -> float:
        """Pass rate over evaluated scenarios. 0.0 if none were evaluated."""
        if self.evaluated_count == 0:
            return 0.0
        return self.passed / self.evaluated_count

