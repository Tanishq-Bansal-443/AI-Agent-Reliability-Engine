"""
Output rendering helpers for the CLI.
"""

from __future__ import annotations

import json
from pydantic import BaseModel

from packages.core.models.reliability import ReliabilityAssessment
from packages.core.models.regression import RegressionReport
from packages.core.models.adaptive import AdaptiveTestPlan


def render_json(model: BaseModel) -> str:
    """
    Render a Pydantic model as a deterministic JSON string.
    """
    return model.model_dump_json(indent=2)


def render_text(
    assessment: ReliabilityAssessment,
    regression_report: RegressionReport | None = None,
    adaptive_test_plan: AdaptiveTestPlan | None = None,
) -> str:
    """
    Render the plain-text human-readable reliability report.
    """
    from packages.reliability.report import format_text
    return format_text(
        assessment=assessment,
        regression_report=regression_report,
        adaptive_test_plan=adaptive_test_plan,
    )


def render_markdown(
    assessment: ReliabilityAssessment,
    regression_report: RegressionReport | None = None,
    adaptive_test_plan: AdaptiveTestPlan | None = None,
) -> str:
    """
    Render the Markdown human-readable reliability report.
    """
    from packages.reliability.report import format_markdown
    return format_markdown(
        assessment=assessment,
        regression_report=regression_report,
        adaptive_test_plan=adaptive_test_plan,
    )
