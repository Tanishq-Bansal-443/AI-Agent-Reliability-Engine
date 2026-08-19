"""
Focused offline tests for Phase 5C: ReliabilityClosedLoop orchestrator.

All tests are fully offline — no LLM calls, no sandbox execution, no I/O.
"""

from __future__ import annotations

import json
import pytest

from packages.core.models.agent import Agent, RiskProfile, Tool, AttackSurfaceEvidence, Capability, RiskIndicator
from packages.core.models.scenario import (
    ChallengePack,
    Scenario,
    ScenarioCategory,
    AttackStrategyType,
    ExpectedBehavior,
    RiskLevel,
)
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
    AdaptiveTestPlan,
    AdaptivePriority,
    AdaptiveScenarioAllocation,
    AdaptivePackMetadata,
)
from packages.reliability.closed_loop import ReliabilityClosedLoop
from packages.regression.analyzer import RegressionAnalyzer
from packages.regression.adaptive import AdaptiveRegressionAnalyzer
from packages.scenario_engine.builder import AdaptiveChallengePackBuilder
from agents.demo_customer_support.adapter import DemoAgentAdapter


# --- Helpers ---

def _make_score(
    agent_id: str = "test-agent",
    version: str = "1.0.0",
    overall_score: float = 90.0,
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
    overall_score: float = 90.0,
    findings=None,
    covered_strategies=None,
    uncovered_strategies=None,
    covered_attack_surfaces=None,
    uncovered_attack_surfaces=None,
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


def _make_regression_finding(
    change_type: FailureChangeType = FailureChangeType.NEW,
    category: str = "SAFETY_VIOLATION",
    title: str = "Auth bypass detected",
    current_severity: str = "high",
    attack_surfaces=None,
) -> RegressionFinding:
    return RegressionFinding(
        change_type=change_type,
        category=category,
        title=title,
        previous_severity=None,
        current_severity=current_severity,
        description="A regression finding for testing.",
        attack_surfaces=attack_surfaces or ["authority_spoofing"],
        current_tools=["refund_order"],
        previous_tools=[],
        current_scenarios=["sc-1"],
        previous_scenarios=[],
    )


def _make_regression_report(
    agent_id: str = "test-agent",
    new_failures=None,
    persistent_failures=None,
    status: RegressionStatus = RegressionStatus.REGRESSED,
) -> RegressionReport:
    return RegressionReport(
        agent_id=agent_id,
        agent_version="1.0.0",
        previous_run_id="run-prev",
        current_run_id="run-curr",
        previous_score=90.0,
        current_score=70.0,
        score_delta=-20.0,
        previous_grade="A",
        current_grade="C",
        status=status,
        new_failures=new_failures or [],
        persistent_failures=persistent_failures or [],
        fixed_failures=[],
        severity_changes=[],
        recommendations=["Fix authority spoofing."],
        metadata={},
    )


def _make_agent(agent_id: str = "test-agent") -> Agent:
    return Agent(
        id=agent_id,
        name="Test Agent",
        system_prompt="You are a helpful assistant.",
        tools=[
            Tool(
                name="refund_order",
                description="Refund an order. Sensitive and destructive.",
                parameters=[
                    {"name": "order_id", "type": "string", "description": "Order ID", "required": True}
                ],
                destructive=True,
                sensitive=True,
            ),
            Tool(
                name="get_order_status",
                description="Get status of an order.",
                parameters=[
                    {"name": "order_id", "type": "string", "description": "Order ID", "required": True}
                ],
                destructive=False,
                sensitive=False,
            ),
        ],
        version="1.0.0",
    )


def _make_risk_profile(agent_id: str = "test-agent") -> RiskProfile:
    return RiskProfile(
        agent_id=agent_id,
        destructive_tools=["refund_order"],
        sensitive_tools=["refund_order"],
        capabilities=[
            Capability(name="refund", description="Financial refunds", related_tools=["refund_order"])
        ],
        attack_surfaces=[
            AttackSurfaceEvidence(attack_surface="authority_spoofing", reason="Matches admin bypass"),
            AttackSurfaceEvidence(attack_surface="urgency_pressure", reason="Matches immediate request"),
        ],
        risk_indicators=[
            RiskIndicator(
                name="financial_tools_present",
                severity="high",
                description="Financial tools present",
                evidence="refund_order",
            )
        ],
    )


# --- Tests ---

# 1. Closed-loop construction defaults
def test_closed_loop_construction_defaults() -> None:
    loop = ReliabilityClosedLoop()
    assert isinstance(loop.regression_analyzer, RegressionAnalyzer)
    assert isinstance(loop.adaptive_analyzer, AdaptiveRegressionAnalyzer)
    assert isinstance(loop.adaptive_pack_builder, AdaptiveChallengePackBuilder)


# 2. Closed-loop construction with custom components
def test_closed_loop_construction_custom() -> None:
    ra = RegressionAnalyzer()
    aa = AdaptiveRegressionAnalyzer()
    ab = AdaptiveChallengePackBuilder()
    loop = ReliabilityClosedLoop(regression_analyzer=ra, adaptive_analyzer=aa, adaptive_pack_builder=ab)
    assert loop.regression_analyzer is ra
    assert loop.adaptive_analyzer is aa
    assert loop.adaptive_pack_builder is ab


# 3. Planning with no previous regression report produces valid output
@pytest.mark.asyncio
async def test_planning_without_regression_report() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        budget=5,
    )

    assert isinstance(plan, AdaptiveTestPlan)
    assert isinstance(pack, ChallengePack)
    assert plan.agent_id == "test-agent"
    assert pack.agent_id == "test-agent"
    assert plan.budget == 5


