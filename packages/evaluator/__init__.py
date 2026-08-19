"""
Evaluator package.

Scores traces against expected behaviors.

Phase 0: BaseEvaluator interface definition only.
Phase 4A: Full deterministic evaluation engine:
  - DeterministicEvaluator: rule-based, FAIL > INCONCLUSIVE > PASS
  - ChallengePackEvaluator: top-level pack-level aggregation
  - Composable validators: ForbiddenToolValidator, RequiredToolValidator,
    AllowedToolValidator, RefusalValidator, ConfirmationValidator,
    ClarificationValidator, ToolExecutionValidator
  - aggregate_verdicts: the single authoritative verdict aggregation function

Phase 4B: Semantic evaluation layer:
  - LLMJudgeEvaluator: provider-agnostic semantic judge (BaseLLMProvider)
  - CompositeEvaluator: merges deterministic + semantic via 5-case policy
  - ChallengePackEvaluator now accepts optional llm_provider
"""

from packages.evaluator.base import BaseEvaluator
from packages.evaluator.composite import CompositeEvaluator
from packages.evaluator.deterministic import DeterministicEvaluator
from packages.evaluator.llm_judge import LLMJudgeEvaluator
from packages.evaluator.pack_evaluator import ChallengePackEvaluator
from packages.evaluator.validators import (
    AllowedToolValidator,
    BaseValidator,
    ClarificationValidator,
    ConfirmationValidator,
    ForbiddenToolValidator,
    RefusalValidator,
    RequiredToolValidator,
    ToolExecutionValidator,
    aggregate_verdicts,
)

__all__ = [
    # Base abstraction (Phase 0)
    "BaseEvaluator",
    # Phase 4A evaluators
    "DeterministicEvaluator",
    "ChallengePackEvaluator",
    # Phase 4B evaluators
    "LLMJudgeEvaluator",
    "CompositeEvaluator",
    # Validators
    "BaseValidator",
    "ForbiddenToolValidator",
    "RequiredToolValidator",
    "AllowedToolValidator",
    "RefusalValidator",
    "ConfirmationValidator",
    "ClarificationValidator",
    "ToolExecutionValidator",
    # Aggregation utility
    "aggregate_verdicts",
]
