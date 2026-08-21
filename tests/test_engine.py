"""
Tests for Phase 6A: End-to-End Reliability Pipeline & Orchestration.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any

from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentProfile, Capability, AttackSurfaceEvidence, RiskIndicator, RiskProfile
from packages.core.models.scenario import ChallengePack, Scenario, AttackStrategy, AttackStrategyType, ExpectedBehavior, ResourceLimits, RiskLevel
from packages.core.models.evaluation import ChallengePackEvaluationResult, EvaluationVerdict, EvaluationStatus
from packages.core.models.reliability import ReliabilityAssessment, ReliabilityScore
from packages.core.models.trace import Trace, ExecutionStatus
from packages.core.providers.base import BaseLLMProvider, LLMMessage, LLMResponse

from packages.engine import ReliabilityEngine, ReliabilityEngineConfig, ReliabilityRunResult
from packages.engine.models import ChallengePackConfig
from packages.sandbox.base import BaseSandbox
from packages.sandbox.local_mock import LocalMockSandbox
from packages.evaluator.deterministic import DeterministicEvaluator
from packages.reliability.closed_loop import ReliabilityClosedLoop
from agents.demo_customer_support.adapter import DemoAgentAdapter


# --- LLM Provider Mock ---

class FakeEngineLLMProvider(BaseLLMProvider):
    def __init__(self, profiling_json: str, eval_json: str, should_fail: bool = False) -> None:
        self.profiling_json = profiling_json
        self.eval_json = eval_json
        self.should_fail = should_fail
        self.calls: list[list[LLMMessage]] = []

    @property
    def provider_name(self) -> str:
        return "test-provider"

    @property
    def model_name(self) -> str:
        return "test-model"

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        self.calls.append(messages)
        if self.should_fail:
            raise RuntimeError("LLM provider call failed")
        
        # Check if the prompt is for profiling or evaluation
        prompt = messages[-1].content
        if "profile" in prompt.lower() or "capabilities" in prompt.lower() or "attack surface" in prompt.lower():
            content = self.profiling_json
        else:
            content = self.eval_json
            
        return LLMResponse(
            content=content,
            finish_reason="stop",
            model=self.model_name,
        )

    async def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[Any],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        raise NotImplementedError()


# Mock profiles and evaluator outputs
mock_profiling_json = """
{
  "capabilities": [
    {
      "name": "refund_processing",
      "description": "Processes order refunds.",
      "risk_level": "high",
      "related_tools": ["refund_order"]
    }
  ],
  "attack_surfaces": [
    {
      "attack_surface": "authority_spoofing",
      "reason": "Susceptible to admin command claims."
    }
  ],
  "destructive_tools": ["refund_order"],
  "sensitive_tools": [],
  "risk_indicators": [],
  "evidence": {}
}
"""

mock_eval_json = """
{
  "verdict": "pass",
  "confidence": 0.9,
  "reasoning": "The agent behaved correctly.",
  "findings": [],
  "evidence": []
}
"""


def _make_dummy_score() -> ReliabilityScore:
    return ReliabilityScore(
        agent_id="dummy",
        version="1.0",
        run_id="run-dummy",
        overall_score=80.0,
        pass_rate=0.8,
        failure_rate=0.2,
        scenario_count=10,
        pass_count=8,
        fail_count=2,
        critical_failure_count=0,
        severity_breakdown={},
        category_breakdown={},
        risk_level=RiskLevel.MEDIUM,
        confidence=1.0,
        recommendations=[],
        timestamp=datetime.now(timezone.utc),
        grade="B",
        scenario_score=80.0,
        severity_adjusted_score=80.0,
        coverage_score=50.0,
        total_scenarios=10,
        passed_scenarios=8,
        failed_scenarios=2,
        inconclusive_scenarios=0,
        critical_failures=0,
        high_failures=0,
        medium_failures=0,
        low_failures=0,
        execution_failures=0,
        evaluation_failures=0,
    )


@pytest.mark.asyncio
class TestReliabilityEngine:

    async def test_1_engine_construction_with_defaults(self) -> None:
        """Test 1: Engine construction with defaults."""
        engine = ReliabilityEngine()
        assert engine.config.llm_profiling_enabled is False
        assert engine.config.llm_evaluation_enabled is False
        assert engine.config.fail_fast is False
        assert engine.config.persistence_enabled is True
        assert engine.config.regression_enabled is True
        assert engine.config.adaptive_enabled is True

    async def test_2_to_8_complete_pipeline_and_integrations(self) -> None:
        """Test 2-8: Verify the complete pipeline, integrations, regression, and adaptive stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReliabilityEngineConfig(
                persistence_enabled=True,
                output_dir=str(Path(tmpdir) / "data"),
                traces_dir=str(Path(tmpdir) / "traces"),
                challenge_pack_limits=ChallengePackConfig(max_total_scenarios=2, max_scenarios_per_strategy=1),
            )
            engine = ReliabilityEngine(config=config)
            adapter = DemoAgentAdapter()

            # Run first assessment to create previous data
            result1 = await engine.assess(adapter)

            assert isinstance(result1, ReliabilityRunResult)
            assert result1.run_id
            assert result1.agent.id == adapter.agent_id
            assert result1.risk_profile
            assert len(result1.selected_strategies) > 0
            assert result1.challenge_pack
            assert len(result1.execution_result.traces) > 0
            assert result1.evaluation_result
            assert result1.reliability_assessment
            # No regression run because previous_assessment was not supplied
            assert result1.regression_report is None
            # Adaptive stages ran
            assert result1.adaptive_test_plan is not None
            assert result1.adaptive_challenge_pack is not None

            # Run second assessment supplying previous data to verify regression integration
            result2 = await engine.assess(
                adapter,
                previous_assessment=result1.reliability_assessment,
                previous_challenge_pack_result=result1.evaluation_result,
            )

            assert result2.regression_report is not None
            assert result2.regression_report.previous_run_id == result1.run_id
            assert result2.adaptive_test_plan is not None
            assert result2.adaptive_challenge_pack is not None

    async def test_9_optional_stages_disabled(self) -> None:
        """Test 9: Turn off regression and adaptive stages."""
        config = ReliabilityEngineConfig(
            persistence_enabled=False,
            regression_enabled=False,
            adaptive_enabled=False,
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        dummy_assessment = ReliabilityAssessment(
            agent_id=adapter.agent_id,
            agent_version=adapter.get_agent().version,
            challenge_pack_id="dummy",
            run_id="run1",
            score=_make_dummy_score(),
            findings=[],
            covered_strategies=[],
            uncovered_strategies=[],
            covered_attack_surfaces=[],
            uncovered_attack_surfaces=[],
            recommendations=[],
        )

        result = await engine.assess(adapter, previous_assessment=dummy_assessment)
        assert result.regression_report is None
        assert result.adaptive_test_plan is None
        assert result.adaptive_challenge_pack is None

    async def test_10_llm_profiling_disabled(self) -> None:
        """Test 10: Run profiling with LLM profiling disabled (uses static profiler)."""
        config = ReliabilityEngineConfig(
            llm_profiling_enabled=False,
            persistence_enabled=False,
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter)
        assert result.risk_profile is not None
        # Static profiler outputs capabilities
        assert len(result.risk_profile.capabilities) > 0

    async def test_11_llm_evaluation_disabled(self) -> None:
        """Test 11: Run evaluation with LLM evaluation disabled (deterministic evaluator)."""
        config = ReliabilityEngineConfig(
            llm_evaluation_enabled=False,
            persistence_enabled=False,
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter)
        assert result.evaluation_result is not None
        assert result.evaluation_result.metadata["evaluation_mode"] == "deterministic"

    async def test_12_execution_failure_propagation(self) -> None:
        """Test 12: Verify that scenario execution failures propagate to evaluation correctly."""
        class CrashSandbox(BaseSandbox):
            @property
            def sandbox_type(self) -> str:
                return "crash"
            async def reset(self) -> None:
                pass
            async def execute(self, scenario: Scenario, adapter: BaseAgentAdapter) -> Trace:
                raise RuntimeError("Sandbox crashed!")

        config = ReliabilityEngineConfig(
            persistence_enabled=False,
            regression_enabled=False,
            adaptive_enabled=False,
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter, sandbox=CrashSandbox())
        assert len(result.execution_result.traces) > 0
        assert all(t.status == ExecutionStatus.ERROR for t in result.execution_result.traces)
        # Verify that these traces are marked as execution failures by evaluator
        assert result.evaluation_result.execution_failures == len(result.execution_result.traces)
        assert result.evaluation_result.evaluated_count == 0

    async def test_13_evaluation_failure_isolation(self) -> None:
        """Test 13: Simulated evaluator crash on a single scenario is isolated."""
        config = ReliabilityEngineConfig(
            persistence_enabled=False,
            regression_enabled=False,
            adaptive_enabled=False,
            challenge_pack_limits=ChallengePackConfig(max_total_scenarios=3, max_scenarios_per_strategy=2),
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        original_evaluate = DeterministicEvaluator.evaluate
        async def mock_evaluate(self_eval, trace, scenario):
            if "Authority Spoofing" in scenario.name:
                raise RuntimeError("Simulated evaluator crash")
            return await original_evaluate(self_eval, trace, scenario)

        # Monkeypatch DeterministicEvaluator to simulate failure
        DeterministicEvaluator.evaluate = mock_evaluate
        try:
            result = await engine.assess(adapter)
            # Check that we have evaluation failures isolated
            assert result.evaluation_result.evaluation_failures > 0
            assert len(result.evaluation_result.scenario_results) > 0
            bad_results = [
                r for r in result.evaluation_result.scenario_results 
                if r.evaluation_status == EvaluationStatus.EVALUATION_ERROR
            ]
            assert len(bad_results) > 0
            assert "Simulated evaluator crash" in bad_results[0].metadata["error"]
        finally:
            DeterministicEvaluator.evaluate = original_evaluate

    async def test_14_partial_pipeline_result_preservation(self) -> None:
        """Test 14: If adaptive planning fails, the assessment is still successfully returned."""
        config = ReliabilityEngineConfig(
            persistence_enabled=False,
            regression_enabled=False,
            adaptive_enabled=True,
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        # Monkeypatch plan_next_test_pack to raise an error
        original_plan = ReliabilityClosedLoop.plan_next_test_pack
        async def mock_plan(*args, **kwargs):
            raise RuntimeError("Simulated adaptive planning error")

        ReliabilityClosedLoop.plan_next_test_pack = mock_plan
        try:
            result = await engine.assess(adapter)
            assert result.adaptive_test_plan is None
            assert result.adaptive_challenge_pack is None
            assert any("Adaptive closed loop planning failed" in w for w in result.metadata["warnings"])
            # Core components are still present
            assert result.risk_profile is not None
            assert result.challenge_pack is not None
            assert result.reliability_assessment is not None
        finally:
            ReliabilityClosedLoop.plan_next_test_pack = original_plan

    async def test_15_deterministic_stage_ordering(self) -> None:
        """Test 15: Attack strategies are sorted deterministically by ID."""
        config = ReliabilityEngineConfig(persistence_enabled=False)
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter)
        strategy_ids = [s.id for s in result.selected_strategies]
        assert strategy_ids == sorted(strategy_ids)

    async def test_16_correct_artifact_id_relationships(self) -> None:
        """Test 16: Ensure artifact ID links and relationships are preserved."""
        config = ReliabilityEngineConfig(persistence_enabled=False)
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter)
        pack = result.challenge_pack
        assert result.execution_result.pack_id == pack.id
        assert result.evaluation_result.pack_id == pack.id
        assert result.reliability_assessment.challenge_pack_id == pack.id
        for trace in result.execution_result.traces:
            assert trace.agent_id == adapter.agent_id
            assert trace.scenario_id in [s.id for s in pack.scenarios]

    async def test_17_persistence_enabled(self) -> None:
        """Test 17: Verify files are correctly saved to disk when persistence is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReliabilityEngineConfig(
                persistence_enabled=True,
                output_dir=str(Path(tmpdir) / "data"),
                traces_dir=str(Path(tmpdir) / "traces"),
            )
            engine = ReliabilityEngine(config=config)
            adapter = DemoAgentAdapter()

            result = await engine.assess(adapter)
            run_id = result.run_id

            # Verify traces are saved
            traces_path = Path(config.traces_dir)
            assert traces_path.exists()
            assert len(list(traces_path.glob("*.json"))) > 0

            # Verify evaluations, assessments, adaptive plan & pack are saved in the new layout
            assert (Path(config.output_dir) / "evaluations" / f"{run_id}.json").exists()
            assert (Path(config.output_dir) / "assessments" / f"{run_id}.json").exists()
            assert (Path(config.output_dir) / "reliability" / f"{run_id}.json").exists()
            assert (Path(config.output_dir) / "runs" / f"{result.execution_result.run_id}.json").exists()
            assert (Path(config.output_dir) / "adaptive" / f"{run_id}.json").exists()
            assert (Path(config.output_dir) / "challenge_packs" / f"{result.challenge_pack.id}.json").exists()


    async def test_18_persistence_disabled(self) -> None:
        """Test 18: Verify no files are written to disk when persistence is disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReliabilityEngineConfig(
                persistence_enabled=False,
                output_dir=str(Path(tmpdir) / "data"),
                traces_dir=str(Path(tmpdir) / "traces"),
            )
            engine = ReliabilityEngine(config=config)
            adapter = DemoAgentAdapter()

            result = await engine.assess(adapter)

            assert not Path(config.traces_dir).exists()
            assert not Path(config.output_dir).exists()

    async def test_19_demo_customer_support_agent_full_pipeline(self) -> None:
        """Test 19: Full pipeline run with demo customer support agent."""
        config = ReliabilityEngineConfig(persistence_enabled=False)
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter)
        assert result.agent.id == "demo-customer-support-v1"
        assert result.reliability_assessment.score.overall_score >= 0.0

    async def test_20_full_json_serialization_deserialization(self) -> None:
        """Test 20: Validate full JSON round-trip serialization of ReliabilityRunResult."""
        config = ReliabilityEngineConfig(persistence_enabled=False)
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter)

        # Serialize
        serialized = result.model_dump_json()
        assert serialized

        # Deserialize
        deserialized = ReliabilityRunResult.model_validate_json(serialized)
        assert deserialized.run_id == result.run_id
        assert deserialized.agent.id == result.agent.id
        assert deserialized.risk_profile.agent_id == result.risk_profile.agent_id
        assert len(deserialized.challenge_pack.scenarios) == len(result.challenge_pack.scenarios)

    async def test_21_repeatability_of_orchestration_structure(self) -> None:
        """Test 21: Verify structure repeatability."""
        config = ReliabilityEngineConfig(
            persistence_enabled=False,
            challenge_pack_limits=ChallengePackConfig(max_total_scenarios=2, max_scenarios_per_strategy=1),
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        res1 = await engine.assess(adapter)
        res2 = await engine.assess(adapter)

        # Scenarios generated should be identical (since generation is deterministic)
        assert len(res1.challenge_pack.scenarios) == len(res2.challenge_pack.scenarios)
        for s1, s2 in zip(res1.challenge_pack.scenarios, res2.challenge_pack.scenarios):
            assert s1.name == s2.name
            assert s1.attack_type == s2.attack_type
            assert s1.initial_message == s2.initial_message

    async def test_22_no_duplicated_logic(self) -> None:
        """Test 22: Verify engine delegates to proper modules rather than replicating code."""
        engine_src = Path("packages/engine/engine.py").read_text()
        assert "class ReliabilityEngine" in engine_src
        assert "from packages.profiler.orchestrator import AgentProfilerOrchestrator" in engine_src
        assert "from packages.scenario_engine.builder import ChallengePackBuilder" in engine_src
        assert "from packages.evaluator.pack_evaluator import ChallengePackEvaluator" in engine_src
        assert "from packages.reliability.scorer import ReliabilityScorer" in engine_src
        assert "from packages.regression.analyzer import RegressionAnalyzer" in engine_src
        assert "from packages.reliability.closed_loop import ReliabilityClosedLoop" in engine_src

    async def test_llm_enabled_pipeline(self) -> None:
        """Verification of semantic path with Mock LLM Provider."""
        provider = FakeEngineLLMProvider(mock_profiling_json, mock_eval_json)
        config = ReliabilityEngineConfig(
            llm_profiling_enabled=True,
            llm_evaluation_enabled=True,
            persistence_enabled=False,
        )
        engine = ReliabilityEngine(config=config)
        adapter = DemoAgentAdapter()

        result = await engine.assess(adapter, llm_provider=provider)
        assert result.risk_profile is not None
        # Check LLM profiling output capability refund_processing was merged
        caps = [c.name for c in result.risk_profile.capabilities]
        assert "refund_processing" in caps
        assert result.evaluation_result.metadata["evaluation_mode"] == "composite"
