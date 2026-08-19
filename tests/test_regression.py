"""
Focused offline tests for Phase 5A: Regression & Baseline Intelligence.
"""

import json
from datetime import datetime, timezone
import pytest

from packages.core.models.scenario import RiskLevel
from packages.core.models.reliability import (
    ReliabilityAssessment,
    ReliabilityFinding,
    ReliabilityScore,
)
from packages.core.models.regression import (
    RegressionStatus,
    FailureChangeType,
    RegressionFinding,
    RegressionReport,
)
from packages.regression.analyzer import RegressionAnalyzer


def _make_score(
    agent_id: str,
    version: str,
    overall_score: float,
    grade: str = "A",
) -> ReliabilityScore:
    return ReliabilityScore(
        agent_id=agent_id,
        version=version,
        overall_score=overall_score,
        pass_rate=overall_score / 100.0,
        failure_rate=(100.0 - overall_score) / 100.0,
        scenario_count=10,
        pass_count=int(overall_score / 10.0),
        fail_count=10 - int(overall_score / 10.0),
        risk_level=RiskLevel.LOW if overall_score >= 90.0 else RiskLevel.MEDIUM,
        grade=grade,
    )


def _make_assessment(
    agent_id: str = "test-agent",
    agent_version: str = "1.0.0",
    run_id: str = "run-1",
    overall_score: float = 100.0,
    grade: str = "A",
    findings: list[ReliabilityFinding] = None,
    covered_strategies: list[str] = None,
    covered_attack_surfaces: list[str] = None,
    limited: bool = False,
    quality: dict = None,
) -> ReliabilityAssessment:
    metadata = {}
    if limited:
        metadata["limited"] = True
    if quality:
        metadata["quality"] = quality

    return ReliabilityAssessment(
        agent_id=agent_id,
        agent_version=agent_version,
        challenge_pack_id="pack-1",
        run_id=run_id,
        score=_make_score(agent_id, agent_version, overall_score, grade),
        findings=findings or [],
        covered_strategies=covered_strategies or [],
        covered_attack_surfaces=covered_attack_surfaces or [],
        recommendations=[],
        metadata=metadata,
    )


# 1. Regression model validation
def test_regression_model_validation() -> None:
    finding = RegressionFinding(
        change_type=FailureChangeType.NEW,
        category="SAFETY_VIOLATION",
        title="Test Title",
        previous_severity=None,
        current_severity="critical",
        previous_scenarios=[],
        current_scenarios=["sc-1"],
        previous_tools=[],
        current_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        description="A new failure mode",
        priority=100,
    )
    assert finding.change_type == FailureChangeType.NEW
    assert finding.priority == 100

    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.1.0",
        previous_run_id="run-1",
        current_run_id="run-2",
        previous_score=95.0,
        current_score=90.0,
        score_delta=-5.0,
        previous_grade="A",
        current_grade="B",
        status=RegressionStatus.REGRESSED,
        new_failures=[finding],
        metadata={"threshold": 2.0},
    )
    assert report.agent_id == "test-agent"
    assert len(report.new_failures) == 1
    assert report.score_delta == -5.0


