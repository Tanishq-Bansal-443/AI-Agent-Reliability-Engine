"""
RegressionGate policy evaluation for CI/CD gates.
"""

from __future__ import annotations

from packages.core.models.regression import RegressionReport, RegressionStatus, FailureChangeType


class RegressionGate:
    """
    Deterministic gate that evaluates a RegressionReport to decide if a build should pass or fail.
    """

    def __init__(
        self,
        fail_on_regressed: bool = True,
        fail_on_new_high_critical: bool = False,
        fail_on_severity_increases: bool = False,
        score_delta_threshold: float | None = None,
        allow_stable: bool = True,
        allow_improved: bool = True,
        inconclusive_as_fail: bool = False,
    ) -> None:
        self.fail_on_regressed = fail_on_regressed
        self.fail_on_new_high_critical = fail_on_new_high_critical
        self.fail_on_severity_increases = fail_on_severity_increases
        self.score_delta_threshold = score_delta_threshold
        self.allow_stable = allow_stable
        self.allow_improved = allow_improved
        self.inconclusive_as_fail = inconclusive_as_fail

    def evaluate(self, report: RegressionReport) -> bool:
        """
        Evaluate the report against the gate's policy constraints.

        Returns:
            bool: True if the assessment passes (no policy violations),
                  False if it fails (policy violation or regression detected).
        """
        # 1. Fail if REGRESSED and configured to do so
        if report.status == RegressionStatus.REGRESSED and self.fail_on_regressed:
            return False

        # 2. Fail if INCONCLUSIVE and inconclusive_as_fail is True
        if report.status == RegressionStatus.INCONCLUSIVE and self.inconclusive_as_fail:
            return False

        # 3. Fail if STABLE is not allowed
        if report.status == RegressionStatus.STABLE and not self.allow_stable:
            return False

        # 4. Fail if IMPROVED is not allowed
        if report.status == RegressionStatus.IMPROVED and not self.allow_improved:
            return False

        # 5. Fail if score drop exceeds the score delta threshold (if provided)
        # Note: score_delta is current - previous.
        # If score_delta_threshold is e.g. -5.0, then any score_delta < -5.0 fails.
        if self.score_delta_threshold is not None:
            if report.score_delta < self.score_delta_threshold:
                return False

        # 6. Fail if there are new HIGH or CRITICAL findings
        if self.fail_on_new_high_critical:
            for failure in report.new_failures:
                sev = (failure.current_severity or "").lower()
                if sev in ("high", "critical"):
                    return False

        # 7. Fail if there are severity increases
        if self.fail_on_severity_increases:
            for failure in report.severity_changes:
                if failure.change_type == FailureChangeType.SEVERITY_INCREASED:
                    return False
            for failure in report.new_failures:
                if failure.change_type == FailureChangeType.SEVERITY_INCREASED:
                    return False

        return True
