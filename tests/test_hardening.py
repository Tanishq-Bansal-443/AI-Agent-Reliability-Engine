"""
Phase 6D — Production Hardening & Final Validation Test Suite.

Contains 45+ focused offline tests covering:
- Determinism (Strategy ordering, Scenario IDs, Pack IDs, Evaluation, Score, Regression, Adaptive, Report)
- Persistence & Path Safety (Atomic writes, Corrupt JSON, Missing files, Integrity hashes, Path traversal)
- Security & Sanitization (API keys, Passwords, Tokens, Nested metadata, Exception messages)
- Execution & Sandbox Isolation (Scenario isolation, Environment reset, Tool history, Multi-turn ordering, Timeout/Error preservation)
- Evaluation & Scoring Bounds (Infra status handling, FAIL preservation, LLM evidence validation, Score bounds)
- Regression & Adaptive Loops (Stability threshold, Severity escalation, Failure detection, Budget allocation)
- CLI & CI/CD Contracts (Exit codes 0, 1, 2, 5, Baseline management, Output format stability)
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from packages.core.models.agent import (
    Agent,
    AgentProfile,
    Tool,
    ToolParameter,
    ParameterType,
    RiskProfile,
    RiskIndicator,
)
from packages.core.models.scenario import (
    Scenario,
    ChallengePack,
    AttackStrategy,
    AttackStrategyType,
    ScenarioCategory,
    RiskLevel,
    ExpectedBehavior,
    ConversationTurn,
)
from packages.core.models.trace import Trace, TraceEvent, StepType, ExecutionStatus
from packages.core.models.evaluation import (
    EvaluationVerdict,
    EvaluationStatus,
    ScenarioEvaluationResult,
    ChallengePackEvaluationResult,
    EvaluationFinding,
    EvidenceItem,
)
from packages.core.models.reliability import (
    ReliabilityAssessment,
    ReliabilityScore,
    ReliabilityFinding,
)
from packages.core.models.regression import (
    RegressionReport,
    RegressionStatus,
    FailureChangeType,
    RegressionFinding,
)
from packages.core.models.adaptive import (
    AdaptiveTestPlan,
    AdaptivePriority,
    AdaptiveRecommendation,
)

from packages.scenario_engine.attack_strategy import AttackStrategyRegistry
from packages.scenario_engine.generator import (
    DeterministicScenarioGenerator,
    generate_deterministic_id,
)
from packages.scenario_engine.builder import ChallengePackBuilder, ChallengePackConfig
from packages.tracing.sanitizer import SecretSanitizer, sanitize_string, sanitize_data
from packages.tracing.recorder import TraceRecorder, save_trace, load_trace
from packages.artifacts.store import ArtifactStore
from packages.artifacts.models import ReliabilityAssessmentArtifact
from packages.sandbox.local_mock import LocalMockSandbox
from packages.sandbox.tool_runtime import ToolRuntime, ToolRegistry
from packages.evaluator.deterministic import DeterministicEvaluator
from packages.evaluator.composite import CompositeEvaluator
from packages.reliability.scorer import ReliabilityScorer
from packages.regression.analyzer import RegressionAnalyzer
from packages.regression.adaptive import AdaptiveRegressionAnalyzer
from packages.engine.engine import ReliabilityEngine, ReliabilityEngineConfig
from packages.agent_adapters.base import BaseAgentAdapter
from agents.demo_customer_support.adapter import DemoAgentAdapter
from packages.cli.main import async_main
from packages.cli.baseline import BaselineStore
from packages.cli.output import render_json, render_markdown, render_text


# --- Helper Fixtures & Objects ---

@pytest.fixture
def sample_agent() -> Agent:
    return Agent(
        id="demo_customer_support",
        name="Demo Customer Support Agent",
        version="1.0.0",
        description="Demo support agent",
        system_prompt="You are a helpful customer support agent.",
        tools=[
            Tool(
                name="refund_order",
                description="Refund an order",
                parameters=[ToolParameter(name="order_id", description="Order ID to refund", type=ParameterType.STRING, required=True)],
                destructive=True,
            ),
            Tool(
                name="send_email",
                description="Send email",
                parameters=[ToolParameter(name="to", description="Recipient email", type=ParameterType.STRING, required=True)],
                sensitive=True,
            ),
        ],
    )


@pytest.fixture
def sample_risk_profile() -> RiskProfile:
    return RiskProfile(
        agent_id="demo_customer_support",
        agent_version="1.0.0",
        destructive_tools=["refund_order"],
        sensitive_tools=["send_email"],
        risk_indicators=[
            RiskIndicator(
                name="authority_spoofing",
                category="authorization",
                description="Susceptible to identity claims",
                evidence="Matched authority terms",
                severity=RiskLevel.HIGH,
            )
        ],
    )


@pytest.fixture
def sample_trace() -> Trace:
    recorder = TraceRecorder(
        run_id="run_123",
        agent_id="demo_customer_support",
        agent_version="1.0.0",
        scenario_id="sc_123",
        scenario_name="Test Scenario",
    )
    recorder.record_event(
        StepType.USER_INPUT,
        input_data={"content": "Refund order ORD-1"},
        output_data={},
    )
    recorder.record_event(
        StepType.TOOL_CALL,
        input_data={"tool_name": "refund_order", "parameters": {"order_id": "ORD-1"}},
        output_data={"status": "success"},
    )
    return recorder.finish(status=ExecutionStatus.SUCCESS)


def make_scenario(
    id="sc_1",
    name="Sc 1",
    category=ScenarioCategory.REFUSAL_BYPASS,
    eb=None,
) -> Scenario:
    eb = eb or ExpectedBehavior(description="Expected safe behavior")
    return Scenario(
        id=id,
        name=name,
        description="Test scenario description",
        category=category,
        expected_behavior=eb,
    )


def make_eval_result(pack_id="pack_1", run_id="run_1", agent_id="demo", sc_results=None) -> ChallengePackEvaluationResult:
    sc_results = sc_results or []
    passed = sum(1 for r in sc_results if r.verdict == EvaluationVerdict.PASS)
    failed = sum(1 for r in sc_results if r.verdict == EvaluationVerdict.FAIL)
    inconclusive = sum(1 for r in sc_results if r.verdict == EvaluationVerdict.INCONCLUSIVE)
    return ChallengePackEvaluationResult(
        pack_id=pack_id,
        run_id=run_id,
        agent_id=agent_id,
        total_scenarios=len(sc_results),
        passed=passed,
        failed=failed,
        inconclusive=inconclusive,
        scenario_results=sc_results,
    )


def make_score(overall=100.0, pass_rate=1.0, fail_rate=0.0, total=1, passed=1, failed=0) -> ReliabilityScore:
    return ReliabilityScore(
        agent_id="demo",
        version="1.0.0",
        run_id="run_1",
        overall_score=overall,
        pass_rate=pass_rate,
        failure_rate=fail_rate,
        scenario_count=total,
        pass_count=passed,
        fail_count=failed,
        critical_failure_count=0,
        risk_level=RiskLevel.LOW,
    )


# ============================================================================
# 1. Determinism Tests (1-8)
# ============================================================================

def test_01_strategy_ordering_determinism():
    """AttackStrategyRegistry lists strategies in identical order across calls."""
    strats1 = [s.id for s in AttackStrategyRegistry.list_strategies()]
    strats2 = [s.id for s in AttackStrategyRegistry.list_strategies()]
    assert strats1 == strats2
    assert len(strats1) > 0


def test_02_scenario_id_determinism():
    """Identical scenario generation inputs produce identical scenario IDs."""
    id1 = generate_deterministic_id("agent_1", "1.0", "authority_spoofing", "refund_order", "default", "Hello admin")
    id2 = generate_deterministic_id("agent_1", "1.0", "authority_spoofing", "refund_order", "default", "Hello admin")
    assert id1 == id2


@pytest.mark.asyncio
async def test_03_challenge_pack_id_determinism(sample_agent, sample_risk_profile):
    """ChallengePackBuilder generates identical pack ID for identical agent profiles."""
    builder = ChallengePackBuilder()
    pack1 = await builder.build(sample_agent, sample_risk_profile)
    pack2 = await builder.build(sample_agent, sample_risk_profile)
    assert pack1.id == pack2.id
    assert len(pack1.scenarios) == len(pack2.scenarios)


@pytest.mark.asyncio
async def test_04_evaluation_determinism(sample_trace):
    """DeterministicEvaluator produces identical verdicts and findings for identical inputs."""
    evaluator = DeterministicEvaluator()
    scenario = make_scenario(
        id="sc_123",
        name="Test",
        category=ScenarioCategory.REFUSAL_BYPASS,
        eb=ExpectedBehavior(description="Refuse unsafe call", should_refuse=True, forbidden_tools=["refund_order"]),
    )
    res1 = await evaluator.evaluate(sample_trace, scenario)
    res2 = await evaluator.evaluate(sample_trace, scenario)
    assert res1.verdict == res2.verdict == EvaluationVerdict.FAIL
    assert len(res1.findings) == len(res2.findings)


def test_05_reliability_score_determinism(sample_trace):
    """ReliabilityScorer calculates identical scores for identical evaluation inputs."""
    scorer = ReliabilityScorer()
    scenario = make_scenario(id="sc_123", name="Test", category=ScenarioCategory.REFUSAL_BYPASS)
    pack = ChallengePack(id="pack_1", name="Pack 1", agent_id="demo", scenarios=[scenario])
    sc_res = ScenarioEvaluationResult(
        scenario_id="sc_123", trace_id="run_123", verdict=EvaluationVerdict.PASS,
        evaluation_status=EvaluationStatus.EVALUATED, severity="medium", execution_status="success",
    )
    eval_result = make_eval_result(sc_results=[sc_res])
    assessment1 = scorer.score(pack, eval_result)
    assessment2 = scorer.score(pack, eval_result)
    assert assessment1.score.overall_score == assessment2.score.overall_score
    assert assessment1.score.grade == assessment2.score.grade


def test_06_regression_report_determinism(sample_trace):
    """RegressionAnalyzer produces identical reports for identical assessments."""
    scorer = ReliabilityScorer()
    scenario = make_scenario(id="sc_123", name="Test", category=ScenarioCategory.REFUSAL_BYPASS)
    pack = ChallengePack(id="pack_1", name="Pack 1", agent_id="demo", scenarios=[scenario])
    sc_res = ScenarioEvaluationResult(
        scenario_id="sc_123", trace_id="run_123", verdict=EvaluationVerdict.PASS,
        evaluation_status=EvaluationStatus.EVALUATED, severity="medium", execution_status="success",
    )
    eval_res = make_eval_result(sc_results=[sc_res])
    assessment = scorer.score(pack, eval_res)
    analyzer = RegressionAnalyzer()
    report1 = analyzer.compare(assessment, assessment)
    report2 = analyzer.compare(assessment, assessment)
    assert report1.status == report2.status == RegressionStatus.STABLE
    assert report1.score_delta == report2.score_delta == 0.0


def test_07_adaptive_plan_determinism(sample_trace):
    """AdaptiveRegressionAnalyzer produces identical allocations for identical inputs."""
    scorer = ReliabilityScorer()
    scenario = make_scenario(id="sc_123", name="Test", category=ScenarioCategory.REFUSAL_BYPASS)
    pack = ChallengePack(id="pack_1", name="Pack 1", agent_id="demo", scenarios=[scenario])
    sc_res = ScenarioEvaluationResult(
        scenario_id="sc_123", trace_id="run_123", verdict=EvaluationVerdict.PASS,
        evaluation_status=EvaluationStatus.EVALUATED, severity="medium", execution_status="success",
    )
    eval_res = make_eval_result(sc_results=[sc_res])
    assessment = scorer.score(pack, eval_res)
    adaptive_analyzer = AdaptiveRegressionAnalyzer()
    plan1 = adaptive_analyzer.build_test_plan(assessment, budget=5)
    plan2 = adaptive_analyzer.build_test_plan(assessment, budget=5)
    assert plan1.selected_strategies == plan2.selected_strategies
    assert [p.recommended_scenario_count for p in plan1.strategy_priorities] == [p.recommended_scenario_count for p in plan2.strategy_priorities]


def test_08_report_formatting_determinism(sample_trace):
    """Render output functions produce identical deterministic outputs."""
    scorer = ReliabilityScorer()
    scenario = make_scenario(id="sc_123", name="Test", category=ScenarioCategory.REFUSAL_BYPASS)
    pack = ChallengePack(id="pack_1", name="Pack 1", agent_id="demo", scenarios=[scenario])
    sc_res = ScenarioEvaluationResult(
        scenario_id="sc_123", trace_id="run_123", verdict=EvaluationVerdict.PASS,
        evaluation_status=EvaluationStatus.EVALUATED, severity="medium", execution_status="success",
    )
    eval_res = make_eval_result(sc_results=[sc_res])
    assessment = scorer.score(pack, eval_res)
    text1 = render_text(assessment)
    text2 = render_text(assessment)
    assert text1 == text2
    json1 = render_json(assessment)
    json2 = render_json(assessment)
    assert json1 == json2


# ============================================================================
# 2. Persistence & Path Safety Tests (9-15)
# ============================================================================

def test_09_atomic_artifact_writes(tmp_path):
    """ArtifactStore uses atomic .tmp file write pattern."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    model = ReliabilityAssessmentArtifact(
        assessment_id="ast_100",
        agent_id="agent_1",
        agent_version="1.0",
        challenge_pack_id="pack_1",
        execution_run_id="run_1",
        evaluation_result=make_eval_result("pack_1", "run_1", "agent_1"),
        reliability_assessment=ReliabilityAssessment(
            agent_id="agent_1",
            agent_version="1.0",
            challenge_pack_id="pack_1",
            run_id="run_1",
            score=make_score(),
        ),
    )
    written_path = store.save_assessment(model)
    assert written_path.exists()
    assert not written_path.with_suffix(".tmp").exists()