# 2. Identical assessments -> STABLE
def test_identical_assessments_stable() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Test Title",
        description="Vulnerability description",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    assessment1 = _make_assessment(overall_score=90.0, grade="B", findings=[finding])
    assessment2 = _make_assessment(overall_score=90.0, grade="B", findings=[finding], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.STABLE
    assert report.score_delta == 0.0
    assert len(report.new_failures) == 0
    assert len(report.fixed_failures) == 0
    assert len(report.persistent_failures) == 1
    assert len(report.severity_changes) == 0


# 3. Positive score delta -> IMPROVED
def test_positive_score_delta_improved() -> None:
    assessment1 = _make_assessment(overall_score=80.0, grade="C")
    assessment2 = _make_assessment(overall_score=85.0, grade="B", run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.IMPROVED
    assert report.score_delta == 5.0


# 4. Negative score delta -> REGRESSED
def test_negative_score_delta_regressed() -> None:
    assessment1 = _make_assessment(overall_score=90.0, grade="B")
    assessment2 = _make_assessment(overall_score=85.0, grade="C", run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.REGRESSED
    assert report.score_delta == -5.0


# 5. Threshold prevents floating-point noise
def test_threshold_prevents_noise() -> None:
    assessment1 = _make_assessment(overall_score=90.0, grade="B")
    
    # 5.1. Positive change of +0.5 (< threshold 2.0)
    assessment2 = _make_assessment(overall_score=90.5, grade="B", run_id="run-2")
    analyzer = RegressionAnalyzer(stability_threshold=2.0)
    report1 = analyzer.compare(assessment1, assessment2)
    assert report1.status == RegressionStatus.STABLE
    assert report1.score_delta == 0.5

    # 5.2. Negative change of -0.1 (< threshold 2.0)
    assessment3 = _make_assessment(overall_score=89.9, grade="B", run_id="run-3")
    report2 = analyzer.compare(assessment1, assessment3)
    assert report2.status == RegressionStatus.STABLE
    assert report2.score_delta == -0.1

    # 5.3. Negative change of -2.1 (> threshold 2.0)
    assessment4 = _make_assessment(overall_score=87.9, grade="B", run_id="run-4")
    report3 = analyzer.compare(assessment1, assessment4)
    assert report3.status == RegressionStatus.REGRESSED
    assert report3.score_delta == -2.1



# 6. New low failure
def test_new_low_failure() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Low Violation",
        description="A minor issue",
        severity="low",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=25,
    )
    assessment1 = _make_assessment(overall_score=95.0, grade="A")
    assessment2 = _make_assessment(overall_score=94.0, grade="A", findings=[finding], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    # Score delta is -1.0, which is stable, and new failure is LOW (not high/critical)
    assert report.status == RegressionStatus.STABLE
    assert len(report.new_failures) == 1
    assert report.new_failures[0].change_type == FailureChangeType.NEW
    assert report.new_failures[0].current_severity == "low"


# 7. New high failure
def test_new_high_failure() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="High Violation",
        description="A major issue",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=75,
    )
    assessment1 = _make_assessment(overall_score=95.0, grade="A")
    assessment2 = _make_assessment(overall_score=94.0, grade="A", findings=[finding], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    # Score delta is -1.0, but a new high failure exists -> REGRESSED
    assert report.status == RegressionStatus.REGRESSED
    assert len(report.new_failures) == 1
    assert report.new_failures[0].current_severity == "high"


# 8. New critical failure
def test_new_critical_failure() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Critical Violation",
        description="A critical issue",
        severity="critical",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=100,
    )
    assessment1 = _make_assessment(overall_score=95.0, grade="A")
    assessment2 = _make_assessment(overall_score=94.0, grade="A", findings=[finding], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    # Overrides to REGRESSED
    assert report.status == RegressionStatus.REGRESSED
    assert len(report.new_failures) == 1
    assert report.new_failures[0].current_severity == "critical"


# 9. Fixed failure
def test_fixed_failure() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Fixed Issue",
        description="A fixed issue",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=75,
    )
    assessment1 = _make_assessment(overall_score=80.0, grade="C", findings=[finding])
    assessment2 = _make_assessment(overall_score=90.0, grade="B", findings=[], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.IMPROVED
    assert len(report.fixed_failures) == 1
    assert report.fixed_failures[0].change_type == FailureChangeType.FIXED
    assert report.fixed_failures[0].previous_severity == "high"


# 10. Persistent failure
def test_persistent_failure() -> None:
    finding1 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Persistent Issue",
        description="An ongoing issue",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    finding2 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Persistent Issue",
        description="An ongoing issue but with new description",
        severity="medium",
        affected_scenarios=["sc-2"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    assessment1 = _make_assessment(overall_score=90.0, grade="B", findings=[finding1])
    assessment2 = _make_assessment(overall_score=90.0, grade="B", findings=[finding2], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.STABLE
    assert len(report.persistent_failures) == 1
    assert report.persistent_failures[0].change_type == FailureChangeType.PERSISTED
    assert report.persistent_failures[0].previous_scenarios == ["sc-1"]
    assert report.persistent_failures[0].current_scenarios == ["sc-2"]


# 11. Severity increase
def test_severity_increase() -> None:
    finding1 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Escalating Issue",
        description="Mild issue",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    finding2 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Escalating Issue",
        description="Severe issue",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=75,
    )
    assessment1 = _make_assessment(overall_score=90.0, grade="B", findings=[finding1])
    assessment2 = _make_assessment(overall_score=90.0, grade="B", findings=[finding2], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    # Score delta is 0.0, but severity increased -> REGRESSED
    assert report.status == RegressionStatus.REGRESSED
    assert len(report.severity_changes) == 1
    assert report.severity_changes[0].change_type == FailureChangeType.SEVERITY_INCREASED
    assert report.severity_changes[0].previous_severity == "medium"
    assert report.severity_changes[0].current_severity == "high"


# 12. Severity decrease
def test_severity_decrease() -> None:
    finding1 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="De-escalating Issue",
        description="Severe issue",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=75,
    )
    finding2 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="De-escalating Issue",
        description="Mild issue",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    assessment1 = _make_assessment(overall_score=90.0, grade="B", findings=[finding1])
    # Let's say score goes to 95.0
    assessment2 = _make_assessment(overall_score=95.0, grade="A", findings=[finding2], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.IMPROVED
    assert len(report.severity_changes) == 1
    assert report.severity_changes[0].change_type == FailureChangeType.SEVERITY_DECREASED
    assert report.severity_changes[0].previous_severity == "high"
    assert report.severity_changes[0].current_severity == "medium"


# 13. Multiple persistent failures
def test_multiple_persistent_failures() -> None:
    f1_a = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Issue 1",
        description="V1",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    f2_a = ReliabilityFinding(
        category="LOOP_FAILURE",
        title="Issue 2",
        description="V1",
        severity="low",
        affected_scenarios=["sc-2"],
        affected_tools=["tool-2"],
        attack_surfaces=["surface-2"],
        evidence=[],
        priority=25,
    )
    f1_b = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Issue 1",
        description="V2",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    f2_b = ReliabilityFinding(
        category="LOOP_FAILURE",
        title="Issue 2",
        description="V2",
        severity="low",
        affected_scenarios=["sc-2"],
        affected_tools=["tool-2"],
        attack_surfaces=["surface-2"],
        evidence=[],
        priority=25,
    )
    assessment1 = _make_assessment(findings=[f1_a, f2_a])
    assessment2 = _make_assessment(findings=[f1_b, f2_b], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert len(report.persistent_failures) == 2


# 14. Attack surface additions
def test_attack_surface_additions() -> None:
    assessment1 = _make_assessment(covered_attack_surfaces=["A", "B"])
    assessment2 = _make_assessment(covered_attack_surfaces=["A", "B", "C"], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.new_attack_surfaces == ["C"]
    assert len(report.resolved_attack_surfaces) == 0


# 15. Attack surface resolution
def test_attack_surface_resolution() -> None:
    assessment1 = _make_assessment(covered_attack_surfaces=["A", "B", "C"])
    assessment2 = _make_assessment(covered_attack_surfaces=["A", "B"], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert len(report.new_attack_surfaces) == 0
    assert report.resolved_attack_surfaces == ["C"]


# 16. Strategy additions
def test_strategy_additions() -> None:
    assessment1 = _make_assessment(covered_strategies=["strat-1"])
    assessment2 = _make_assessment(covered_strategies=["strat-1", "strat-2"], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.new_strategies == ["strat-2"]
    assert len(report.resolved_strategies) == 0


# 17. Strategy resolution
def test_strategy_resolution() -> None:
    assessment1 = _make_assessment(covered_strategies=["strat-1", "strat-2"])
    assessment2 = _make_assessment(covered_strategies=["strat-1"], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert len(report.new_strategies) == 0
    assert report.resolved_strategies == ["strat-2"]


# 18. Critical regression overrides high score
def test_critical_regression_overrides_high_score() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Critical Security Issue",
        description="A major flaw",
        severity="critical",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=100,
    )
    assessment1 = _make_assessment(overall_score=70.0, grade="D")
    # Score improved significantly, but new critical failure was introduced
    assessment2 = _make_assessment(overall_score=95.0, grade="A", findings=[finding], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.REGRESSED
    assert len(report.new_failures) == 1


# 19. High regression overrides score threshold
def test_high_regression_overrides_score_threshold() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="High Security Issue",
        description="A major flaw",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=75,
    )
    assessment1 = _make_assessment(overall_score=80.0, grade="C")
    # Score delta is +5.0 (>= 2.0 threshold), but there is a new HIGH failure
    assessment2 = _make_assessment(overall_score=85.0, grade="B", findings=[finding], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.REGRESSED


# 20. Fixed critical failure improves report
def test_fixed_critical_failure_improves_report() -> None:
    finding = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Critical Security Issue",
        description="A major flaw",
        severity="critical",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=100,
    )
    assessment1 = _make_assessment(overall_score=80.0, grade="C", findings=[finding])
    assessment2 = _make_assessment(overall_score=90.0, grade="B", findings=[], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.IMPROVED
    assert len(report.fixed_failures) == 1
    assert "recommend preserving the regression test/scenario." in report.recommendations


# 21. Recommendation generation
def test_recommendation_generation() -> None:
    f1 = ReliabilityFinding(
        category="AUTHORITY_SPOOFING",
        title="Authority Spoofing vulnerability",
        description="desc",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=75,
    )
    f2 = ReliabilityFinding(
        category="PROMPT_INJECTION",
        title="Prompt Injection vulnerability",
        description="desc",
        severity="medium",
        affected_scenarios=["sc-2"],
        affected_tools=["tool-2"],
        attack_surfaces=["surface-2"],
        evidence=[],
        priority=50,
    )
    assessment1 = _make_assessment()
    assessment2 = _make_assessment(findings=[f1, f2], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert "strengthen identity and authorization verification." in report.recommendations
    assert "strengthen instruction-boundary enforcement." in report.recommendations


# 22. Recommendation deduplication
def test_recommendation_deduplication() -> None:
    f1 = ReliabilityFinding(
        category="PROMPT_INJECTION",
        title="Prompt Injection 1",
        description="desc",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=75,
    )
    f2 = ReliabilityFinding(
        category="PROMPT_INJECTION",
        title="Prompt Injection 2",
        description="desc",
        severity="medium",
        affected_scenarios=["sc-2"],
        affected_tools=["tool-2"],
        attack_surfaces=["surface-2"],
        evidence=[],
        priority=50,
    )
    assessment1 = _make_assessment()
    assessment2 = _make_assessment(findings=[f1, f2], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    # Should only appear once
    assert report.recommendations.count("strengthen instruction-boundary enforcement.") == 1


# 23. Deterministic finding ordering
def test_deterministic_finding_ordering() -> None:
    # 1. priority descending
    # 2. severity descending
    # 3. change_type ascending
    # 4. category ascending
    # 5. title ascending
    f1 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="Z title",
        description="desc",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    f2 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="A title",
        description="desc",
        severity="medium",
        affected_scenarios=["sc-2"],
        affected_tools=["tool-2"],
        attack_surfaces=["surface-2"],
        evidence=[],
        priority=50,
    )
    f3 = ReliabilityFinding(
        category="LOOP_FAILURE",
        title="A title",
        description="desc",
        severity="low",
        affected_scenarios=["sc-3"],
        affected_tools=["tool-3"],
        attack_surfaces=["surface-3"],
        evidence=[],
        priority=25,
    )
    assessment1 = _make_assessment()
    assessment2 = _make_assessment(findings=[f1, f2, f3], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    # Priority 50 (f2, f1) -> Priority 25 (f3)
    # Among priority 50: f2 ("A title") comes before f1 ("Z title")
    names = [f.title for f in report.new_failures]
    assert names == ["A title", "Z title", "A title"]
    assert report.new_failures[0].category == "SAFETY_VIOLATION"
    assert report.new_failures[2].category == "LOOP_FAILURE"


# 24. Deterministic report repeatability
def test_deterministic_report_repeatability() -> None:
    f1 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="A",
        description="desc",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    assessment1 = _make_assessment(findings=[f1])
    assessment2 = _make_assessment(findings=[], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report1 = analyzer.compare(assessment1, assessment2)
    report2 = analyzer.compare(assessment1, assessment2)

    assert report1.model_dump() == report2.model_dump()


# 25. Agent ID mismatch rejection
def test_agent_id_mismatch_rejection() -> None:
    assessment1 = _make_assessment(agent_id="agent-A")
    assessment2 = _make_assessment(agent_id="agent-B")

    analyzer = RegressionAnalyzer()
    with pytest.raises(ValueError, match="Agent identity mismatch"):
        analyzer.compare(assessment1, assessment2)


# 26. Agent version change metadata
def test_agent_version_change_metadata() -> None:
    assessment1 = _make_assessment(agent_version="1.0.0")
    assessment2 = _make_assessment(agent_version="1.1.0", run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.metadata["agent_version_changed"] is True
    assert report.metadata["previous_agent_version"] == "1.0.0"
    assert report.metadata["current_agent_version"] == "1.1.0"


# 27. Limited previous assessment
def test_limited_previous_assessment() -> None:
    assessment1 = _make_assessment(limited=True)
    assessment2 = _make_assessment(run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.INCONCLUSIVE
    assert report.metadata["comparison_limited"] is True


# 28. Limited current assessment
def test_limited_current_assessment() -> None:
    assessment1 = _make_assessment()
    assessment2 = _make_assessment(limited=True, run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.INCONCLUSIVE
    assert report.metadata["comparison_limited"] is True


# 29. Serialization round-trip
def test_serialization_round_trip() -> None:
    f1 = ReliabilityFinding(
        category="SAFETY_VIOLATION",
        title="A",
        description="desc",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=50,
    )
    assessment1 = _make_assessment(findings=[f1])
    assessment2 = _make_assessment(findings=[], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    json_str = report.model_dump_json()
    loaded_report = RegressionReport.model_validate_json(json_str)

    assert report.model_dump() == loaded_report.model_dump()


# 30. Demo authority-spoofing regression
def test_demo_authority_spoofing_regression() -> None:
    f = ReliabilityFinding(
        category="AUTHORITY_SPOOFING",
        title="Vulnerabilities in category: 'AUTHORITY_SPOOFING'",
        description="Agent successfully executed unauthorized command.",
        severity="critical",
        affected_scenarios=["sc-1"],
        affected_tools=["refund_order"],
        attack_surfaces=["authorization-bypass"],
        evidence=[],
        priority=100,
    )
    assessment1 = _make_assessment(overall_score=95.0, grade="A")
    assessment2 = _make_assessment(overall_score=85.0, grade="B", findings=[f], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.REGRESSED
    assert len(report.new_failures) == 1
    assert "strengthen identity and authorization verification." in report.recommendations


# 31. Demo refund-order regression
def test_demo_refund_order_regression() -> None:
    # Finding targeting a specific tool 'refund_order'
    f = ReliabilityFinding(
        category="TOOL_MISUSE",
        title="Exposed vulnerabilities on tool: 'refund_order'",
        description="Agent executed refund_order without authorization.",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["refund_order"],
        attack_surfaces=["authorization-bypass"],
        evidence=[],
        priority=85,
    )
    assessment1 = _make_assessment(overall_score=90.0, grade="B")
    assessment2 = _make_assessment(overall_score=88.0, grade="B", findings=[f], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.REGRESSED
    assert len(report.new_failures) == 1
    assert report.new_failures[0].priority == 85


# 32. Persistent authorization failure
def test_persistent_authorization_failure() -> None:
    f1 = ReliabilityFinding(
        category="AUTHORIZATION_BYPASS",
        title="Bypass auth",
        description="desc",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=85,
    )
    f2 = ReliabilityFinding(
        category="AUTHORIZATION_BYPASS",
        title="Bypass auth",
        description="desc",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["tool-1"],
        attack_surfaces=["surface-1"],
        evidence=[],
        priority=85,
    )
    assessment1 = _make_assessment(findings=[f1])
    assessment2 = _make_assessment(findings=[f2], run_id="run-2")

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment1, assessment2)

    assert report.status == RegressionStatus.STABLE
    assert len(report.persistent_failures) == 1
    assert "prioritize remediation before relying on the agent for affected actions." in report.recommendations


# 33. Full end-to-end previous/current assessment comparison
def test_full_e2e_comparison() -> None:
    # Previous assessment:
    # Overall score: 85.0
    # Findings:
    #   - f_prev_fixed: TOOL_MISUSE on 'charge_payment', high severity, priority 85.
    #   - f_prev_pers: loop failure, low severity, priority 25.
    #   - f_prev_sev_inc: auth bypass on 'refund', medium severity, priority 50.
    f_prev_fixed = ReliabilityFinding(
        category="TOOL_MISUSE",
        title="Exposed vulnerabilities on tool: 'charge_payment'",
        description="desc",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["charge_payment"],
        attack_surfaces=["financial"],
        evidence=[],
        priority=85,
    )
    f_prev_pers = ReliabilityFinding(
        category="LOOP_FAILURE",
        title="Vulnerabilities in category: 'LOOP_FAILURE'",
        description="desc",
        severity="low",
        affected_scenarios=["sc-2"],
        affected_tools=[],
        attack_surfaces=["surface-2"],
        evidence=[],
        priority=25,
    )
    f_prev_sev_inc = ReliabilityFinding(
        category="AUTHORIZATION_BYPASS",
        title="Exposed vulnerabilities on tool: 'refund'",
        description="desc",
        severity="medium",
        affected_scenarios=["sc-3"],
        affected_tools=["refund"],
        attack_surfaces=["surface-3"],
        evidence=[],
        priority=50,
    )
    assessment_prev = _make_assessment(
        overall_score=85.0,
        grade="B",
        findings=[f_prev_fixed, f_prev_pers, f_prev_sev_inc],
        covered_strategies=["strat-A", "strat-B"],
        covered_attack_surfaces=["surf-A", "surf-B"],
    )

    # Current assessment:
    # Overall score: 90.0
    # Findings:
    #   - f_curr_new: prompt injection, high severity, priority 75.
    #   - f_curr_pers: loop failure, low severity, priority 25.
    #   - f_curr_sev_inc: auth bypass on 'refund', high severity (increased), priority 75.
    f_curr_new = ReliabilityFinding(
        category="PROMPT_INJECTION",
        title="Vulnerabilities in category: 'PROMPT_INJECTION'",
        description="desc",
        severity="high",
        affected_scenarios=["sc-4"],
        affected_tools=[],
        attack_surfaces=["surface-4"],
        evidence=[],
        priority=75,
    )
    f_curr_pers = ReliabilityFinding(
        category="LOOP_FAILURE",
        title="Vulnerabilities in category: 'LOOP_FAILURE'",
        description="desc",
        severity="low",
        affected_scenarios=["sc-2"],
        affected_tools=[],
        attack_surfaces=["surface-2"],
        evidence=[],
        priority=25,
    )
    f_curr_sev_inc = ReliabilityFinding(
        category="AUTHORIZATION_BYPASS",
        title="Exposed vulnerabilities on tool: 'refund'",
        description="desc",
        severity="high",
        affected_scenarios=["sc-3"],
        affected_tools=["refund"],
        attack_surfaces=["surface-3"],
        evidence=[],
        priority=75,
    )
    assessment_curr = _make_assessment(
        overall_score=90.0,
        grade="A",
        findings=[f_curr_new, f_curr_pers, f_curr_sev_inc],
        covered_strategies=["strat-A", "strat-C"],
        covered_attack_surfaces=["surf-A", "surf-C"],
        run_id="run-2",
    )

    analyzer = RegressionAnalyzer()
    report = analyzer.compare(assessment_prev, assessment_curr)

    # Check status:
    # Score improved (85 -> 90), but we introduced a new HIGH failure (prompt injection)
    # and a CRITICAL/HIGH severity increased (auth bypass on refund went medium -> high).
    # Either of these overrides to REGRESSED.
    assert report.status == RegressionStatus.REGRESSED
    assert report.score_delta == 5.0

    # Check findings classification
    assert len(report.new_failures) == 1
    assert report.new_failures[0].title == "Vulnerabilities in category: 'PROMPT_INJECTION'"
    assert report.new_failures[0].change_type == FailureChangeType.NEW

    assert len(report.fixed_failures) == 1
    assert report.fixed_failures[0].title == "Exposed vulnerabilities on tool: 'charge_payment'"
    assert report.fixed_failures[0].change_type == FailureChangeType.FIXED

    assert len(report.persistent_failures) == 1
    assert report.persistent_failures[0].title == "Vulnerabilities in category: 'LOOP_FAILURE'"
    assert report.persistent_failures[0].change_type == FailureChangeType.PERSISTED

    assert len(report.severity_changes) == 1
    assert report.severity_changes[0].title == "Exposed vulnerabilities on tool: 'refund'"
    assert report.severity_changes[0].change_type == FailureChangeType.SEVERITY_INCREASED
    assert report.severity_changes[0].previous_severity == "medium"
    assert report.severity_changes[0].current_severity == "high"

    # Check attack surfaces & strategies
    assert report.new_attack_surfaces == ["surf-C"]
    assert report.resolved_attack_surfaces == ["surf-B"]
    assert report.new_strategies == ["strat-C"]
    assert report.resolved_strategies == ["strat-B"]

    # Check recommendations
    assert "strengthen instruction-boundary enforcement." in report.recommendations
    assert "investigate the changed behavior before deployment." in report.recommendations
    assert "recommend preserving the regression test/scenario." in report.recommendations
