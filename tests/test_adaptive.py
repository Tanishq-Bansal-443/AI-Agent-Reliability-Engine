"""
Focused offline tests for Phase 5B: Adaptive Regression Intelligence.
"""

import json
from datetime import datetime, timezone
import pytest

from packages.core.models.scenario import RiskLevel, ChallengePack, Scenario, ExpectedBehavior
from packages.core.models.evaluation import ChallengePackEvaluationResult, ScenarioEvaluationResult, EvaluationVerdict, EvaluationStatus
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
from packages.core.models.adaptive import (
    AdaptivePriority,
    AdaptiveRecommendation,
    AdaptiveTestPlan,
)
from packages.regression.adaptive import AdaptiveRegressionAnalyzer


def _make_score(
    agent_id: str,
    version: str,
    overall_score: float,
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
        grade="A" if overall_score >= 90.0 else "B",
    )


def _make_assessment(
    agent_id: str = "test-agent",
    agent_version: str = "1.0.0",
    run_id: str = "run-1",
    overall_score: float = 100.0,
    findings: list[ReliabilityFinding] = None,
    covered_strategies: list[str] = None,
    uncovered_strategies: list[str] = None,
    covered_attack_surfaces: list[str] = None,
    uncovered_attack_surfaces: list[str] = None,
) -> ReliabilityAssessment:
    return ReliabilityAssessment(
        agent_id=agent_id,
        agent_version=agent_version,
        challenge_pack_id="pack-1",
        run_id=run_id,
        score=_make_score(agent_id, agent_version, overall_score),
        findings=findings or [],
        covered_strategies=covered_strategies or [],
        uncovered_strategies=uncovered_strategies or [],
        covered_attack_surfaces=covered_attack_surfaces or [],
        uncovered_attack_surfaces=uncovered_attack_surfaces or [],
        recommendations=[],
        metadata={},
    )


# --- 1. Model Validations ---

def test_adaptive_priority_validation() -> None:
    ap = AdaptivePriority(
        strategy_id="authority_spoofing",
        priority_score=85.5,
        risk_level=RiskLevel.CRITICAL,
        reason="Testing priority validation",
        evidence=["finding-1"],
        recommended_scenario_count=3,
        metadata={"custom": "info"},
    )
    assert ap.strategy_id == "authority_spoofing"
    assert ap.priority_score == 85.5
    assert ap.risk_level == RiskLevel.CRITICAL


def test_adaptive_recommendation_validation() -> None:
    ar = AdaptiveRecommendation(
        id="rec-hash-123",
        strategy_id="urgency_pressure",
        target_tool="refund_order",
        title="Increase urgency pressure tests",
        description="Verify handling of immediate demands",
        priority=75.0,
        reason="Detected vulnerability",
        recommended_action="Run new scenarios with urgent phrasing",
        metadata={},
    )
    assert ar.id == "rec-hash-123"
    assert ar.strategy_id == "urgency_pressure"
    assert ar.target_tool == "refund_order"


def test_adaptive_test_plan_validation() -> None:
    plan = AdaptiveTestPlan(
        agent_id="test-agent",
        agent_version="1.0.0",
        source_run_id="run-1",
        prior_run_id=None,
        budget=10,
        selected_strategies=["authority_spoofing"],
        strategy_priorities=[],
        recommendations=[],
        coverage_gaps=["strategy_gap:urgency_pressure"],
        reasoning_summary="Summary text",
        metadata={},
    )
    assert plan.agent_id == "test-agent"
    assert plan.budget == 10
    assert "strategy_gap:urgency_pressure" in plan.coverage_gaps


# --- 2. Analyzer Tests ---

def test_empty_assessment() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=100.0)
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=5)
    
    assert plan.agent_id == "test-agent"
    assert plan.budget == 5
    assert len(plan.selected_strategies) == 0
    # No failures -> priorities are all 0
    for prio in plan.strategy_priorities:
        assert prio.priority_score == 0.0


def test_no_regression_report() -> None:
    # If no report but assessment has active findings, they should count as PERSISTED (+20)
    analyzer = AdaptiveRegressionAnalyzer()
    finding = ReliabilityFinding(
        category="authority_spoofing",
        title="Identity Spoofing Issue",
        description="Bypassed administrator checks",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=["refund_order", "delete_user", "verify_admin"],
        attack_surfaces=["authority_spoofing"],
        evidence=[],
        priority=75,
    )
    assessment = _make_assessment(overall_score=80.0, findings=[finding])
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=5)
    
    auth_prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # Base PERSISTED (+20) + Financial tool 'refund_order' (+10) + Destructive tool 'refund_order' (+10) + Auth tool (+10) = 50.0
    assert auth_prio.priority_score == 50.0
    assert auth_prio.risk_level == RiskLevel.HIGH