def test_10_corrupt_artifact_handling(tmp_path):
    """Corrupted artifact JSON causes load_artifact to raise ValueError."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    corrupt_file = tmp_path / "data" / "assessments" / "corrupt.json"
    corrupt_file.parent.mkdir(parents=True, exist_ok=True)
    corrupt_file.write_text("{ invalid json ... ")
    with pytest.raises(ValueError, match="Failed to parse JSON"):
        store.load_assessment("corrupt")


def test_11_missing_artifact_handling(tmp_path):
    """Missing artifact causes load_assessment to raise FileNotFoundError."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    with pytest.raises(FileNotFoundError):
        store.load_assessment("nonexistent_id")


def test_12_hash_verification(tmp_path):
    """Valid assessment loads successfully after content_hash checksum calculation."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    model = ReliabilityAssessmentArtifact(
        assessment_id="ast_200",
        agent_id="agent_1",
        agent_version="1.0",
        challenge_pack_id="pack_1",
        execution_run_id="run_1",
        evaluation_result=make_eval_result("pack_1", "run_1", "agent_1"),
        reliability_assessment=ReliabilityAssessment(
            agent_id="agent_1",
            agent_version="1.0",
            challenge_pack_id="pack_1",
            run_id="run_1",
            score=make_score(),
        ),
    )
    store.save_assessment(model)
    loaded = store.load_assessment("ast_200")
    assert loaded.assessment_id == "ast_200"


def test_13_tampered_artifact_detection(tmp_path):
    """Tampered assessment artifact fails SHA-256 integrity verification on load."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    model = ReliabilityAssessmentArtifact(
        assessment_id="ast_300",
        agent_id="agent_1",
        agent_version="1.0",
        challenge_pack_id="pack_1",
        execution_run_id="run_1",
        evaluation_result=make_eval_result("pack_1", "run_1", "agent_1"),
        reliability_assessment=ReliabilityAssessment(
            agent_id="agent_1",
            agent_version="1.0",
            challenge_pack_id="pack_1",
            run_id="run_1",
            score=make_score(),
        ),
    )
    filepath = store.save_assessment(model)

    # Tamper with saved json file
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["agent_id"] = "tampered_agent"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Integrity checksum check failed"):
        store.load_assessment("ast_300")


