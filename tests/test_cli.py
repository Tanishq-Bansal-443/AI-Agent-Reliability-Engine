"""
Offline unit tests for the Reliability Engine CLI package.
"""

from __future__ import annotations

import json
import pytest
from io import StringIO
from pathlib import Path
from datetime import datetime, timezone

from packages.cli.main import async_main
from packages.artifacts.store import ArtifactStore
from packages.artifacts.models import ReliabilityAssessmentArtifact
from packages.core.models.reliability import ReliabilityAssessment, ReliabilityScore
from packages.core.models.scenario import ChallengePack, RiskLevel
from packages.core.models.evaluation import ChallengePackEvaluationResult
from packages.core.models.execution import ExecutionRun, ExecutionRunStatus
from packages.core.models.trace import Trace, ExecutionStatus
from packages.core.models.regression import RegressionReport, RegressionStatus
from packages.cli.baseline import BaselineStore
from packages.cli.policy import RegressionGate


async def run_cli(args_list: list[str]) -> tuple[int, str, str]:
    """Helper to run async CLI and capture outputs."""
    import sys
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    try:
        code = await async_main(args_list)
        return code, sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def create_mock_assessment(
    store: ArtifactStore,
    assessment_id: str,
    version: str = "1.0.0",
    agent_id: str = "demo-customer-support-v1",
    execution_failures: int = 0,
    evaluation_failures: int = 0,
) -> ReliabilityAssessmentArtifact:
    """Helper to populate mock assessment artifacts in a test store."""
    score = ReliabilityScore(
        agent_id=agent_id,
        version=version,
        run_id=assessment_id,
        overall_score=85.0,
        pass_rate=0.8,
        failure_rate=0.2,
        scenario_count=5,
        pass_count=4,
        fail_count=1,
        critical_failure_count=0,
        risk_level=RiskLevel.LOW,
        execution_failures=execution_failures,
        evaluation_failures=evaluation_failures,
    )

    assessment = ReliabilityAssessment(
        agent_id=agent_id,
        agent_version=version,
        challenge_pack_id="pack-1",
        run_id=assessment_id,
        score=score,
        findings=[],
    )

    eval_result = ChallengePackEvaluationResult(
        pack_id="pack-1",
        run_id=assessment_id,
        agent_id=agent_id,
        scenario_results=[],
        total_scenarios=5,
        passed=4,
        failed=1,
        inconclusive=0,
        execution_failures=execution_failures,
        evaluation_failures=evaluation_failures,
    )

    artifact = ReliabilityAssessmentArtifact(
        assessment_id=assessment_id,
        agent_id=agent_id,
        agent_version=version,
        challenge_pack_id="pack-1",
        execution_run_id=assessment_id,
        trace_ids=["trace-1"],
        evaluation_result=eval_result,
        reliability_assessment=assessment,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    # 1. Top level assessment
    store.save_assessment(artifact)

    # 2. Challenge Pack
    challenge_pack = ChallengePack(
        id="pack-1",
        name="Mock Challenge Pack",
        agent_id=agent_id,
        agent_version=version,
        scenarios=[],
    )
    store.save_artifact(challenge_pack, "challenge_packs", "pack-1.json")

    # 3. Execution Run
    run = ExecutionRun(
        run_id=assessment_id,
        challenge_pack_id="pack-1",
        agent_id=agent_id,
        agent_version=version,
        status=ExecutionRunStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1000,
        scenario_ids=["scen-1"],
        trace_references={"scen-1": "trace-1"},
    )
    store.save_artifact(run, "runs", f"{assessment_id}.json")

    # 4. Evaluation Result
    store.save_artifact(eval_result, "evaluations", f"{assessment_id}.json")

    # 5. Reliability Assessment
    store.save_artifact(assessment, "reliability", f"{assessment_id}.json")

    # 6. Trace File
    trace = Trace(
        run_id="trace-1",
        agent_id=agent_id,
        agent_version=version,
        scenario_id="scen-1",
        scenario_name="scenario-1",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        events=[],
        status=ExecutionStatus.SUCCESS,
    )
    from packages.tracing.recorder import save_trace
    save_trace(trace, store.traces_dir)

    return artifact


# --- 1. CLI Construction ---
@pytest.mark.asyncio
async def test_1_cli_construction() -> None:
    code, stdout, stderr = await run_cli(["--help"])
    assert code == 0
    assert "assess" in stdout
    assert "report" in stdout


# --- 2. Assess Command ---
@pytest.mark.asyncio
async def test_2_assess_command(tmp_path: Path) -> None:
    # Running offline assessment on demo agent
    out_dir = tmp_path / "data"
    tr_dir = tmp_path / "traces"
    code, stdout, stderr = await run_cli([
        "assess",
        "--agent", "demo_customer_support",
        "--output-dir", str(out_dir),
        "--traces-dir", str(tr_dir),
        "--max-scenarios", "2"
    ])
    assert code == 0
    assert "RELIABILITY METRICS" in stdout


# --- 3. Report Command ---
@pytest.mark.asyncio
async def test_3_report_command(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "test-assessment-id")

    code, stdout, stderr = await run_cli([
        "report", "test-assessment-id",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    assert "AGENT RELIABILITY REPORT" in stdout


# --- 4. List Command ---
@pytest.mark.asyncio
async def test_4_list_command(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-1")
    create_mock_assessment(store, "assess-2")

    code, stdout, stderr = await run_cli([
        "list",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    lines = stdout.strip().split("\n")
    assert "assess-1" in lines
    assert "assess-2" in lines


# --- 5. Show Command ---
@pytest.mark.asyncio
async def test_5_show_command(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-show")

    code, stdout, stderr = await run_cli([
        "show", "assess-show",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    assert "Assessment ID:           assess-show" in stdout
    assert "Agent ID:               demo-customer-support-v1" in stdout


# --- 6. Compare Command ---
@pytest.mark.asyncio
async def test_6_compare_command(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "prev-id")
    create_mock_assessment(store, "curr-id")

    code, stdout, stderr = await run_cli([
        "compare", "prev-id", "curr-id",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    assert "Score Delta:" in stdout
    assert "Regression Status:" in stdout


# --- 7. JSON Output ---
@pytest.mark.asyncio
async def test_7_json_output(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-json")

    code, stdout, stderr = await run_cli([
        "report", "assess-json",
        "--format", "json",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    data = json.loads(stdout)
    assert data["agent_id"] == "demo-customer-support-v1"


# --- 8. Markdown Output ---
@pytest.mark.asyncio
async def test_8_markdown_output(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-md")

    code, stdout, stderr = await run_cli([
        "report", "assess-md",
        "--format", "markdown",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    assert "# Agent Reliability Report" in stdout


# --- 9. Text Output ---
@pytest.mark.asyncio
async def test_9_text_output(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-text")

    code, stdout, stderr = await run_cli([
        "report", "assess-text",
        "--format", "text",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    assert "AGENT RELIABILITY REPORT" in stdout


# --- 10. CLI Exit Codes ---
@pytest.mark.asyncio
async def test_10_cli_exit_codes() -> None:
    code, stdout, stderr = await run_cli(["invalid-command"])
    # argparse exits with code 4 or print help / error and exits with 4
    assert code == 4


# --- 11. Regression Exit Code ---
@pytest.mark.asyncio
async def test_11_regression_exit_code(tmp_path: Path) -> None:
    # Pre-populate baseline with higher score
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    prev_artifact = create_mock_assessment(store, "prev-assess")
    prev_artifact.reliability_assessment.score.overall_score = 99.0
    store.save_assessment(prev_artifact)

    # Set baseline
    bstore = BaselineStore(base_dir=tmp_path / "data")
    bstore.set_baseline("prev-assess", store)

    # Now assess current demo agent (overall score will be lower than 99.0, leading to regressed status)
    code, stdout, stderr = await run_cli([
        "assess",
        "--agent", "demo_customer_support",
        "--previous", "prev-assess",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
        "--max-scenarios", "2",
        "--fail-on-regressed", "true",
    ])
    # Expect regression policy to fail with exit code 1
    assert code == 1


# --- 12. Execution Failure Exit Code ---
@pytest.mark.asyncio
async def test_12_execution_failure_exit_code(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-exec-fail", execution_failures=1)

    code, stdout, stderr = await run_cli([
        "report", "assess-exec-fail",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    # For report, loading a saved artifact succeeds even if it contains failures.
    assert code == 0


# --- 13. Evaluation Failure Exit Code ---
@pytest.mark.asyncio
async def test_13_evaluation_failure_exit_code(tmp_path: Path) -> None:
    # Constructing a scenario assessment run that simulates an evaluation failure.
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-eval-fail", evaluation_failures=1)
    
    code, stdout, stderr = await run_cli([
        "report", "assess-eval-fail",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0


# --- 14. Invalid Arguments ---
@pytest.mark.asyncio
async def test_14_invalid_arguments() -> None:
    # Invalid flag combination
    code, stdout, stderr = await run_cli(["assess", "--invalid-flag"])
    assert code == 4


# --- 15. Missing Assessment ---
@pytest.mark.asyncio
async def test_15_missing_assessment(tmp_path: Path) -> None:
    code, stdout, stderr = await run_cli([
        "show", "nonexistent-id",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 5


# --- 16. Baseline Set ---
@pytest.mark.asyncio
async def test_16_baseline_set(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-base")

    code, stdout, stderr = await run_cli([
        "baseline", "set", "assess-base",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    assert "Baseline set successfully" in stdout


# --- 17. Baseline Get ---
@pytest.mark.asyncio
async def test_17_baseline_get(tmp_path: Path) -> None:
    bstore = BaselineStore(base_dir=tmp_path / "data")
    # First get should be None
    code, stdout, stderr = await run_cli([
        "baseline", "get",
        "--output-dir", str(tmp_path / "data")
    ])
    assert code == 0
    assert stdout.strip() == "None"

    # Set baseline and check
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-base")
    bstore.set_baseline("assess-base", store)

    code, stdout, stderr = await run_cli([
        "baseline", "get",
        "--output-dir", str(tmp_path / "data")
    ])
    assert code == 0
    assert stdout.strip() == "assess-base"


# --- 18. Baseline Clear ---
@pytest.mark.asyncio
async def test_18_baseline_clear(tmp_path: Path) -> None:
    bstore = BaselineStore(base_dir=tmp_path / "data")
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "assess-base")
    bstore.set_baseline("assess-base", store)

    code, stdout, stderr = await run_cli([
        "baseline", "clear",
        "--output-dir", str(tmp_path / "data")
    ])
    assert code == 0
    assert bstore.get_baseline() is None


# --- 19. Baseline Validation ---
@pytest.mark.asyncio
async def test_19_baseline_validation(tmp_path: Path) -> None:
    # Try setting baseline to invalid ID
    code, stdout, stderr = await run_cli([
        "baseline", "set", "nonexistent-id",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 5


# --- 20. RegressionGate Policy ---
def test_20_regression_gate_policy() -> None:
    report = RegressionReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        previous_run_id="run-1",
        current_run_id="run-2",
        previous_score=80.0,
        current_score=75.0,
        score_delta=-5.0,
        previous_grade="B",
        current_grade="C",
        status=RegressionStatus.REGRESSED,
        new_failures=[],
        fixed_failures=[],
        persistent_failures=[],
        severity_changes=[],
    )
    gate = RegressionGate(fail_on_regressed=True)
    assert gate.evaluate(report) is False


# --- 21. Artifact Verification ---
@pytest.mark.asyncio
async def test_21_artifact_verification(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "verify-ok")

    code, stdout, stderr = await run_cli([
        "artifacts", "verify", "verify-ok",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 0
    data = json.loads(stdout)
    assert data["valid"] is True


# --- 22. Missing Child Artifact Detection ---
@pytest.mark.asyncio
async def test_22_missing_child_artifact_detection(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "verify-missing-child")
    
    # Delete the challenge pack file
    challenge_pack_path = store._get_path("challenge_packs", "pack-1.json")
    if challenge_pack_path.exists():
        challenge_pack_path.unlink()

    code, stdout, stderr = await run_cli([
        "artifacts", "verify", "verify-missing-child",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    assert code == 5
    data = json.loads(stdout)
    assert data["valid"] is False
    assert data["details"]["challenge_pack_exists"] is False


# --- 23. Corrupt Artifact Detection ---
@pytest.mark.asyncio
async def test_23_corrupt_artifact_detection(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "data", tmp_path / "traces")
    create_mock_assessment(store, "verify-corrupt")
    
    # Manually append corrupt text to top-level assessment json file
    path = store._get_path("assessments", "verify-corrupt.json")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\ncorrupt-extra-text")

    code, stdout, stderr = await run_cli([
        "artifacts", "verify", "verify-corrupt",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
    ])
    # Should fail integrity hash or json decode, leading to code 5
    assert code == 5


# --- 24. Demo Customer-Support Assessment ---
@pytest.mark.asyncio
async def test_24_demo_customer_support_assessment(tmp_path: Path) -> None:
    # Full run on demo customer support
    code, stdout, stderr = await run_cli([
        "assess",
        "--agent", "demo_customer_support",
        "--output-dir", str(tmp_path / "data"),
        "--traces-dir", str(tmp_path / "traces"),
        "--max-scenarios", "1"
    ])
    assert code == 0
    assert "AGENT RELIABILITY REPORT" in stdout


# --- 25. End-to-End CLI -> Engine -> ArtifactStore -> Report Flow ---
@pytest.mark.asyncio
async def test_25_end_to_end_flow(tmp_path: Path) -> None:
    out_dir = tmp_path / "data"
    tr_dir = tmp_path / "traces"

    # 1. Run first assessment
    code1, stdout1, stderr1 = await run_cli([
        "assess",
        "--agent", "demo_customer_support",
        "--output-dir", str(out_dir),
        "--traces-dir", str(tr_dir),
        "--max-scenarios", "1"
    ])
    assert code1 == 0

    # 2. Get assessment list and find the run ID
    store = ArtifactStore(out_dir, tr_dir)
    assessments = store.list_assessments()
    assert len(assessments) == 1
    assessment_id = assessments[0]

    # 3. Generate report for the assessment
    code2, stdout2, stderr2 = await run_cli([
        "report", assessment_id,
        "--output-dir", str(out_dir),
        "--traces-dir", str(tr_dir),
        "--format", "markdown"
    ])
    assert code2 == 0
    assert "# Agent Reliability Report" in stdout2