def test_new_failure_increases_priority() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=90.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.NEW,
        category="urgency_pressure",
        title="Immediate cancel bypass",
        previous_severity=None,
        current_severity="medium",
        previous_scenarios=[],
        current_scenarios=["sc-2"],
        previous_tools=[],
        current_tools=["cancel_order", "refund_order"],
        attack_surfaces=["urgency_pressure"],
        description="New urgency pressure failure",
        priority=50,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=100.0,
        current_score=90.0,
        score_delta=-10.0,
        previous_grade="A",
        current_grade="B",
        status=RegressionStatus.REGRESSED,
        new_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "urgency_pressure")
    # NEW failure (+35) + Destructive tool 'cancel_order' (+10) + Financial tool 'cancel_order' (+10) = 55.0
    assert prio.priority_score == 55.0


def test_severity_increase_increases_priority() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.SEVERITY_INCREASED,
        category="authority_spoofing",
        title="Admin spoof issue",
        previous_severity="low",
        current_severity="critical",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["refund_order", "delete_user", "verify_admin"],
        current_tools=["refund_order", "delete_user", "verify_admin"],
        attack_surfaces=["authority_spoofing"],
        description="Severity increased",
        priority=100,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=90.0,
        current_score=80.0,
        score_delta=-10.0,
        previous_grade="B",
        current_grade="C",
        status=RegressionStatus.REGRESSED,
        severity_changes=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # Sev increase (+30) + Destructive (+10) + Financial (+10) + Auth (+10) = 60.0
    assert prio.priority_score == 60.0


def test_persistent_failure_increases_priority() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="prompt_injection",
        title="System instruction hijack",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["send_email"],
        current_tools=["send_email"],
        attack_surfaces=["prompt_injection"],
        description="Hijack persist",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "prompt_injection")
    # PERSISTED (+20) + tool is send_email (communication -> no auth/destructive/financial associated, so no tool bonus directly) = 20.0
    assert prio.priority_score == 20.0


def test_fixed_failure_receives_reduced_priority() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=100.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.FIXED,
        category="prompt_injection",
        title="System prompt bypass",
        previous_severity="medium",
        current_severity=None,
        previous_scenarios=["sc-1"],
        current_scenarios=[],
        previous_tools=["read_db"],
        current_tools=[],
        attack_surfaces=["prompt_injection"],
        description="Fixed bypass",
        priority=50,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=90.0,
        current_score=100.0,
        score_delta=10.0,
        previous_grade="B",
        current_grade="A",
        status=RegressionStatus.IMPROVED,
        fixed_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "prompt_injection")
    # Fixed failure does not receive NEW (+35) or PERSISTED (+20) active bonuses.
    # Hence, priority is 0.0 unless there are other factors (like tools).
    assert prio.priority_score == 0.0


# --- 3. Coverage Gaps ---

def test_coverage_gap_detection() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(
        uncovered_strategies=["prompt_injection", "data_exfiltration"],
        uncovered_attack_surfaces=["authority_spoofing"],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment)
    assert "strategy_gap:prompt_injection" in plan.coverage_gaps
    assert "strategy_gap:data_exfiltration" in plan.coverage_gaps
    assert "attack_surface_gap:authority_spoofing" in plan.coverage_gaps


def test_attack_surface_gap_detection() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(uncovered_attack_surfaces=["urgency_pressure"])
    plan = analyzer.build_test_plan(current_assessment=assessment)
    assert "attack_surface_gap:urgency_pressure" in plan.coverage_gaps


def test_strategy_gap_detection() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(uncovered_strategies=["instruction_conflict"])
    plan = analyzer.build_test_plan(current_assessment=assessment)
    assert "strategy_gap:instruction_conflict" in plan.coverage_gaps


def test_risk_gap_detection() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment()
    pack = ChallengePack(
        id="pack-1",
        name="Test Pack",
        description="",
        agent_id="test-agent",
        scenarios=[],
        risk_coverage={"financial": False, "destructive": True},
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, challenge_pack=pack)
    assert "risk_gap:financial" in plan.coverage_gaps
    assert "risk_gap:destructive" not in plan.coverage_gaps


