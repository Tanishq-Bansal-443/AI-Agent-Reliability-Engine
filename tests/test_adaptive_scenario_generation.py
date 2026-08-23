import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from packages.engine.engine import ReliabilityEngine
from packages.engine.models import ReliabilityEngineConfig
from packages.core.models.agent import Agent, RiskProfile, Capability, Tool, AgentProfile, AgentOutput
from packages.core.models.scenario import ChallengePack, Scenario, ExpectedBehavior
from packages.core.models.evaluation import ChallengePackEvaluationResult, ScenarioEvaluationResult, EvaluationVerdict, EvaluationStatus
from packages.agent_adapters.base import BaseAgentAdapter


class MockAgentAdapter(BaseAgentAdapter):
    def __init__(self, agent_id="mock_agent"):
        self._agent_id = agent_id

    def get_agent(self) -> Agent:
        return Agent(
            id=self._agent_id,
            name="Mock Agent",
            system_prompt="You are a helpful assistant. verify identity, admin",
            tools=[
                Tool(
                    name="refund_order",
                    description="refund a customer order",
                    parameters=[],
                    destructive=True,
                    sensitive=True
                )
            ]
        )

    def get_profile(self) -> AgentProfile:
        agent = self.get_agent()
        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            capabilities=[],
            tools=agent.tools,
            constraints=[],
            risk_surface=MagicMock()
        )

    async def run(self, user_message: str, scenario_id: str) -> AgentOutput:
        return AgentOutput(response="Processed successfully.")


@pytest.mark.asyncio
async def test_low_risk_assessment_stops_at_baseline():
    """Prove that a low-risk assessment can finish after baseline testing without triggering follow-ups."""
    adapter = MockAgentAdapter()
    engine = ReliabilityEngine(ReliabilityEngineConfig(persistence_enabled=False))

    # Mock evaluate_pack to return PASS for all scenarios
    async def mock_evaluate_pack(pack, scenario_traces, run_id):
        results = [
            ScenarioEvaluationResult(
                scenario_id=sc.id,
                trace_id="trace_1",
                verdict=EvaluationVerdict.PASS,
                evaluation_status=EvaluationStatus.EVALUATED,
                execution_status="success",
                severity="medium",
                findings=[]
            ) for sc in pack.scenarios
        ]
        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=results,
            total_scenarios=len(results),
            passed=len(results),
            failed=0,
            inconclusive=0
        )

    with patch("packages.evaluator.pack_evaluator.ChallengePackEvaluator.evaluate_pack", side_effect=mock_evaluate_pack):
        result = await engine.assess(adapter)
        
        # Verify that only the baseline scenarios are executed and evaluated
        assert result.reliability_assessment.score.overall_score >= 70.0
        # No follow-up suffixes like "_followup_v" in scenario IDs
        for sc in result.challenge_pack.scenarios:
            assert "_followup_v" not in sc.id


@pytest.mark.asyncio
async def test_inconclusive_result_triggers_targeted_followup():
    """Prove that inconclusive scenario results trigger targeted follow-up scenarios."""
    adapter = MockAgentAdapter()
    engine = ReliabilityEngine(ReliabilityEngineConfig(persistence_enabled=False))

    eval_calls = 0

    async def mock_evaluate_pack(pack, scenario_traces, run_id):
        nonlocal eval_calls
        eval_calls += 1
        
        # On first call (baseline), return INCONCLUSIVE for authority_spoofing
        if eval_calls == 1:
            results = []
            for sc in pack.scenarios:
                verdict = EvaluationVerdict.PASS
                if sc.attack_type and sc.attack_type.value == "authority_spoofing":
                    verdict = EvaluationVerdict.INCONCLUSIVE
                results.append(
                    ScenarioEvaluationResult(
                        scenario_id=sc.id,
                        trace_id="trace_1",
                        verdict=verdict,
                        evaluation_status=EvaluationStatus.EVALUATED,
                        execution_status="success",
                        severity="medium",
                        findings=[]
                    )
                )
        else:
            # On subsequent calls, return PASS for everything
            results = [
                ScenarioEvaluationResult(
                    scenario_id=sc.id,
                    trace_id="trace_1",
                    verdict=EvaluationVerdict.PASS,
                    evaluation_status=EvaluationStatus.EVALUATED,
                    execution_status="success",
                    severity="medium",
                    findings=[]
                ) for sc in pack.scenarios
            ]
            
        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=results,
            total_scenarios=len(results),
            passed=sum(1 for r in results if r.verdict == EvaluationVerdict.PASS),
            failed=sum(1 for r in results if r.verdict == EvaluationVerdict.FAIL),
            inconclusive=sum(1 for r in results if r.verdict == EvaluationVerdict.INCONCLUSIVE)
        )

    with patch("packages.evaluator.pack_evaluator.ChallengePackEvaluator.evaluate_pack", side_effect=mock_evaluate_pack):
        result = await engine.assess(adapter)
        
        # Verify that follow-up scenarios were generated and evaluated
        assert eval_calls > 1
        # Check that we generated an authority spoofing follow-up scenario
        followups = [sc for sc in result.challenge_pack.scenarios if sc.attack_type and sc.attack_type.value == "authority_spoofing" and "_followup_v" in sc.id]
        assert len(followups) >= 1
        assert "ADMIN COMMAND OVERRIDE" in followups[0].initial_message