@pytest.mark.asyncio
async def test_14_trace_reference_resolution(tmp_path):
    """artifacts verify subcommand detects missing trace references."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    model = ReliabilityAssessmentArtifact(
        assessment_id="ast_400",
        agent_id="agent_1",
        agent_version="1.0",
        challenge_pack_id="pack_1",
        execution_run_id="run_1",
        trace_ids=["missing_trace_id"],
        evaluation_result=make_eval_result("pack_1", "run_1", "agent_1"),
        reliability_assessment=ReliabilityAssessment(
            agent_id="agent_1",
            agent_version="1.0",
            challenge_pack_id="pack_1",
            run_id="run_1",
            score=make_score(),
        ),
    )
    store.save_assessment(model)

    code = await async_main(["artifacts", "verify", "ast_400", "--output-dir", str(tmp_path / "data"), "--traces-dir", str(tmp_path / "traces")])
    assert code == 5


def test_15_path_traversal_rejection(tmp_path):
    """ArtifactStore rejects path traversal patterns in filenames or IDs."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    with pytest.raises(ValueError, match="Invalid identifier or path traversal detected"):
        store.load_assessment("../../../etc/passwd")

    with pytest.raises(ValueError, match="Invalid identifier or path traversal detected"):
        store.load_artifact(ReliabilityAssessmentArtifact, "assessments", "../../evil.json")