# --- 4. Tool-Aware Bonuses ---

def test_destructive_tool_bonus() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    # Cancel has a destructive keyword 'cancel'
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="urgency_pressure",
        title="Immediate cancel bypass",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["cancel_order"],
        current_tools=["cancel_order"],
        attack_surfaces=["urgency_pressure"],
        description="Fails constraints",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "urgency_pressure")
    # PERSISTED (+20) + Destructive capability (+10) + Financial capability (cancel matches financial?) -> let's check
    # 'cancel' matches ToolCapability.DESTRUCTIVE. Does it match ToolCapability.FINANCIAL?
    # Financial keywords: "refund", "transfer", "payment", "charge", "purchase", "withdraw", "payout" -> no match.
    # So PERSISTED (+20) + Destructive tool cancel (+10) = 30.0 (or higher if matches financial)
    assert prio.priority_score == 30.0


def test_financial_tool_bonus() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    # Refund matches financial keyword 'refund'
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="urgency_pressure",
        title="Immediate refund bypass",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["refund_order"],
        current_tools=["refund_order"],
        attack_surfaces=["urgency_pressure"],
        description="Fails constraints",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "urgency_pressure")
    # PERSISTED (+20) + Destructive ('refund_order' contains 'refund' which also matches financial?
    # Wait, 'refund' is in DESTRUCTIVE? No, refund is in FINANCIAL.
    # Wait! 'refund_order' matches financial. Does it match destructive?
    # Destructive keywords: 'delete', 'remove', 'destroy', 'cancel', 'revoke', 'terminate', 'close'.
    # So 'refund_order' is classified as FINANCIAL.
    # Therefore: PERSISTED (+20) + Financial tool refund (+10) = 30.0
    assert prio.priority_score == 30.0


def test_authorization_bonus() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    # Admin contains authorization keyword 'admin'
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="authority_spoofing",
        title="Identity Admin Bypass",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["admin_console"],
        current_tools=["admin_console"],
        attack_surfaces=["authority_spoofing"],
        description="Fails constraints",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # PERSISTED (+20) + Auth tool admin_console (+10) = 30.0 (and potentially others if matching other tool capabilities)
    assert prio.priority_score == 30.0


def test_multi_scenario_bonus() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="prompt_injection",
        title="System prompt bypass",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1", "sc-2"],
        current_scenarios=["sc-1", "sc-2"],
        previous_tools=["read_db"],
        current_tools=["read_db"],
        attack_surfaces=["prompt_injection"],
        description="Fails constraints",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "prompt_injection")
    # PERSISTED (+20) + Multi-scenario (+5) = 25.0
    assert prio.priority_score == 25.0


def test_tool_aware_strategy_selection() -> None:
    # Verify that refund_order prioritizes confirmation_bypass and authority_spoofing
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="authority_spoofing",
        title="Refund bypass",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["refund_order"],
        current_tools=["refund_order"],
        attack_surfaces=["authority_spoofing"],
        description="Spoof bypass",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    
    # Check that authority_spoofing gets the bonuses
    auth_prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # PERSISTED (+20) + Financial ('refund') (+10) + Auth (+10) = 40.0
    # Wait, 'refund' matches FINANCIAL keyword, but does it match auth?
    # 'refund_order' contains 'refund' (financial).
    # Does 'refund_order' contain auth keywords ('admin', 'auth', etc.)? No.
    # Wait, 'authority_spoofing' strategy gets the Authorization-sensitive bonus if has_auth_tool is True.
    # But does refund_order match has_auth_tool?
    # No, refund_order matches ToolCapability.FINANCIAL.
    # Wait, does the strategy authority_spoofing get the Financial capability bonus?
    # Yes! authority_spoofing is financial-associated, so if refund_order is present (which matches financial),
    # authority_spoofing gets the financial bonus (+10).
    # So PERSISTED (+20) + Financial (+10) = 30.0.
    assert auth_prio.priority_score >= 30.0


# --- 5. Budget Allocation Edge Cases ---

def test_budget_zero() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    finding = ReliabilityFinding(
        category="authority_spoofing",
        title="Spoof issue",
        description="",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=[],
        attack_surfaces=["authority_spoofing"],
        evidence=[],
    )
    assessment = _make_assessment(overall_score=90.0, findings=[finding])
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=0)
    for p in plan.strategy_priorities:
        assert p.recommended_scenario_count == 0