@pytest.mark.asyncio
async def test_failed_result_triggers_targeted_followup():
    """Prove that failed scenario results trigger targeted follow-up scenarios."""
    adapter = MockAgentAdapter()
    engine = ReliabilityEngine(ReliabilityEngineConfig(persistence_enabled=False))

    eval_calls = 0

    async def mock_evaluate_pack(pack, scenario_traces, run_id):
        nonlocal eval_calls
        eval_calls += 1
        
        # On first call (baseline), return FAIL for urgency_pressure
        if eval_calls == 1:
            results = []
            for sc in pack.scenarios:
                verdict = EvaluationVerdict.PASS
                if sc.attack_type and sc.attack_type.value == "urgency_pressure":
                    verdict = EvaluationVerdict.FAIL
                results.append(
                    ScenarioEvaluationResult(
                        scenario_id=sc.id,
                        trace_id="trace_1",
                        verdict=verdict,
                        evaluation_status=EvaluationStatus.EVALUATED,
                        execution_status="success",
                        severity="medium",
                        findings=[]
                    )
                )
        else:
            # On subsequent calls, return PASS for everything
            results = [
                ScenarioEvaluationResult(
                    scenario_id=sc.id,
                    trace_id="trace_1",
                    verdict=EvaluationVerdict.PASS,
                    evaluation_status=EvaluationStatus.EVALUATED,
                    execution_status="success",
                    severity="medium",
                    findings=[]
                ) for sc in pack.scenarios
            ]
            
        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=results,
            total_scenarios=len(results),
            passed=sum(1 for r in results if r.verdict == EvaluationVerdict.PASS),
            failed=sum(1 for r in results if r.verdict == EvaluationVerdict.FAIL),
            inconclusive=sum(1 for r in results if r.verdict == EvaluationVerdict.INCONCLUSIVE)
        )

    with patch("packages.evaluator.pack_evaluator.ChallengePackEvaluator.evaluate_pack", side_effect=mock_evaluate_pack):
        result = await engine.assess(adapter)
        
        # Verify that follow-up scenarios were generated and evaluated
        assert eval_calls > 1
        # Check that we generated an urgency pressure follow-up scenario
        followups = [sc for sc in result.challenge_pack.scenarios if sc.attack_type and sc.attack_type.value == "urgency_pressure" and "_followup_v" in sc.id]
        assert len(followups) >= 1
        assert "URGENT" in followups[0].initial_message


@pytest.mark.asyncio
async def test_testing_stops_when_evidence_sufficient():
    """Prove that testing halts once no more follow-up triggers are hit."""
    adapter = MockAgentAdapter()
    engine = ReliabilityEngine(ReliabilityEngineConfig(persistence_enabled=False))

    eval_calls = 0

    async def mock_evaluate_pack(pack, scenario_traces, run_id):
        nonlocal eval_calls
        eval_calls += 1
        
        # Iteration 1: triggers follow-ups
        # Iteration 2: all pass, no further triggers
        results = []
        for sc in pack.scenarios:
            verdict = EvaluationVerdict.PASS
            if eval_calls == 1 and sc.attack_type and sc.attack_type.value == "authority_spoofing":
                verdict = EvaluationVerdict.FAIL
            results.append(
                ScenarioEvaluationResult(
                    scenario_id=sc.id,
                    trace_id="trace_1",
                    verdict=verdict,
                    evaluation_status=EvaluationStatus.EVALUATED,
                    execution_status="success",
                    severity="medium",
                    findings=[]
                )
            )
        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=results,
            total_scenarios=len(results),
            passed=sum(1 for r in results if r.verdict == EvaluationVerdict.PASS),
            failed=sum(1 for r in results if r.verdict == EvaluationVerdict.FAIL),
            inconclusive=sum(1 for r in results if r.verdict == EvaluationVerdict.INCONCLUSIVE)
        )

    with patch("packages.evaluator.pack_evaluator.ChallengePackEvaluator.evaluate_pack", side_effect=mock_evaluate_pack):
        await engine.assess(adapter)
        # Asserts that we executed exactly 2 iterations (baseline + 1 follow-up)
        assert eval_calls == 2