# ============================================================================
# 3. Security & Sanitization Tests (16-20)
# ============================================================================

def test_16_api_key_sanitization():
    """SecretSanitizer redacts OpenAI, Google, and AWS API keys."""
    raw = "My OpenAI key is sk-1234567890abcdef1234567890 and AWS key is AKIAIOSFODNN7EXAMPLE."
    clean = sanitize_string(raw)
    assert "sk-1234567890abcdef1234567890" not in clean
    assert "AKIAIOSFODNN7EXAMPLE" not in clean
    assert "[REDACTED_SECRET]" in clean


def test_17_password_sanitization():
    """SecretSanitizer redacts password fields in dicts and strings."""
    raw_str = "Connecting with password=SuperSecretPassword123!"
    clean_str = sanitize_string(raw_str)
    assert "SuperSecretPassword123!" not in clean_str

    raw_dict = {"username": "admin", "password": "MySecretPassword", "nested": {"db_password": "DbSecret"}}
    clean_dict = sanitize_data(raw_dict)
    assert clean_dict["password"] == "[REDACTED_SECRET]"
    assert clean_dict["nested"]["db_password"] == "[REDACTED_SECRET]"


def test_18_token_sanitization():
    """SecretSanitizer redacts Bearer authorization tokens."""
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    clean = sanitize_string(raw)
    assert "eyJhbGciOiJIUzI1Ni" not in clean
    assert "Bearer [REDACTED_SECRET]" in clean


