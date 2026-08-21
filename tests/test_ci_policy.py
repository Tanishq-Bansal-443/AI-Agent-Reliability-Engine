"""
Offline unit tests for the RegressionGate policy.
"""

from __future__ import annotations

import pytest
from packages.core.models.regression import RegressionReport, RegressionStatus, RegressionFinding, FailureChangeType
from packages.cli.policy import RegressionGate


def make_report(
    status: RegressionStatus,
    score_delta: float = 0.0,
    new_failures: list[RegressionFinding] | None = None,
    severity_changes: list[RegressionFinding] | None = None,
) -> RegressionReport:
    """Helper to synthesize a test RegressionReport."""
    return RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-1",
        current_run_id="run-2",
        previous_score=80.0,
        current_score=80.0 + score_delta,
        score_delta=score_delta,
        previous_grade="B",
        current_grade="B",
        status=status,
        new_failures=new_failures or [],
        fixed_failures=[],
        persistent_failures=[],
        severity_changes=severity_changes or [],
    )


def test_1_regressed_fails() -> None:
    """REGRESSED -> fail when fail_on_regressed is True."""
    report = make_report(status=RegressionStatus.REGRESSED)
    gate = RegressionGate(fail_on_regressed=True)
    assert gate.evaluate(report) is False


def test_2_improved_passes() -> None:
    """IMPROVED -> pass under default config."""
    report = make_report(status=RegressionStatus.IMPROVED, score_delta=5.0)
    gate = RegressionGate()
    assert gate.evaluate(report) is True


def test_3_stable_passes() -> None:
    """STABLE -> pass under default config."""
    report = make_report(status=RegressionStatus.STABLE)
    gate = RegressionGate()
    assert gate.evaluate(report) is True


def test_4_inconclusive_policy_behavior() -> None:
    """INCONCLUSIVE behaves according to configuration."""
    report = make_report(status=RegressionStatus.INCONCLUSIVE)
    # Default is pass (not inconclusive_as_fail)
    gate_default = RegressionGate()
    assert gate_default.evaluate(report) is True

    # Configured as fail
    gate_fail = RegressionGate(inconclusive_as_fail=True)
    assert gate_fail.evaluate(report) is False


def test_5_new_high_failure() -> None:
    """New HIGH failures cause policy evaluation to fail when configured."""
    finding = RegressionFinding(
        change_type=FailureChangeType.NEW,
        category="auth",
        title="High Severity Bypass",
        current_severity="high",
        description="New high vulnerability detected"
    )
    report = make_report(status=RegressionStatus.STABLE, new_failures=[finding])

    # Default shouldn't fail on new high if not configured
    gate_default = RegressionGate()
    assert gate_default.evaluate(report) is True

    # Configured to fail on new high/critical
    gate_policy = RegressionGate(fail_on_new_high_critical=True)
    assert gate_policy.evaluate(report) is False


def test_6_new_critical_failure() -> None:
    """New CRITICAL failures cause policy evaluation to fail when configured."""
    finding = RegressionFinding(
        change_type=FailureChangeType.NEW,
        category="auth",
        title="Critical Security Bypass",
        current_severity="critical",
        description="New critical vulnerability detected"
    )
    report = make_report(status=RegressionStatus.STABLE, new_failures=[finding])

    gate_policy = RegressionGate(fail_on_new_high_critical=True)
    assert gate_policy.evaluate(report) is False


def test_7_severity_increase() -> None:
    """Severity increases fail policy evaluation when configured."""
    finding = RegressionFinding(
        change_type=FailureChangeType.SEVERITY_INCREASED,
        category="auth",
        title="Severity Escalation",
        previous_severity="low",
        current_severity="medium",
        description="Severity increased from low to medium"
    )
    report = make_report(status=RegressionStatus.STABLE, severity_changes=[finding])

    # Default should pass
    gate_default = RegressionGate()
    assert gate_default.evaluate(report) is True

    # Configured to fail
    gate_policy = RegressionGate(fail_on_severity_increases=True)
    assert gate_policy.evaluate(report) is False


def test_8_score_threshold() -> None:
    """Score delta below threshold fails evaluation."""
    # Score drop of 10 points
    report = make_report(status=RegressionStatus.REGRESSED, score_delta=-10.0)

    # Threshold set to -5.0 (allow up to 5 points drop)
    gate_pass = RegressionGate(fail_on_regressed=False, score_delta_threshold=-15.0)
    assert gate_pass.evaluate(report) is True

    # Threshold set to -5.0 (fail on drop larger than 5 points)
    gate_fail = RegressionGate(fail_on_regressed=False, score_delta_threshold=-5.0)
    assert gate_fail.evaluate(report) is False


def test_9_multiple_policy_conditions() -> None:
    """Check that multiple policy constraints combine conjunctively (any violation fails)."""
    finding = RegressionFinding(
        change_type=FailureChangeType.NEW,
        category="auth",
        title="High Severity Bypass",
        current_severity="high",
        description="High severity"
    )
    report = make_report(status=RegressionStatus.IMPROVED, score_delta=2.0, new_failures=[finding])

    # Policy accepts improved status but rejects new high/critical findings
    gate = RegressionGate(
        fail_on_regressed=True,
        fail_on_new_high_critical=True
    )
    assert gate.evaluate(report) is False


def test_10_deterministic_repeatability() -> None:
    """Verify that gate evaluation is pure and repeatable."""
    report = make_report(status=RegressionStatus.REGRESSED)
    gate = RegressionGate(fail_on_regressed=True)
    
    # Check multiple times to verify no state mutations affect results
    assert gate.evaluate(report) is False
    assert gate.evaluate(report) is False