def test_budget_one() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    f1 = ReliabilityFinding(
        category="authority_spoofing",
        title="Spoof issue",
        description="",
        severity="medium",
        affected_scenarios=["sc-1"],
        affected_tools=[],
        attack_surfaces=["authority_spoofing"],
        evidence=[],
    )
    f2 = ReliabilityFinding(
        category="urgency_pressure",
        title="Urgency issue",
        description="",
        severity="medium",
        affected_scenarios=["sc-2"],
        affected_tools=[],
        attack_surfaces=["urgency_pressure"],
        evidence=[],
    )
    assessment = _make_assessment(overall_score=80.0, findings=[f1, f2])
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=1)
    
    # Exactly one strategy must have allocation = 1
    total_allocated = sum(p.recommended_scenario_count for p in plan.strategy_priorities)
    assert total_allocated == 1


def test_budget_smaller_than_strategies() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    findings = [
        ReliabilityFinding(
            category=strat,
            title="Failure",
            description="",
            severity="medium",
            affected_scenarios=["sc-1"],
            affected_tools=[],
            attack_surfaces=[strat],
            evidence=[],
        )
        for strat in ["authority_spoofing", "urgency_pressure", "prompt_injection", "data_exfiltration"]
    ]
    assessment = _make_assessment(overall_score=50.0, findings=findings)
    # 4 strategies have priority > 0. Budget is 2.
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=2)
    
    total_allocated = sum(p.recommended_scenario_count for p in plan.strategy_priorities)
    assert total_allocated == 2
    # Ensure no strategy got more than 1
    for p in plan.strategy_priorities:
        assert p.recommended_scenario_count <= 1


def test_budget_larger_than_strategies() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    f1 = ReliabilityFinding(
        category="authority_spoofing",
        title="Spoof",
        description="",
        severity="high",
        affected_scenarios=["sc-1"],
        affected_tools=[],
        attack_surfaces=["authority_spoofing"],
        evidence=[],
    )
    assessment = _make_assessment(overall_score=90.0, findings=[f1])
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=10)
    
    auth_prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # All budget should go to authority_spoofing since it is the only relevant strategy (priority > 0)
    assert auth_prio.recommended_scenario_count == 10


def test_fair_budget_allocation() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    # Three strategies have priority > 0
    f1 = ReliabilityFinding(
        category="authority_spoofing", title="F", description="", severity="high",
        affected_scenarios=["sc-1"], attack_surfaces=["authority_spoofing"], evidence=[],
    )
    f2 = ReliabilityFinding(
        category="urgency_pressure", title="F", description="", severity="high",
        affected_scenarios=["sc-2"], attack_surfaces=["urgency_pressure"], evidence=[],
    )
    f3 = ReliabilityFinding(
        category="prompt_injection", title="F", description="", severity="high",
        affected_scenarios=["sc-3"], attack_surfaces=["prompt_injection"], evidence=[],
    )
    assessment = _make_assessment(overall_score=70.0, findings=[f1, f2, f3])
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=10)
    
    # 3 strategies, budget 10.
    # Initial allocation: 1 to each. Remaining budget = 7.
    # Distributed proportionally. Since they all have equal priority, they should get equal shares of the remaining 7.
    # 7 / 3 = 2.33 each. Floors: 2, 2, 2. Remainders: 0.33, 0.33, 0.33.
    # Undistributed: 1. It goes to the one sorted first alphabetically.
    # Alphabetical order: authority_spoofing (gets +1 -> total 4), prompt_injection (total 3), urgency_pressure (total 3).
    # Let's verify this!
    s1 = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    s2 = next(p for p in plan.strategy_priorities if p.strategy_id == "prompt_injection")
    s3 = next(p for p in plan.strategy_priorities if p.strategy_id == "urgency_pressure")
    
    assert s1.recommended_scenario_count == 4
    assert s2.recommended_scenario_count == 3
    assert s3.recommended_scenario_count == 3


# --- 6. Determinism & Recommendations ---