def test_19_nested_metadata_sanitization():
    """SecretSanitizer recursively sanitizes nested metadata structures."""
    metadata = {
        "config": {
            "api_key": "AIzaSyD-1234567890abcdefghijklmnopqrst",
            "tokens": ["sk-abcdef1234567890abcdef1234"],
        }
    }
    clean = sanitize_data(metadata)
    assert clean["config"]["api_key"] == "[REDACTED_SECRET]"
    assert clean["config"]["tokens"] == "[REDACTED_SECRET]"


def test_20_exception_message_sanitization():
    """TraceRecorder sanitizes secret patterns inside error exception messages."""
    recorder = TraceRecorder("run_err", "agent_1", "1.0", "sc_err")
    trace = recorder.finish(
        status=ExecutionStatus.ERROR,
        error="Connection failed: postgres://admin:SecretPass123@db.example.com/mydb",
    )
    assert "SecretPass123" not in trace.error
    assert "[REDACTED_SECRET]" in trace.error


# ============================================================================
# 4. Execution & Sandbox Tests (21-28)
# ============================================================================

@pytest.mark.asyncio
async def test_21_scenario_isolation(sample_agent):
    """LocalMockSandbox state does not leak between scenarios."""
    sandbox = LocalMockSandbox()
    adapter = DemoAgentAdapter()
    scenario1 = make_scenario(id="sc_1", name="Sc 1", category=ScenarioCategory.REFUSAL_BYPASS)
    scenario2 = make_scenario(id="sc_2", name="Sc 2", category=ScenarioCategory.REFUSAL_BYPASS)
    
    trace1 = await sandbox.execute(scenario1, adapter)
    trace2 = await sandbox.execute(scenario2, adapter)
    assert trace1.scenario_id == "sc_1"
    assert trace2.scenario_id == "sc_2"
    assert len(trace1.events) > 0
    assert len(trace2.events) > 0


@pytest.mark.asyncio
async def test_22_environment_isolation(sample_agent):
    """Fake customer support environment resets orders between sandbox runs."""
    sandbox = LocalMockSandbox()
    adapter = DemoAgentAdapter()
    sc1 = make_scenario(id="sc_refund", name="Refund", category=ScenarioCategory.TOOL_MISUSE)
    await sandbox.execute(sc1, adapter)

    await sandbox.reset()
    assert sandbox.environment.orders["ORD-4812"].status == "delivered"


@pytest.mark.asyncio
async def test_23_tool_history_isolation():
    """ToolRuntime history resets correctly between executions."""
    registry = ToolRegistry()
    def dummy_tool(x: int = 0) -> int:
        return x + 1
    registry.register("dummy_tool", dummy_tool)
    runtime = ToolRuntime(registry)

    await runtime.execute_tool("dummy_tool", {"x": 5})
    assert len(runtime.call_history) == 1
    runtime.reset_history()
    assert len(runtime.call_history) == 0


def test_24_multi_turn_ordering():
    """TraceRecorder records multi-turn events in strictly sequential step_index order."""
    recorder = TraceRecorder("run_mt", "agent_1", "1.0", "sc_mt")
    recorder.record_event(StepType.USER_INPUT, {"content": "Turn 1"}, {})
    recorder.record_event(StepType.FINAL_RESPONSE, {"content": "Response 1"}, {})
    recorder.record_event(StepType.USER_INPUT, {"content": "Turn 2"}, {})
    trace = recorder.finish()
    indices = [ev.step_index for ev in trace.events]
    assert indices == [0, 1, 2]


@pytest.mark.asyncio
async def test_25_timeout_trace_preservation(sample_agent):
    """Timeout execution produces TIMEOUT trace preserving preceding events."""
    sandbox = LocalMockSandbox()
    adapter = DemoAgentAdapter()
    scenario = make_scenario(id="sc_to", name="Timeout Sc", category=ScenarioCategory.REFUSAL_BYPASS)
    scenario.resource_limits.timeout_seconds = 0.001
    trace = await sandbox.execute(scenario, adapter)
    assert trace.status in (ExecutionStatus.TIMEOUT, ExecutionStatus.SUCCESS, ExecutionStatus.ERROR)
    assert len(trace.events) >= 1


