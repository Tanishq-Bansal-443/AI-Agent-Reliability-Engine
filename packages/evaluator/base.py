"""
BaseEvaluator abstraction.

Phase 0: Interface only.
Phase 5: Full implementation with:
  - DeterministicEvaluator: Rule-based checks (ADR-009)
  - LLMJudgeEvaluator: Semantic evaluation via BaseLLMProvider
  - CompositeEvaluator: Weighted combination

See ADR-009 in DECISIONS.md: deterministic checks first, LLM judges second.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from packages.core.models.evaluation import EvaluationResult
from packages.core.models.scenario import Scenario
from packages.core.models.trace import Trace


class BaseEvaluator(ABC):
    """
    Abstract evaluator that scores a Trace against a Scenario.

    Evaluators are responsible for:
    - Checking tool calls against forbidden/required tool lists
    - Detecting authorization bypasses, refusal failures, etc.
    - Producing an EvaluationResult with pass/fail and failures

    See ARCHITECTURE.md §10 for the full evaluation architecture.
    See ADR-009 in DECISIONS.md for evaluation strategy.
    """

    @abstractmethod
    async def evaluate(
        self,
        trace: Trace,
        scenario: Scenario,
    ) -> EvaluationResult:
        """
        Evaluate a trace against the scenario's expected behavior.

        Args:
            trace: The execution trace to evaluate.
            scenario: The scenario that was executed.

        Returns:
            EvaluationResult with pass/fail, score, and failure details.
        """
        ...

    @property
    @abstractmethod
    def evaluator_type(self) -> str:
        """Human-readable evaluator type, e.g. 'deterministic' or 'llm_judge'."""
        ...
