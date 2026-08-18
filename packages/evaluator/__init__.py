"""
Evaluator package.

Scores traces against expected behaviors.
Phase 0: Interface definitions only.
Phase 5: Full implementation with deterministic + LLM judge evaluators.
"""

from packages.evaluator.base import BaseEvaluator

__all__ = ["BaseEvaluator"]