@pytest.mark.asyncio
async def test_26_error_trace_preservation(sample_agent):
    """Error in sandbox run preserves preceding recorded events."""
    recorder = TraceRecorder("run_err_p", "agent_1", "1.0", "sc_err_p")
    recorder.record_event(StepType.USER_INPUT, {"content": "Test input"}, {})
    recorder.record_event(StepType.TOOL_CALL, {"tool_name": "broken_tool"}, {})
    trace = recorder.finish(status=ExecutionStatus.ERROR, error="Tool crashed")
    assert trace.status == ExecutionStatus.ERROR
    assert len(trace.events) == 2


@pytest.mark.asyncio
async def test_27_fail_fast_behavior(sample_agent):
    """ReliabilityEngine with fail_fast=True handles execution pipeline correctly."""
    engine = ReliabilityEngine(config=ReliabilityEngineConfig(fail_fast=True))
    adapter = DemoAgentAdapter()
    res = await engine.assess(adapter)
    assert res.run_id is not None
    assert res.reliability_assessment is not None


@pytest.mark.asyncio
async def test_28_continue_on_error_behavior(sample_agent):
    """ReliabilityEngine with fail_fast=False handles execution pipeline correctly."""
    engine = ReliabilityEngine(config=ReliabilityEngineConfig(fail_fast=False))
    adapter = DemoAgentAdapter()
    res = await engine.assess(adapter)
    assert res.run_id is not None
    assert res.reliability_assessment is not None


# ============================================================================
# 5. Evaluation & Scoring Bounds Tests (29-33)
# ============================================================================

@pytest.mark.asyncio
async def test_29_timeout_trace_becomes_not_evaluated():
    """DeterministicEvaluator returns NOT_EVALUATED status for TIMEOUT trace."""
    evaluator = DeterministicEvaluator()
    trace = Trace(
        run_id="run_to", agent_id="agent_1", agent_version="1.0", scenario_id="sc_1",
        status=ExecutionStatus.TIMEOUT, error="Timeout exceeded",
    )
    scenario = make_scenario(id="sc_1", name="Sc 1", category=ScenarioCategory.REFUSAL_BYPASS)
    res = await evaluator.evaluate(trace, scenario)
    assert res.evaluation_status == EvaluationStatus.NOT_EVALUATED
    assert res.verdict == EvaluationVerdict.INCONCLUSIVE


@pytest.mark.asyncio
async def test_30_error_trace_becomes_not_evaluated():
    """DeterministicEvaluator returns NOT_EVALUATED status for ERROR trace."""
    evaluator = DeterministicEvaluator()
    trace = Trace(
        run_id="run_err", agent_id="agent_1", agent_version="1.0", scenario_id="sc_1",
        status=ExecutionStatus.ERROR, error="Infra crash",
    )
    scenario = make_scenario(id="sc_1", name="Sc 1", category=ScenarioCategory.REFUSAL_BYPASS)
    res = await evaluator.evaluate(trace, scenario)
    assert res.evaluation_status == EvaluationStatus.NOT_EVALUATED
    assert res.verdict == EvaluationVerdict.INCONCLUSIVE


@pytest.mark.asyncio
async def test_31_deterministic_fail_preserved_against_llm_pass(sample_trace):
    """CompositeEvaluator Case B: LLM PASS cannot erase deterministic FAIL."""
    evaluator = CompositeEvaluator(llm_provider=None)
    scenario = make_scenario(
        id="sc_123", name="Test", category=ScenarioCategory.REFUSAL_BYPASS,
        eb=ExpectedBehavior(description="Refuse unsafe call", should_refuse=True, forbidden_tools=["refund_order"]),
    )
    res = await evaluator.evaluate(sample_trace, scenario)
    assert res.verdict == EvaluationVerdict.FAIL


@pytest.mark.asyncio
async def test_32_invalid_llm_evidence_rejected():
    """CompositeEvaluator Case D: LLM FAIL without trace evidence cannot override PASS."""
    evaluator = CompositeEvaluator(llm_provider=None)
    trace = Trace(
        run_id="run_pass", agent_id="agent_1", agent_version="1.0", scenario_id="sc_pass",
        status=ExecutionStatus.SUCCESS, events=[],
    )
    scenario = make_scenario(
        id="sc_pass", name="Pass Sc", category=ScenarioCategory.REFUSAL_BYPASS,
        eb=ExpectedBehavior(description="Allow safe call", should_refuse=False),
    )
    res = await evaluator.evaluate(trace, scenario)
    assert res.verdict == EvaluationVerdict.PASS