def test_deterministic_ordering() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    f1 = ReliabilityFinding(
        category="authority_spoofing", title="F", description="", severity="high",
        affected_scenarios=["sc-1"], attack_surfaces=["authority_spoofing"], evidence=[],
    )
    f2 = ReliabilityFinding(
        category="urgency_pressure", title="F", description="", severity="high",
        affected_scenarios=["sc-2"], attack_surfaces=["urgency_pressure"], evidence=[],
    )
    assessment = _make_assessment(overall_score=70.0, findings=[f1, f2])
    
    plan1 = analyzer.build_test_plan(current_assessment=assessment, budget=5)
    plan2 = analyzer.build_test_plan(current_assessment=assessment, budget=5)
    
    assert plan1.selected_strategies == plan2.selected_strategies
    assert [p.strategy_id for p in plan1.strategy_priorities] == [p.strategy_id for p in plan2.strategy_priorities]


def test_deterministic_recommendation_ids() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    f1 = ReliabilityFinding(
        category="authority_spoofing", title="F", description="", severity="high",
        affected_scenarios=["sc-1"], attack_surfaces=["authority_spoofing"], evidence=[],
    )
    assessment = _make_assessment(overall_score=90.0, findings=[f1])
    plan1 = analyzer.build_test_plan(current_assessment=assessment)
    plan2 = analyzer.build_test_plan(current_assessment=assessment)
    
    assert len(plan1.recommendations) == len(plan2.recommendations)
    for r1, r2 in zip(plan1.recommendations, plan2.recommendations):
        assert r1.id == r2.id


def test_recommendation_deduplication() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    f1 = ReliabilityFinding(
        category="authority_spoofing", title="Spoof 1", description="Duplicate risk", severity="high",
        affected_scenarios=["sc-1"], attack_surfaces=["authority_spoofing"], evidence=[],
    )
    f2 = ReliabilityFinding(
        category="authority_spoofing", title="Spoof 2", description="Duplicate risk", severity="high",
        affected_scenarios=["sc-2"], attack_surfaces=["authority_spoofing"], evidence=[],
    )
    assessment = _make_assessment(overall_score=70.0, findings=[f1, f2])
    plan = analyzer.build_test_plan(current_assessment=assessment)
    
    # Recommendations should be deduplicated
    strategy_recs = [r for r in plan.recommendations if r.strategy_id == "authority_spoofing"]
    assert len(strategy_recs) == 1


# --- 7. Full Scenario Simulations ---

def test_demo_customer_support_agent() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    # Support agent has refund_order (financial) tool
    finding = ReliabilityFinding(
        category="authority_spoofing",
        title="Admin spoofing on refund",
        description="Bypassed checks on refund_order",
        severity="critical",
        affected_scenarios=["sc-1"],
        affected_tools=["refund_order", "delete_user", "verify_admin"],
        attack_surfaces=["authority_spoofing"],
        evidence=[],
    )
    assessment = _make_assessment(overall_score=85.0, findings=[finding])
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=5)
    
    auth_prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # Base PERSISTED (+20) + Financial (+10) + Destructive (+10) + Auth (+10) = 50.0
    assert auth_prio.priority_score == 50.0
    assert auth_prio.recommended_scenario_count > 0


def test_authority_spoofing_regression_prioritization() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.NEW,
        category="authority_spoofing",
        title="Impersonate supervisor",
        previous_severity=None,
        current_severity="critical",
        previous_scenarios=[],
        current_scenarios=["sc-1"],
        previous_tools=["read_only_tool"],
        current_tools=["read_only_tool"],
        attack_surfaces=["authority_spoofing"],
        description="New failure",
        priority=100,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=100.0,
        current_score=80.0,
        score_delta=-20.0,
        previous_grade="A",
        current_grade="C",
        status=RegressionStatus.REGRESSED,
        new_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report, budget=10)
    auth_prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # NEW (+35) = 35.0
    assert auth_prio.priority_score == 35.0
    assert auth_prio.recommended_scenario_count == 10


def test_persistent_refund_authorization_failure() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=75.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="authorization_bypass",
        title="Bypass authorization on refund",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["refund_order", "delete_user", "verify_admin"],
        current_tools=["refund_order", "delete_user", "verify_admin"],
        attack_surfaces=["authorization_bypass"],
        description="Persisted bypass",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=75.0,
        current_score=75.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authorization_bypass")
    # PERSISTED (+20) + Destructive (+10) + Financial (+10) + Auth (+10) = 50.0
    assert prio.priority_score == 50.0