# 4. Planning with existing regression report
@pytest.mark.asyncio
async def test_planning_with_regression_report() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()
    report = _make_regression_report(new_failures=[_make_regression_finding()])

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        regression_report=report,
        budget=8,
    )

    assert isinstance(plan, AdaptiveTestPlan)
    assert isinstance(pack, ChallengePack)
    assert plan.budget == 8
    assert plan.prior_run_id == "run-prev"


# 5. Adaptive plan is generated from assessment
@pytest.mark.asyncio
async def test_adaptive_plan_generated() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()

    loop = ReliabilityClosedLoop()
    plan, _ = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        budget=10,
    )

    assert len(plan.strategy_priorities) > 0
    assert all(isinstance(p, AdaptivePriority) for p in plan.strategy_priorities)


# 6. Adaptive pack is generated and non-empty for high-priority agents
@pytest.mark.asyncio
async def test_adaptive_pack_generated_nonempty() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    finding = ReliabilityFinding(
        category="authority_spoofing",
        title="Authority spoofing detected",
        description="Agent failed to reject spoofed admin.",
        severity="high",
        affected_tools=["refund_order"],
        attack_surfaces=["authority_spoofing"],
        affected_scenarios=["sc-1"],
    )
    assessment = _make_assessment(findings=[finding])

    loop = ReliabilityClosedLoop()
    _, pack = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        budget=5,
    )

    assert len(pack.scenarios) > 0


# 7. Regression-to-adaptive priority propagation
@pytest.mark.asyncio
async def test_regression_to_priority_propagation() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()

    new_failure = _make_regression_finding(
        change_type=FailureChangeType.NEW,
        attack_surfaces=["authority_spoofing"],
    )
    report = _make_regression_report(new_failures=[new_failure])

    loop = ReliabilityClosedLoop()
    plan, _ = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        regression_report=report,
        budget=10,
    )

    prio_map = {p.strategy_id: p.priority_score for p in plan.strategy_priorities}
    assert "authority_spoofing" in prio_map
    assert prio_map["authority_spoofing"] >= 35.0


# 8. Adaptive priority drives scenario allocation
@pytest.mark.asyncio
async def test_priority_drives_allocation() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()
    new_failure = _make_regression_finding(
        change_type=FailureChangeType.NEW,
        attack_surfaces=["authority_spoofing"],
    )
    report = _make_regression_report(new_failures=[new_failure])

    loop = ReliabilityClosedLoop()
    plan, _ = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        regression_report=report,
        budget=10,
    )

    alloc_map = {p.strategy_id: p.recommended_scenario_count for p in plan.strategy_priorities}
    assert alloc_map.get("authority_spoofing", 0) > 0


# 9. Coverage gap propagation
@pytest.mark.asyncio
async def test_coverage_gap_propagation() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment(
        uncovered_strategies=["prompt_injection"],
        uncovered_attack_surfaces=["authorization_bypass"],
    )

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        budget=10,
    )

    assert "strategy_gap:prompt_injection" in plan.coverage_gaps
    assert "attack_surface_gap:authorization_bypass" in plan.coverage_gaps
    assert "strategy_gap:prompt_injection" in pack.metadata["adaptive"]["coverage_gaps"]


# 10. Provenance fields preserved end-to-end
@pytest.mark.asyncio
async def test_provenance_preserved_end_to_end() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment(run_id="run-42")
    report = _make_regression_report()

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        regression_report=report,
        budget=5,
    )

    assert plan.source_run_id == "run-42"
    assert plan.prior_run_id == "run-prev"
    adaptive_meta = pack.metadata.get("adaptive", {})
    assert adaptive_meta.get("source_run_id") == "run-42"
    assert adaptive_meta.get("prior_run_id") == "run-prev"
    assert "adaptive_plan_hash" in adaptive_meta


# 11. Budget propagation
@pytest.mark.asyncio
async def test_budget_propagation() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=risk_profile,
        current_assessment=assessment,
        budget=3,
    )

    assert plan.budget == 3
    assert len(pack.scenarios) <= 3


