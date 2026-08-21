"""
Reliability package.

Foundational models for reliability scoring and regression testing.
Phase 0: Models are defined in core/models/reliability.py.
         This package re-exports them for convenience.
"""

from packages.core.models.reliability import (
    RegressionTest,
    ReliabilityScore,
    ReliabilityFinding,
    ReliabilityAssessment,
)
from packages.reliability.scorer import ReliabilityScorer
from packages.reliability.closed_loop import ReliabilityClosedLoop
from packages.reliability.report import format_text, format_markdown

__all__ = [
    "RegressionTest",
    "ReliabilityScore",
    "ReliabilityFinding",
    "ReliabilityAssessment",
    "ReliabilityScorer",
    "ReliabilityClosedLoop",
    "format_text",
    "format_markdown",
]
