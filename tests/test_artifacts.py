"""
Tests for Phase 6B Reliability Artifacts & Persistence.
"""

from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel

from packages.artifacts.models import ReliabilityAssessmentArtifact
from packages.artifacts.store import ArtifactStore
from packages.core.models.agent import Agent, RiskProfile
from packages.core.models.scenario import ChallengePack, ExpectedBehavior, Scenario, ResourceLimits, RiskLevel
from packages.core.models.trace import Trace, ExecutionStatus
from packages.core.models.execution import ChallengePackExecutionResult, ExecutionRun, ExecutionRunStatus
from packages.core.models.evaluation import ChallengePackEvaluationResult, EvaluationVerdict, EvaluationStatus
from packages.core.models.reliability import ReliabilityAssessment, ReliabilityScore
from packages.core.models.regression import RegressionReport, RegressionStatus
from packages.core.models.adaptive import AdaptiveTestPlan

from packages.regression.analyzer import RegressionAnalyzer
from packages.regression.adaptive import AdaptiveRegressionAnalyzer
from packages.engine import ReliabilityEngine, ReliabilityEngineConfig
from agents.demo_customer_support.adapter import DemoAgentAdapter


def _make_dummy_score() -> ReliabilityScore:
    return ReliabilityScore(
        agent_id="test-agent",
        version="1.0.0",
        run_id="run-1",
        overall_score=85.0,
        pass_rate=0.85,
        failure_rate=0.15,
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
        scenario_score=85.0,
        severity_adjusted_score=85.0,
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


def _make_dummy_assessment(run_id: str) -> ReliabilityAssessment:
    return ReliabilityAssessment(
        agent_id="test-agent",
        agent_version="1.0.0",
        challenge_pack_id="pack-1",
        run_id=run_id,
        score=_make_dummy_score(),
        findings=[],
        covered_strategies=[],
        uncovered_strategies=[],
        covered_attack_surfaces=[],
        uncovered_attack_surfaces=[],
        recommendations=[],
    )


def _make_dummy_evaluation(run_id: str) -> ChallengePackEvaluationResult:
    return ChallengePackEvaluationResult(
        pack_id="pack-1",
        run_id=run_id,
        agent_id="test-agent",
        scenario_results=[],
        total_scenarios=10,
        passed=8,
        failed=2,
        inconclusive=0,
        execution_failures=0,
        evaluation_failures=0,
    )


class TestArtifactStore:

    def test_artifact_store_construction(self) -> None:
        """Cover 1: Artifact store construction and directory initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=tmpdir, traces_dir=str(Path(tmpdir) / "traces"))
            assert store.base_dir == Path(tmpdir)
            assert store.traces_dir == Path(tmpdir) / "traces"
            assert "assessments" in store.dirs

    def test_save_load_assessment_round_trip(self) -> None:
        """Cover 2, 8, 9, 21, 22: Save/load assessment round-trip, content hashes, and trace references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=tmpdir, traces_dir=str(Path(tmpdir) / "traces"))
            
            assessment = _make_dummy_assessment("run-123")
            evaluation = _make_dummy_evaluation("run-123")
            
            artifact = ReliabilityAssessmentArtifact(
                assessment_id="run-123",
                agent_id="test-agent",
                agent_version="1.0.0",
                challenge_pack_id="pack-1",
                execution_run_id="exec-123",
                trace_ids=["trace-1", "trace-2"],
                evaluation_result=evaluation,
                reliability_assessment=assessment,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            
            # Save
            filepath = store.save_assessment(artifact)
            assert filepath.exists()
            
            # Load and verify
            loaded = store.load_assessment("run-123")
            assert loaded.assessment_id == "run-123"
            assert loaded.agent_id == "test-agent"
            assert loaded.trace_ids == ["trace-1", "trace-2"]
            assert loaded.content_hash != ""
            
            # Verify no duplicate trace payloads exist in the top-level artifact itself
            with open(filepath, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            assert "traces" not in raw_data
            assert "trace_ids" in raw_data

    def test_save_load_child_artifacts(self) -> None:
        """Cover 3: Save/load child artifacts individually."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=tmpdir, traces_dir=str(Path(tmpdir) / "traces"))
            
            evaluation = _make_dummy_evaluation("run-1")
            
            # Save generic child
            store.save_artifact(evaluation, "evaluations", "run-1.json")
            assert (Path(tmpdir) / "evaluations" / "run-1.json").exists()
            
            # Load generic child
            loaded = store.load_artifact(ChallengePackEvaluationResult, "evaluations", "run-1.json")
            assert loaded.run_id == "run-1"
            assert loaded.pack_id == "pack-1"

    def test_missing_artifact_handling(self) -> None:
        """Cover 4: Missing artifact file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=tmpdir, traces_dir=str(Path(tmpdir) / "traces"))
            with pytest.raises(FileNotFoundError):
                store.load_assessment("non-existent")

    def test_corrupt_json_handling(self) -> None:
        """Cover 5, 28: Corrupt JSON file or child raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=tmpdir, traces_dir=str(Path(tmpdir) / "traces"))
            
            # Write corrupt JSON
            assessment_dir = Path(tmpdir) / "assessments"
            assessment_dir.mkdir(parents=True, exist_ok=True)
            with open(assessment_dir / "corrupt.json", "w", encoding="utf-8") as f:
                f.write("{invalid-json}")
                
            with pytest.raises(ValueError) as excinfo:
                store.load_assessment("corrupt")
            assert "Failed to parse JSON" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_persistence_disabled_and_enabled(self) -> None:
        """Cover 6, 7: Engine integration with persistence disabled and enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Disabled
            config_disabled = ReliabilityEngineConfig(
                persistence_enabled=False,
                output_dir=str(Path(tmpdir) / "data"),
                traces_dir=str(Path(tmpdir) / "traces"),
            )
            engine = ReliabilityEngine(config=config_disabled)
            adapter = DemoAgentAdapter()
            
            result = await engine.assess(adapter)
            assert not Path(config_disabled.output_dir).exists()
            assert not Path(config_disabled.traces_dir).exists()
            
            # 2. Enabled
            config_enabled = ReliabilityEngineConfig(
                persistence_enabled=True,
                output_dir=str(Path(tmpdir) / "data"),
                traces_dir=str(Path(tmpdir) / "traces"),
            )
            engine = ReliabilityEngine(config=config_enabled)
            
            result_enabled = await engine.assess(adapter)
            
            # Verify directories created
            assert Path(config_enabled.output_dir).exists()
            assert Path(config_enabled.traces_dir).exists()
            assert (Path(config_enabled.output_dir) / "assessments" / f"{result_enabled.run_id}.json").exists()
            assert (Path(config_enabled.output_dir) / "runs" / f"{result_enabled.execution_result.run_id}.json").exists()
            assert (Path(config_enabled.output_dir) / "challenge_packs" / f"{result_enabled.challenge_pack.id}.json").exists()

    def test_provenance_relationships(self) -> None:
        """Cover 10, 11, 12, 13: ExecutionRun -> Trace, ChallengePack -> ExecutionRun, etc."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=tmpdir, traces_dir=str(Path(tmpdir) / "traces"))
            
            # Trace
            trace = Trace(
                run_id="trace-123",
                agent_id="test-agent",
                agent_version="1.0.0",
                scenario_id="sc-1",
                scenario_name="Spoof",
                events=[],
                status=ExecutionStatus.SUCCESS,
            )
            # Save trace
            from packages.tracing.recorder import save_trace
            save_trace(trace, store.traces_dir)
            
            # ExecutionRun
            exec_run = ExecutionRun(
                run_id="exec-123",
                challenge_pack_id="pack-1",
                agent_id="test-agent",
                agent_version="1.0.0",
                status=ExecutionRunStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                scenario_ids=["sc-1"],
                trace_references={"sc-1": "trace-123"},
            )
            store.save_artifact(exec_run, "runs", "exec-123.json")
            
            # Load and check ExecutionRun -> Trace relationship
            loaded_run = store.load_artifact(ExecutionRun, "runs", "exec-123.json")
            assert loaded_run.trace_references["sc-1"] == "trace-123"
            
            # Assessment -> RegressionReport
            regression = RegressionReport(
                agent_id="test-agent",
                agent_version="1.0.0",
                previous_run_id="run-1",
                current_run_id="run-2",
                previous_score=80.0,
                current_score=85.0,
                score_delta=5.0,
                previous_grade="B",
                current_grade="B",
                status=RegressionStatus.IMPROVED,
            )
            
            # Assessment -> AdaptiveTestPlan
            adaptive = AdaptiveTestPlan(
                agent_id="test-agent",
                agent_version="1.0.0",
                budget=5,
                reasoning_summary="Test budget",
            )
            
            # Save complete assessment
            assessment = _make_dummy_assessment("run-2")
            evaluation = _make_dummy_evaluation("run-2")
            
            artifact = ReliabilityAssessmentArtifact(
                assessment_id="run-2",
                agent_id="test-agent",
                agent_version="1.0.0",
                challenge_pack_id="pack-1",
                execution_run_id="exec-123",
                trace_ids=["trace-123"],
                evaluation_result=evaluation,
                reliability_assessment=assessment,
                regression_report=regression,
                adaptive_test_plan=adaptive,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            store.save_assessment(artifact)
            
            loaded_art = store.load_assessment("run-2")
            assert loaded_art.regression_report.previous_run_id == "run-1"
            assert loaded_art.adaptive_test_plan.budget == 5

    def test_loaded_assessment_usable_by_analyzers(self) -> None:
        """Cover 14, 15, 16: Loaded assessment usable by RegressionAnalyzer and AdaptiveRegressionAnalyzer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=tmpdir, traces_dir=str(Path(tmpdir) / "traces"))
            
            assessment_prev = _make_dummy_assessment("run-prev")
            evaluation_prev = _make_dummy_evaluation("run-prev")
            
            assessment_curr = _make_dummy_assessment("run-curr")
            evaluation_curr = _make_dummy_evaluation("run-curr")
            
            # Set slightly different scores
            assessment_prev.score.overall_score = 80.0
            assessment_prev.score.grade = "C"
            assessment_curr.score.overall_score = 90.0
            assessment_curr.score.grade = "A"
            
            art_prev = ReliabilityAssessmentArtifact(
                assessment_id="run-prev",
                agent_id="test-agent",
                agent_version="1.0.0",
                challenge_pack_id="pack-1",
                execution_run_id="exec-prev",
                trace_ids=[],
                evaluation_result=evaluation_prev,
                reliability_assessment=assessment_prev,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            
            art_curr = ReliabilityAssessmentArtifact(
                assessment_id="run-curr",
                agent_id="test-agent",
                agent_version="1.0.0",
                challenge_pack_id="pack-1",
                execution_run_id="exec-curr",
                trace_ids=[],
                evaluation_result=evaluation_curr,
                reliability_assessment=assessment_curr,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            
            store.save_assessment(art_prev)
            store.save_assessment(art_curr)
            
            # Load back
            loaded_prev = store.load_assessment("run-prev")
            loaded_curr = store.load_assessment("run-curr")
            
            # 1. Usable by RegressionAnalyzer
            analyzer = RegressionAnalyzer()
            report = analyzer.compare(
                previous=loaded_prev.reliability_assessment,
                current=loaded_curr.reliability_assessment,
                previous_challenge_pack_result=loaded_prev.evaluation_result,
                current_challenge_pack_result=loaded_curr.evaluation_result,
            )
            assert report.score_delta == 10.0
            assert report.status == RegressionStatus.IMPROVED
            
            # 2. Usable by AdaptiveRegressionAnalyzer
            adaptive_analyzer = AdaptiveRegressionAnalyzer()
            test_plan = adaptive_analyzer.build_test_plan(
                current_assessment=loaded_curr.reliability_assessment,
                regression_report=report,
                current_evaluation=loaded_curr.evaluation_result,
                challenge_pack=ChallengePack(name="Test", agent_id="test-agent"),
                budget=10,
            )
            assert test_plan.budget == 10
            assert test_plan.agent_id == "test-agent"

    @pytest.mark.asyncio
    async def test_end_to_end_engine_and_reload(self) -> None:
        """Cover 18, 27: Full end-to-end engine -> artifact store -> reload using Demo Agent Adapter."""
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
            
            # Load back using store
            store = ArtifactStore(config.output_dir, config.traces_dir)
            loaded_art = store.load_assessment(run_id)
            
            assert loaded_art.assessment_id == run_id
            assert loaded_art.agent_id == adapter.agent_id
            assert loaded_art.evaluation_result.run_id == run_id
            assert loaded_art.reliability_assessment.run_id == run_id
            
            # Check list_assessments
            assessments_list = store.list_assessments()
            assert run_id in assessments_list