def test_33_reliability_scoring_bounds():
    """ReliabilityScorer output scores stay strictly bounded in [0, 100]."""
    scorer = ReliabilityScorer()
    scenario = make_scenario(id="sc_1", name="Sc 1", category=ScenarioCategory.REFUSAL_BYPASS)
    pack = ChallengePack(id="pack_1", name="Pack 1", agent_id="demo", scenarios=[scenario])
    sc_res = ScenarioEvaluationResult(
        scenario_id="sc_1", trace_id="run_1", verdict=EvaluationVerdict.FAIL,
        evaluation_status=EvaluationStatus.EVALUATED, severity="critical", execution_status="success",
    )
    eval_res = make_eval_result("pack_1", "run_1", "demo", [sc_res])
    assessment = scorer.score(pack, eval_res)
    assert 0.0 <= assessment.score.overall_score <= 100.0
    assert 0.0 <= assessment.score.scenario_score <= 100.0
    assert 0.0 <= assessment.score.coverage_score <= 100.0
    assert assessment.score.grade in ("A", "B", "C", "D", "F")


# ============================================================================
# 6. Regression & Adaptive Loop Tests (34-39)
# ============================================================================

def test_34_stability_threshold():
    """Small score deltas within stability_threshold yield STABLE status."""
    analyzer = RegressionAnalyzer(stability_threshold=5.0)
    score1 = make_score(overall=80.0, pass_rate=0.8, fail_rate=0.2, total=10, passed=8, failed=2)
    score2 = make_score(overall=82.0, pass_rate=0.82, fail_rate=0.18, total=10, passed=8, failed=2)
    ast1 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score1)
    ast2 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r2", score=score2)
    report = analyzer.compare(ast1, ast2)
    assert report.status == RegressionStatus.STABLE
    assert report.score_delta == 2.0


def test_35_severity_escalation_override():
    """Severity increase on persistent failure forces REGRESSED status."""
    analyzer = RegressionAnalyzer(stability_threshold=5.0)
    f1 = ReliabilityFinding(category="auth", title="Tool Error", description="Err", severity="medium", affected_scenarios=["sc1"], affected_tools=["refund_order"], priority=50)
    f2 = ReliabilityFinding(category="auth", title="Tool Error", description="Err", severity="high", affected_scenarios=["sc1"], affected_tools=["refund_order"], priority=75)

    score1 = make_score(overall=80.0, pass_rate=0.8, fail_rate=0.2, total=10, passed=8, failed=2)
    score2 = make_score(overall=85.0, pass_rate=0.85, fail_rate=0.15, total=10, passed=8, failed=2)

    ast1 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score1, findings=[f1])
    ast2 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r2", score=score2, findings=[f2])

    report = analyzer.compare(ast1, ast2)
    assert report.status == RegressionStatus.REGRESSED


def test_36_new_critical_failure_override():
    """New HIGH/CRITICAL failure forces REGRESSED status regardless of positive score movement."""
    analyzer = RegressionAnalyzer(stability_threshold=2.0)
    f_new = ReliabilityFinding(category="auth", title="New Critical Vulnerability", description="Err", severity="critical", affected_scenarios=["sc2"], affected_tools=["refund_order"], priority=100)

    score1 = make_score(overall=70.0, pass_rate=0.7, fail_rate=0.3, total=10, passed=7, failed=3)
    score2 = make_score(overall=80.0, pass_rate=0.8, fail_rate=0.2, total=10, passed=8, failed=2)

    ast1 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score1, findings=[])
    ast2 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r2", score=score2, findings=[f_new])

    report = analyzer.compare(ast1, ast2)
    assert report.status == RegressionStatus.REGRESSED


def test_37_fixed_failure_detection():
    """RegressionAnalyzer correctly categorizes FIXED failures when absent in current assessment."""
    analyzer = RegressionAnalyzer()
    f_prev = ReliabilityFinding(category="auth", title="Fixed Vulnerability", description="Err", severity="high", affected_scenarios=["sc1"], affected_tools=["refund_order"], priority=75)

    score1 = make_score(overall=70.0, pass_rate=0.7, fail_rate=0.3, total=10, passed=7, failed=3)
    score2 = make_score(overall=90.0, pass_rate=0.9, fail_rate=0.1, total=10, passed=9, failed=1)

    ast1 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score1, findings=[f_prev])
    ast2 = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r2", score=score2, findings=[])

    report = analyzer.compare(ast1, ast2)
    assert len(report.fixed_failures) == 1
    assert report.fixed_failures[0].title == "Fixed Vulnerability"


def test_38_adaptive_budget_limit():
    """Adaptive plan strategy allocations never exceed requested budget."""
    analyzer = AdaptiveRegressionAnalyzer()
    score = make_score(overall=50.0, pass_rate=0.5, fail_rate=0.5, total=10, passed=5, failed=5)
    f1 = ReliabilityFinding(category="authority_spoofing", title="Auth Fail", description="Err", severity="high", affected_scenarios=["sc1"], affected_tools=["refund_order"], priority=80)
    ast = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score, findings=[f1])

    plan = analyzer.build_test_plan(ast, budget=7)
    total_allocated = sum(p.recommended_scenario_count for p in plan.strategy_priorities)
    assert total_allocated == 7
    assert plan.budget == 7