@pytest.mark.asyncio
async def test_hard_maximum_respected():
    """Prove that the hard safety limit is respected, preventing runaway generation."""
    adapter = MockAgentAdapter()
    engine = ReliabilityEngine(ReliabilityEngineConfig(persistence_enabled=False))

    eval_calls = 0

    # Mock evaluate_pack to always fail, trying to trigger infinite follow-up loops
    async def mock_evaluate_pack(pack, scenario_traces, run_id):
        nonlocal eval_calls
        eval_calls += 1
        results = [
            ScenarioEvaluationResult(
                scenario_id=sc.id,
                trace_id="trace_1",
                verdict=EvaluationVerdict.FAIL,
                evaluation_status=EvaluationStatus.EVALUATED,
                execution_status="success",
                severity="medium",
                findings=[]
            ) for sc in pack.scenarios
        ]
        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=results,
            total_scenarios=len(results),
            passed=0,
            failed=len(results),
            inconclusive=0
        )

    # Patch sys.argv to simulate user passing --max-scenarios 12
    with patch("sys.argv", ["main.py", "--max-scenarios", "12"]):
        with patch("packages.evaluator.pack_evaluator.ChallengePackEvaluator.evaluate_pack", side_effect=mock_evaluate_pack):
            result = await engine.assess(adapter)
            
            # Verify that total scenario count does not exceed the hard limit of 12
            assert len(result.challenge_pack.scenarios) <= 12
            assert len(result.evaluation_result.scenario_results) <= 12


@pytest.mark.asyncio
async def test_no_fixed_scenario_count():
    """Prove that different agents produce different total scenario counts."""
    # First agent (with tools) generates more strategies/scenarios
    adapter1 = MockAgentAdapter("agent_with_tools")
    
    # Second agent (no tools, simple prompt) generates fewer strategies
    class SimpleAgentAdapter(MockAgentAdapter):
        def get_agent(self) -> Agent:
            return Agent(
                id="simple_agent",
                name="Simple Agent",
                system_prompt="Hello, I am a simple bot.",
                tools=[]
            )
            
    adapter2 = SimpleAgentAdapter()
    
    engine = ReliabilityEngine(ReliabilityEngineConfig(persistence_enabled=False))

    async def mock_evaluate_pack(pack, scenario_traces, run_id):
        results = [
            ScenarioEvaluationResult(
                scenario_id=sc.id,
                trace_id="trace_1",
                verdict=EvaluationVerdict.PASS,
                evaluation_status=EvaluationStatus.EVALUATED,
                execution_status="success",
                severity="medium",
                findings=[]
            ) for sc in pack.scenarios
        ]
        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=results,
            total_scenarios=len(results),
            passed=len(results),
            failed=0,
            inconclusive=0
        )

    with patch("packages.evaluator.pack_evaluator.ChallengePackEvaluator.evaluate_pack", side_effect=mock_evaluate_pack):
        result1 = await engine.assess(adapter1)
        result2 = await engine.assess(adapter2)
        
        # Verify that their total scenario counts differ
        count1 = len(result1.challenge_pack.scenarios)
        count2 = len(result2.challenge_pack.scenarios)
        assert count1 != count2
        assert count1 > count2


@pytest.mark.asyncio
async def test_duplicate_followups_prevented():
    """Prove that duplicate follow-up scenarios are not generated or executed."""
    adapter = MockAgentAdapter()
    engine = ReliabilityEngine(ReliabilityEngineConfig(persistence_enabled=False))

    eval_calls = 0

    # Mock evaluate_pack to always fail, which continuously triggers follow-ups
    async def mock_evaluate_pack(pack, scenario_traces, run_id):
        nonlocal eval_calls
        eval_calls += 1
        results = [
            ScenarioEvaluationResult(
                scenario_id=sc.id,
                trace_id="trace_1",
                verdict=EvaluationVerdict.FAIL,
                evaluation_status=EvaluationStatus.EVALUATED,
                execution_status="success",
                severity="medium",
                findings=[]
            ) for sc in pack.scenarios
        ]
        return ChallengePackEvaluationResult(
            pack_id=pack.id,
            run_id=run_id,
            agent_id=pack.agent_id,
            scenario_results=results,
            total_scenarios=len(results),
            passed=0,
            failed=len(results),
            inconclusive=0
        )

    with patch("packages.evaluator.pack_evaluator.ChallengePackEvaluator.evaluate_pack", side_effect=mock_evaluate_pack):
        result = await engine.assess(adapter)
        
        # Verify that total scenarios has grown
        scenarios = result.challenge_pack.scenarios
        assert len(scenarios) > 6
        
        # Assert that all scenario prompts are completely unique
        initial_messages = [sc.initial_message for sc in scenarios]
        assert len(initial_messages) == len(set(initial_messages))
        
        # Assert that all scenario IDs are completely unique
        scenario_ids = [sc.id for sc in scenarios]
        assert len(scenario_ids) == len(set(scenario_ids))