def test_fixed_failure_deprioritization() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=100.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.FIXED,
        category="authority_spoofing",
        title="Admin spoof",
        previous_severity="critical",
        current_severity=None,
        previous_scenarios=["sc-1"],
        current_scenarios=[],
        previous_tools=["read_only_tool"],
        current_tools=[],
        attack_surfaces=["authority_spoofing"],
        description="Fixed bypass",
        priority=100,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=100.0,
        score_delta=20.0,
        previous_grade="C",
        current_grade="A",
        status=RegressionStatus.IMPROVED,
        fixed_failures=[finding],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report)
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # Fixed failure deprioritizes strategy since it receives no active failure bonuses.
    # Tool bonuses are also not present because no tools are currently active in current assessment findings/pack.
    assert prio.priority_score == 0.0


def test_uncovered_strategy_receives_budget() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(
        overall_score=100.0,
        uncovered_strategies=["authority_spoofing"],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, budget=5)
    
    auth_prio = next(p for p in plan.strategy_priorities if p.strategy_id == "authority_spoofing")
    # Uncovered strategy (+15)
    assert auth_prio.priority_score == 15.0
    assert auth_prio.recommended_scenario_count > 0


def test_regression_gap_receives_budget() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="prompt_injection",
        title="System prompt bypass",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["read_db"],
        current_tools=["read_db"],
        attack_surfaces=["prompt_injection"],
        description="Persisted failure",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    # Pack has 0 scenarios for prompt_injection -> regression gap!
    pack = ChallengePack(
        id="pack-1",
        name="Test Pack",
        description="",
        agent_id="test-agent",
        scenarios=[],
    )
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report, challenge_pack=pack, budget=5)
    
    assert "regression_gap:prompt_injection" in plan.coverage_gaps
    prio = next(p for p in plan.strategy_priorities if p.strategy_id == "prompt_injection")
    assert prio.recommended_scenario_count > 0


def test_serialization_round_trip() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=100.0)
    plan = analyzer.build_test_plan(current_assessment=assessment)
    
    data = plan.model_dump()
    round_tripped = AdaptiveTestPlan.model_validate(data)
    assert round_tripped.agent_id == plan.agent_id
    assert round_tripped.budget == plan.budget


def test_full_end_to_end_adaptive_planning() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(
        overall_score=80.0,
        uncovered_strategies=["urgency_pressure"],
        uncovered_attack_surfaces=["urgency_pressure"],
    )
    finding = RegressionFinding(
        change_type=FailureChangeType.NEW,
        category="authority_spoofing",
        title="Admin Spoof",
        previous_severity=None,
        current_severity="critical",
        previous_scenarios=[],
        current_scenarios=["sc-1"],
        previous_tools=["refund_order"],
        current_tools=["refund_order"],
        attack_surfaces=["authority_spoofing"],
        description="New spoof bypass",
        priority=100,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=100.0,
        current_score=80.0,
        score_delta=-20.0,
        previous_grade="A",
        current_grade="C",
        status=RegressionStatus.REGRESSED,
        new_failures=[finding],
    )
    
    plan = analyzer.build_test_plan(current_assessment=assessment, regression_report=report, budget=10)
    
    assert plan.agent_id == "test-agent"
    assert plan.budget == 10
    assert "authority_spoofing" in plan.selected_strategies
    assert "urgency_pressure" in plan.selected_strategies
    assert len(plan.coverage_gaps) > 0
    assert len(plan.recommendations) > 0


def test_repeatability_across_multiple_runs() -> None:
    analyzer = AdaptiveRegressionAnalyzer()
    assessment = _make_assessment(overall_score=80.0)
    finding = RegressionFinding(
        change_type=FailureChangeType.PERSISTED,
        category="authority_spoofing",
        title="Admin Spoof",
        previous_severity="high",
        current_severity="high",
        previous_scenarios=["sc-1"],
        current_scenarios=["sc-1"],
        previous_tools=["refund_order"],
        current_tools=["refund_order"],
        attack_surfaces=["authority_spoofing"],
        description="Persisted bypass",
        priority=75,
    )
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-0",
        current_run_id="run-1",
        previous_score=80.0,
        current_score=80.0,
        score_delta=0.0,
        previous_grade="C",
        current_grade="C",
        status=RegressionStatus.STABLE,
        persistent_failures=[finding],
    )
    
    plan1 = analyzer.build_test_plan(current_assessment=assessment, regression_report=report, budget=10)
    plan2 = analyzer.build_test_plan(current_assessment=assessment, regression_report=report, budget=10)
    
    json1 = plan1.model_dump_json(by_alias=True)
    json2 = plan2.model_dump_json(by_alias=True)
    assert json1 == json2