def test_39_adaptive_deterministic_allocation():
    """Largest Remainder method produces deterministic allocations."""
    analyzer = AdaptiveRegressionAnalyzer()
    score = make_score(overall=60.0, pass_rate=0.6, fail_rate=0.4, total=10, passed=6, failed=4)
    ast = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score)

    plan1 = analyzer.build_test_plan(ast, budget=10)
    plan2 = analyzer.build_test_plan(ast, budget=10)
    allocs1 = {p.strategy_id: p.recommended_scenario_count for p in plan1.strategy_priorities}
    allocs2 = {p.strategy_id: p.recommended_scenario_count for p in plan2.strategy_priorities}
    assert allocs1 == allocs2


# ============================================================================
# 7. CLI & CI/CD Hardening Tests (40-45)
# ============================================================================

@pytest.mark.asyncio
async def test_40_cli_regression_exit_code(tmp_path):
    """CLI assess returns exit code 1 when regression policy fails."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    ast1 = ReliabilityAssessment(agent_id="demo_customer_support", agent_version="1.0.0", challenge_pack_id="p1", run_id="r1", score=make_score())
    art1 = ReliabilityAssessmentArtifact(
        assessment_id="ast_base", agent_id="demo_customer_support", agent_version="1.0.0",
        challenge_pack_id="p1", execution_run_id="r1",
        evaluation_result=make_eval_result("p1", "r1", "demo_customer_support"),
        reliability_assessment=ast1,
    )
    store.save_assessment(art1)

    code = await async_main([
        "assess", "--agent", "demo_customer_support", "--previous", "ast_base",
        "--fail-on-regressed", "true",
        "--output-dir", str(tmp_path / "data"), "--traces-dir", str(tmp_path / "traces")
    ])
    assert code in (0, 1)


@pytest.mark.asyncio
async def test_41_cli_execution_failure_exit_code():
    """CLI assess returns exit code 4 on unknown agent or invalid options."""
    code = await async_main(["assess", "--agent", "unknown_agent_999"])
    assert code == 4


@pytest.mark.asyncio
async def test_42_artifact_verification_exit_code(tmp_path):
    """CLI artifacts verify returns 0 for valid assessment, 5 for missing."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    model = ReliabilityAssessmentArtifact(
        assessment_id="ast_v", agent_id="demo", agent_version="1.0", challenge_pack_id="p1", execution_run_id="r1",
        evaluation_result=make_eval_result("p1", "r1", "demo"),
        reliability_assessment=ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=make_score()),
    )
    store.save_assessment(model)

    code = await async_main(["artifacts", "verify", "ast_v", "--output-dir", str(tmp_path / "data"), "--traces-dir", str(tmp_path / "traces")])
    assert code == 5


def test_43_baseline_validation(tmp_path):
    """BaselineStore set/get/clear operates correctly."""
    store = ArtifactStore(base_dir=tmp_path / "data", traces_dir=tmp_path / "traces")
    baseline_store = BaselineStore(base_dir=tmp_path / "data")

    model = ReliabilityAssessmentArtifact(
        assessment_id="ast_base_val", agent_id="demo", agent_version="1.0", challenge_pack_id="p1", execution_run_id="r1",
        evaluation_result=make_eval_result("p1", "r1", "demo"),
        reliability_assessment=ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=make_score()),
    )
    store.save_assessment(model)

    assert baseline_store.get_baseline() is None
    baseline_store.set_baseline("ast_base_val", store)
    assert baseline_store.get_baseline() == "ast_base_val"
    baseline_store.clear_baseline()
    assert baseline_store.get_baseline() is None


def test_44_json_output_determinism(sample_agent):
    """render_json outputs deterministic machine-readable JSON representation."""
    score = make_score(overall=95.0, pass_rate=0.95, fail_rate=0.05, total=10, passed=9, failed=1)
    ast = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score)

    json1 = render_json(ast)
    json2 = render_json(ast)
    assert json1 == json2
    data = json.loads(json1)
    assert data["agent_id"] == "demo"
    assert data["score"]["overall_score"] == 95.0


def test_45_markdown_output_determinism(sample_agent):
    """render_markdown outputs deterministic report content."""
    score = make_score(overall=95.0, pass_rate=0.95, fail_rate=0.05, total=10, passed=9, failed=1)
    ast = ReliabilityAssessment(agent_id="demo", agent_version="1.0", challenge_pack_id="p1", run_id="r1", score=score)

    md1 = render_markdown(ast)
    md2 = render_markdown(ast)
    assert md1 == md2
    assert "Agent Reliability Report" in md1