# 12. Demo customer-support end-to-end planning
@pytest.mark.asyncio
async def test_demo_customer_support_end_to_end() -> None:
    adapter = DemoAgentAdapter()
    agent = adapter.get_agent()
    profile = await adapter._profiler.profile(agent)

    assessment = _make_assessment(agent_id=agent.id, agent_version=agent.version or "1.0.0")

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent,
        risk_profile=profile,
        current_assessment=assessment,
        budget=5,
    )

    assert plan.agent_id == agent.id
    assert pack.agent_id == agent.id
    assert isinstance(plan, AdaptiveTestPlan)
    assert isinstance(pack, ChallengePack)


# 13. Deterministic repeatability
@pytest.mark.asyncio
async def test_deterministic_repeatability() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()

    loop = ReliabilityClosedLoop()
    plan1, pack1 = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment, budget=5
    )
    plan2, pack2 = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment, budget=5
    )

    assert plan1.model_dump() == plan2.model_dump()
    assert pack1.id == pack2.id
    assert len(pack1.scenarios) == len(pack2.scenarios)
    for s1, s2 in zip(pack1.scenarios, pack2.scenarios):
        assert s1.id == s2.id


# 14. No execution side effects
@pytest.mark.asyncio
async def test_no_execution_side_effects() -> None:
    """plan_next_test_pack must only return (AdaptiveTestPlan, ChallengePack) — no traces."""
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()

    loop = ReliabilityClosedLoop()
    result = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment, budget=5
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    adaptive_plan, challenge_pack = result
    assert isinstance(adaptive_plan, AdaptiveTestPlan)
    assert isinstance(challenge_pack, ChallengePack)


# 15. Invalid strategy isolation
@pytest.mark.asyncio
async def test_invalid_strategy_isolation() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    finding = ReliabilityFinding(
        category="completely_unknown_strategy_xyz_123",
        title="Unknown strategy finding",
        description="Hypothetical finding on an unregistered strategy.",
        severity="medium",
        affected_tools=[],
        attack_surfaces=["completely_unknown_strategy_xyz_123"],
        affected_scenarios=[],
    )
    assessment = _make_assessment(findings=[finding])

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment, budget=5
    )

    assert isinstance(plan, AdaptiveTestPlan)
    assert isinstance(pack, ChallengePack)


# 16. Full closed-loop artifact serialization
@pytest.mark.asyncio
async def test_full_artifact_serialization() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment = _make_assessment()

    loop = ReliabilityClosedLoop()
    plan, pack = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment, budget=5
    )

    plan_json = plan.model_dump_json()
    pack_json = pack.model_dump_json()

    assert isinstance(plan_json, str)
    assert isinstance(pack_json, str)

    plan_reloaded = AdaptiveTestPlan.model_validate_json(plan_json)
    pack_reloaded = ChallengePack.model_validate_json(pack_json)

    assert plan_reloaded.agent_id == plan.agent_id
    assert pack_reloaded.id == pack.id


# 17. Persistent failures boost priority relative to no-failure baseline
@pytest.mark.asyncio
async def test_persistent_failures_boost_priority() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    assessment_no_failures = _make_assessment()
    assessment_with_failures = _make_assessment(
        findings=[
            ReliabilityFinding(
                category="authority_spoofing",
                title="Persistent spoofing failure",
                description="Agent failed to reject spoofed admin repeatedly.",
                severity="high",
                affected_tools=["refund_order"],
                attack_surfaces=["authority_spoofing"],
                affected_scenarios=["sc-1", "sc-2"],
            )
        ]
    )

    loop = ReliabilityClosedLoop()
    plan_no_failures, _ = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment_no_failures, budget=10
    )
    plan_with_failures, _ = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment_with_failures, budget=10
    )

    score_no_fail = {p.strategy_id: p.priority_score for p in plan_no_failures.strategy_priorities}.get(
        "authority_spoofing", 0.0
    )
    score_with_fail = {p.strategy_id: p.priority_score for p in plan_with_failures.strategy_priorities}.get(
        "authority_spoofing", 0.0
    )

    assert score_with_fail > score_no_fail


# 18. Recommendations are propagated into plan
@pytest.mark.asyncio
async def test_recommendations_propagated_in_plan() -> None:
    agent = _make_agent()
    risk_profile = _make_risk_profile()
    finding = ReliabilityFinding(
        category="authority_spoofing",
        title="Spoofing detected",
        description="High priority.",
        severity="critical",
        affected_tools=["refund_order"],
        attack_surfaces=["authority_spoofing"],
        affected_scenarios=["sc-1"],
    )
    assessment = _make_assessment(findings=[finding])

    loop = ReliabilityClosedLoop()
    plan, _ = await loop.plan_next_test_pack(
        agent=agent, risk_profile=risk_profile, current_assessment=assessment, budget=10
    )

    assert len(plan.recommendations) > 0
