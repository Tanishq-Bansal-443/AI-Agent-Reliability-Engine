"""
CLI Entrypoint for the AI Agent Reliability Engine.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.artifacts.store import ArtifactStore
from packages.artifacts.models import ReliabilityAssessmentArtifact
from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile
from packages.sandbox.tool_runtime import ToolRuntime

from packages.cli.baseline import BaselineStore
from packages.cli.policy import RegressionGate
from packages.cli.output import render_json, render_text, render_markdown


class VersionOverriddenAgentAdapter(BaseAgentAdapter):
    """
    Adapter wrapper that overrides the agent definition's version.
    """

    def __init__(self, adapter: BaseAgentAdapter, version: str) -> None:
        self._adapter = adapter
        self._version = version

    def get_agent(self) -> Agent:
        agent = self._adapter.get_agent()
        return agent.model_copy(update={"version": self._version})

    def get_profile(self) -> AgentProfile:
        return self._adapter.get_profile()

    async def run(self, agent_input: AgentInput, runtime: ToolRuntime) -> AgentOutput:
        return await self._adapter.run(agent_input, runtime)


def resolve_agent_adapter(agent_id: str) -> BaseAgentAdapter:
    """
    Resolve agent ID string to a concrete agent adapter instance.
    """
    normalized_id = agent_id.replace("-", "_").lower()
    if normalized_id in ("demo_customer_support", "demo_customer_support_v1"):
        from agents.demo_customer_support.adapter import DemoAgentAdapter
        return DemoAgentAdapter()
    else:
        raise ValueError(f"Unknown agent: '{agent_id}'")


def resolve_agent_adapter_cli(args: argparse.Namespace) -> BaseAgentAdapter:
    """
    Resolve CLI arguments to a concrete agent adapter instance.
    """
    agent_type = getattr(args, "agent_type", "built-in")
    if agent_type == "built-in":
        if not getattr(args, "agent", None):
            raise ValueError("--agent is required for built-in agent type")
        return resolve_agent_adapter(args.agent)
    elif agent_type == "http":
        if not getattr(args, "agent_url", None):
            raise ValueError("--agent-url is required for http agent type")
        from packages.agent_adapters.http import HTTPAgentAdapter
        from urllib.parse import urlparse
        parsed = urlparse(args.agent_url)
        agent_id = parsed.netloc.replace(":", "_").replace(".", "_") or "http_agent"
        return HTTPAgentAdapter(
            endpoint_url=args.agent_url,
            method=getattr(args, "agent_method", "POST"),
            timeout=getattr(args, "agent_timeout", 10.0),
            request_input_field=getattr(args, "agent_input_field", "message"),
            response_output_field=getattr(args, "agent_output_field", "response"),
            agent_id=agent_id,
            agent_name=f"HTTP Agent ({parsed.netloc})",
        )
    elif agent_type == "python":
        if not getattr(args, "agent_path", None):
            raise ValueError("--agent-path is required for python agent type")
        from packages.agent_adapters.python import load_python_agent
        return load_python_agent(args.agent_path, getattr(args, "agent_class", None))
    else:
        raise ValueError(f"Unknown agent type: '{agent_type}'")


def str_to_bool(val: str) -> bool:
    """Helper to parse command-line arguments to bool."""
    return val.lower() in ("true", "1", "yes", "on")


async def handle_assess(args: argparse.Namespace) -> int:
    """Run a complete reliability assessment."""
    try:
        adapter = resolve_agent_adapter_cli(args)
        if args.version:
            adapter = VersionOverriddenAgentAdapter(adapter, args.version)
    except ValueError as exc:
        print(f"CLI Error: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"Error initializing agent: {exc}", file=sys.stderr)
        return 4

    from packages.engine.models import ReliabilityEngineConfig
    from packages.scenario_engine.builder import ChallengePackConfig
    from packages.engine.engine import ReliabilityEngine

    challenge_limits = ChallengePackConfig()
    if args.max_scenarios is not None:
        challenge_limits.max_total_scenarios = args.max_scenarios

    output_dir = args.output_dir or "data"
    traces_dir = args.traces_dir or "traces"

    engine_config = ReliabilityEngineConfig(
        challenge_pack_limits=challenge_limits,
        execution_timeout=args.timeout,
        fail_fast=args.fail_fast,
        persistence_enabled=not args.no_persistence,
        output_dir=output_dir,
        traces_dir=traces_dir,
    )

    previous_assessment = None
    previous_challenge_pack_result = None
    store = ArtifactStore(base_dir=output_dir, traces_dir=traces_dir)

    if args.previous:
        try:
            prev_artifact = store.load_assessment(args.previous)
            previous_assessment = prev_artifact.reliability_assessment
            previous_challenge_pack_result = prev_artifact.evaluation_result
        except FileNotFoundError:
            print(f"Artifact not found error: Previous assessment '{args.previous}' was not found.", file=sys.stderr)
            return 5
        except ValueError as val_err:
            print(f"Artifact corrupted / integrity check failed for '{args.previous}': {val_err}", file=sys.stderr)
            return 5
        except Exception as exc:
            print(f"Error loading previous assessment '{args.previous}': {exc}", file=sys.stderr)
            return 5

    # Run assessment
    engine = ReliabilityEngine(config=engine_config)
    try:
        result = await engine.assess(
            adapter=adapter,
            previous_assessment=previous_assessment,
            previous_challenge_pack_result=previous_challenge_pack_result,
        )
    except Exception as exc:
        # Determine if failure is execution or evaluation failure.
        # Since evaluation is the last step that doesn't capture inner exceptions, we check traceback or assume.
        # But we can also inspect the exception itself.
        exc_str = str(exc).lower()
        if "evaluator" in exc_str or "scoring" in exc_str or "scorer" in exc_str:
            print(f"Evaluation Failure: {exc}", file=sys.stderr)
            return 3
        print(f"Execution Failure: {exc}", file=sys.stderr)
        return 2

    # Check for execution/evaluation failures reported in the score
    score_details = result.reliability_assessment.score
    if score_details.execution_failures > 0:
        print(f"Execution Failure: {score_details.execution_failures} execution failures reported in run.", file=sys.stderr)
        return 2
    if score_details.evaluation_failures > 0:
        print(f"Evaluation Failure: {score_details.evaluation_failures} evaluation failures reported in run.", file=sys.stderr)
        return 3

    # Output formatting
    fmt = args.format or "text"
    if fmt == "json":
        print(render_json(result.reliability_assessment))
    elif fmt == "markdown":
        print(render_markdown(result.reliability_assessment, result.regression_report, result.adaptive_test_plan))
    else:
        print(render_text(result.reliability_assessment, result.regression_report, result.adaptive_test_plan))

    # Evaluate Regression Gate Policy if previous baseline comparison ran
    if result.regression_report is not None:
        gate = RegressionGate(
            fail_on_regressed=args.fail_on_regressed,
            fail_on_new_high_critical=args.fail_on_new_high_critical,
            fail_on_severity_increases=args.fail_on_severity_increases,
            score_delta_threshold=args.score_delta_threshold,
            allow_stable=args.allow_stable,
            allow_improved=args.allow_improved,
            inconclusive_as_fail=args.inconclusive_as_fail,
        )
        gate_passed = gate.evaluate(result.regression_report)
        if not gate_passed:
            print("Reliability regression policy violated.", file=sys.stderr)
            return 1

    return 0


def handle_report(args: argparse.Namespace) -> int:
    """Load a persisted assessment and generate a human-readable report."""
    output_dir = args.output_dir or "data"
    traces_dir = args.traces_dir or "traces"
    store = ArtifactStore(base_dir=output_dir, traces_dir=traces_dir)

    try:
        artifact = store.load_assessment(args.assessment_id)
    except FileNotFoundError:
        print(f"Artifact not found error: Assessment '{args.assessment_id}' not found.", file=sys.stderr)
        return 5
    except ValueError as val_err:
        print(f"Artifact corrupted / integrity check failed: {val_err}", file=sys.stderr)
        return 5
    except Exception as exc:
        print(f"Error loading assessment '{args.assessment_id}': {exc}", file=sys.stderr)
        return 5

    fmt = args.format or "text"
    if fmt == "json":
        report_content = render_json(artifact.reliability_assessment)
    elif fmt == "markdown":
        report_content = render_markdown(artifact.reliability_assessment, artifact.regression_report, artifact.adaptive_test_plan)
    else:
        report_content = render_text(artifact.reliability_assessment, artifact.regression_report, artifact.adaptive_test_plan)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report_content)
        except Exception as exc:
            print(f"Failed to write report to {args.output}: {exc}", file=sys.stderr)
            return 5
    else:
        print(report_content)

    return 0


def handle_list(args: argparse.Namespace) -> int:
    """List persisted assessments."""
    output_dir = args.output_dir or "data"
    traces_dir = args.traces_dir or "traces"
    store = ArtifactStore(base_dir=output_dir, traces_dir=traces_dir)

    try:
        assessments = store.list_assessments()
        for assessment_id in assessments:
            print(assessment_id)
    except Exception as exc:
        print(f"Error listing assessments: {exc}", file=sys.stderr)
        return 5

    return 0


def handle_show(args: argparse.Namespace) -> int:
    """Display structured metadata for a persisted assessment."""
    output_dir = args.output_dir or "data"
    traces_dir = args.traces_dir or "traces"
    store = ArtifactStore(base_dir=output_dir, traces_dir=traces_dir)

    try:
        artifact = store.load_assessment(args.assessment_id)
    except FileNotFoundError:
        print(f"Artifact not found error: Assessment '{args.assessment_id}' not found.", file=sys.stderr)
        return 5
    except ValueError as val_err:
        print(f"Artifact corrupted / integrity check failed: {val_err}", file=sys.stderr)
        return 5
    except Exception as exc:
        print(f"Error loading assessment '{args.assessment_id}': {exc}", file=sys.stderr)
        return 5

    score_details = artifact.reliability_assessment.score
    regression_status = artifact.regression_report.status.value if artifact.regression_report else "None"

    lines = [
        f"Assessment ID:           {artifact.assessment_id}",
        f"Agent ID:               {artifact.agent_id}",
        f"Agent Version:          {artifact.agent_version}",
        f"Challenge Pack ID:      {artifact.challenge_pack_id}",
        f"Execution Run ID:       {artifact.execution_run_id}",
        f"Overall Score:          {score_details.overall_score}",
        f"Grade:                  {score_details.grade}",
        f"Regression Status:      {regression_status}",
        "Artifact Relationships:",
        f"  - Assessment:         {store._get_path('assessments', f'{artifact.assessment_id}.json')}",
        f"  - Challenge Pack:     {store._get_path('challenge_packs', f'{artifact.challenge_pack_id}.json')}",
        f"  - Execution Run:      {store._get_path('runs', f'{artifact.execution_run_id}.json')}",
        f"  - Evaluation Result:  {store._get_path('evaluations', f'{artifact.evaluation_result.run_id}.json')}",
        f"  - Reliability Score:  {store._get_path('reliability', f'{artifact.reliability_assessment.run_id}.json')}",
    ]

    if artifact.regression_report:
        lines.append(f"  - Regression Report:  {store._get_path('regression', f'{artifact.reliability_assessment.run_id}.json')}")
    if artifact.adaptive_test_plan:
        lines.append(f"  - Adaptive Test Plan: {store._get_path('adaptive', f'{artifact.reliability_assessment.run_id}.json')}")

    lines.append(f"Warnings:               {artifact.warnings}")
    lines.append(f"Errors:                 {artifact.errors}")

    for line in lines:
        print(line)

    return 0


def handle_compare(args: argparse.Namespace) -> int:
    """Compare two persisted assessments."""
    output_dir = args.output_dir or "data"
    traces_dir = args.traces_dir or "traces"
    store = ArtifactStore(base_dir=output_dir, traces_dir=traces_dir)

    try:
        prev_art = store.load_assessment(args.previous_id)
        curr_art = store.load_assessment(args.current_id)
    except FileNotFoundError as exc:
        print(f"Artifact not found error: {exc}", file=sys.stderr)
        return 5
    except ValueError as val_err:
        print(f"Artifact corrupted / integrity check failed: {val_err}", file=sys.stderr)
        return 5
    except Exception as exc:
        print(f"Error loading assessments: {exc}", file=sys.stderr)
        return 5

    from packages.regression.analyzer import RegressionAnalyzer
    try:
        analyzer = RegressionAnalyzer()
        report = analyzer.compare(
            previous=prev_art.reliability_assessment,
            current=curr_art.reliability_assessment,
            previous_challenge_pack_result=prev_art.evaluation_result,
            current_challenge_pack_result=curr_art.evaluation_result,
        )
    except Exception as exc:
        print(f"Regression comparison failed: {exc}", file=sys.stderr)
        return 3

    print(f"Score Delta:         {report.score_delta:+.2f}")
    print(f"Regression Status:   {report.status.value.upper()}")
    print(f"New Failures:        {len(report.new_failures)}")
    for f in report.new_failures:
        print(f"  - {f.title} ({f.current_severity})")
    print(f"Fixed Failures:      {len(report.fixed_failures)}")
    for f in report.fixed_failures:
        print(f"  - {f.title} ({f.previous_severity})")
    print(f"Persistent Failures: {len(report.persistent_failures)}")
    for f in report.persistent_failures:
        print(f"  - {f.title} ({f.current_severity})")
    print(f"Severity Changes:    {len(report.severity_changes)}")
    for f in report.severity_changes:
        print(f"  - {f.title} ({f.previous_severity} -> {f.current_severity})")
    print("Recommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")

    return 0


def handle_baseline_set(args: argparse.Namespace) -> int:
    """Set the baseline assessment ID."""
    output_dir = args.output_dir or "data"
    traces_dir = args.traces_dir or "traces"
    store = ArtifactStore(base_dir=output_dir, traces_dir=traces_dir)
    baseline_store = BaselineStore(base_dir=output_dir)

    try:
        baseline_store.set_baseline(args.assessment_id, store)
        print(f"Baseline set successfully to: {args.assessment_id}")
    except FileNotFoundError:
        print(f"Artifact not found error: Assessment '{args.assessment_id}' does not exist.", file=sys.stderr)
        return 5
    except ValueError as val_err:
        print(f"Artifact corrupted / integrity check failed for '{args.assessment_id}': {val_err}", file=sys.stderr)
        return 5
    except Exception as exc:
        print(f"Error setting baseline: {exc}", file=sys.stderr)
        return 5

    return 0


def handle_baseline_get(args: argparse.Namespace) -> int:
    """Print the current baseline assessment ID."""
    output_dir = args.output_dir or "data"
    baseline_store = BaselineStore(base_dir=output_dir)
    val = baseline_store.get_baseline()
    if val:
        print(val)
        return 0
    else:
        print("None")
        return 0


def handle_baseline_clear(args: argparse.Namespace) -> int:
    """Clear the baseline assessment ID."""
    output_dir = args.output_dir or "data"
    baseline_store = BaselineStore(base_dir=output_dir)
    baseline_store.clear_baseline()
    print("Baseline cleared.")
    return 0


def handle_artifacts_list(args: argparse.Namespace) -> int:
    """List assessments, alias for list."""
    return handle_list(args)


def handle_artifacts_verify(args: argparse.Namespace) -> int:
    """Verify integrity of top-level assessment and child references."""
    output_dir = args.output_dir or "data"
    traces_dir = args.traces_dir or "traces"
    store = ArtifactStore(base_dir=output_dir, traces_dir=traces_dir)

    # 1. Load the top-level artifact
    try:
        artifact = store.load_assessment(args.assessment_id)
    except FileNotFoundError:
        print(f"Verification FAILED: Top-level assessment artifact '{args.assessment_id}' not found.", file=sys.stderr)
        return 5
    except ValueError as val_err:
        print(f"Verification FAILED: Integrity checksum check failed: {val_err}", file=sys.stderr)
        return 5
    except Exception as exc:
        print(f"Verification FAILED: Failed to load assessment artifact: {exc}", file=sys.stderr)
        return 5

    # 2. Check child references and traces
    challenge_pack_path = store._get_path("challenge_packs", f"{artifact.challenge_pack_id}.json")
    challenge_pack_exists = challenge_pack_path.exists()

    run_path = store._get_path("runs", f"{artifact.execution_run_id}.json")
    execution_run_exists = run_path.exists()

    eval_path = store._get_path("evaluations", f"{artifact.evaluation_result.run_id}.json")
    evaluation_result_exists = eval_path.exists()

    reliability_path = store._get_path("reliability", f"{artifact.reliability_assessment.run_id}.json")
    reliability_assessment_exists = reliability_path.exists()

    missing_traces = []
    for trace_id in artifact.trace_ids:
        trace_path = store._get_path("traces", f"{trace_id}.json")
        if not trace_path.exists():
            missing_traces.append(trace_id)

    valid = (
        challenge_pack_exists
        and execution_run_exists
        and evaluation_result_exists
        and reliability_assessment_exists
        and not missing_traces
    )

    result = {
        "assessment_id": args.assessment_id,
        "valid": valid,
        "integrity_hash": artifact.content_hash,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "details": {
            "challenge_pack_exists": challenge_pack_exists,
            "execution_run_exists": execution_run_exists,
            "evaluation_result_exists": evaluation_result_exists,
            "reliability_assessment_exists": reliability_assessment_exists,
            "traces_resolved_count": len(artifact.trace_ids) - len(missing_traces),
            "missing_traces": missing_traces
        }
    }

    print(json.dumps(result, indent=2))

    if not valid:
        print("Verification FAILED: One or more referenced child artifacts or traces are missing.", file=sys.stderr)
        return 5

    return 0


async def handle_watch(args: argparse.Namespace) -> int:
    """Watch command, deterministic one-shot assess invocation."""
    output_dir = args.output_dir or "data"
    baseline_store = BaselineStore(base_dir=output_dir)
    baseline_id = baseline_store.get_baseline()

    # Re-use args to invoke assess
    assess_args = argparse.Namespace(**vars(args))
    assess_args.previous = baseline_id
    # Default agent if not specified
    if not getattr(assess_args, "agent", None) and getattr(assess_args, "agent_type", "built-in") == "built-in":
        assess_args.agent = "demo_customer_support"

    return await handle_assess(assess_args)


async def async_main(argv: list[str] | None = None) -> int:
    """Asynchronous CLI Entrypoint orchestration."""
    parser = argparse.ArgumentParser(
        prog="python -m packages.cli.main",
        description="Operational CLI for AI Agent Reliability Engine"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Assess parser
    parser_assess = subparsers.add_parser("assess", help="Run a complete reliability assessment (Built-in, HTTP, or Python)")
    parser_assess.add_argument("--agent", help="Agent adapter ID (e.g. demo_customer_support; required for built-in type)")
    parser_assess.add_argument("--agent-type", choices=["built-in", "http", "python"], default="built-in", help="Type of agent to evaluate")
    parser_assess.add_argument("--agent-url", help="HTTP endpoint URL for HTTP agent (e.g. http://localhost:5000/chat)")
    parser_assess.add_argument("--agent-method", default="POST", help="HTTP method for HTTP agent")
    parser_assess.add_argument("--agent-timeout", type=float, default=10.0, help="Timeout in seconds for HTTP agent request")
    parser_assess.add_argument("--agent-input-field", default="message", help="Request input JSON field path for HTTP agent")
    parser_assess.add_argument("--agent-output-field", default="response", help="Response output JSON field path for HTTP agent")
    parser_assess.add_argument("--agent-path", help="Python file path for custom Python agent")
    parser_assess.add_argument("--agent-class", help="Python class name to load for custom Python agent")
    parser_assess.add_argument("--version", help="Override agent version")
    parser_assess.add_argument("--max-scenarios", type=int, help="Maximum scenarios to run")
    parser_assess.add_argument("--timeout", type=float, help="Timeout in seconds per scenario")
    parser_assess.add_argument("--fail-fast", action="store_true", help="Fail fast on first scenario error")
    parser_assess.add_argument("--no-persistence", action="store_true", help="Disable assessment persistence")
    parser_assess.add_argument("--output-dir", default="data", help="Output directory path")
    parser_assess.add_argument("--traces-dir", default="traces", help="Traces directory path")
    parser_assess.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="Output format")
    parser_assess.add_argument("--previous", help="Previous assessment ID for regression analysis")
    # Gate options
    parser_assess.add_argument("--fail-on-regressed", type=str_to_bool, default=True)
    parser_assess.add_argument("--fail-on-new-high-critical", action="store_true", default=False)
    parser_assess.add_argument("--fail-on-severity-increases", action="store_true", default=False)
    parser_assess.add_argument("--score-delta-threshold", type=float, default=None)
    parser_assess.add_argument("--allow-stable", type=str_to_bool, default=True)
    parser_assess.add_argument("--allow-improved", type=str_to_bool, default=True)
    parser_assess.add_argument("--inconclusive-as-fail", action="store_true", default=False)

    # 2. Report parser
    parser_report = subparsers.add_parser("report", help="Generate a human-readable report")
    parser_report.add_argument("assessment_id", help="Persisted assessment ID")
    parser_report.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="Output format")
    parser_report.add_argument("--output", help="Write report to file path instead of stdout")
    parser_report.add_argument("--output-dir", default="data", help="Output directory path")
    parser_report.add_argument("--traces-dir", default="traces", help="Traces directory path")

    # 3. List parser
    parser_list = subparsers.add_parser("list", help="List persisted assessments")
    parser_list.add_argument("--output-dir", default="data", help="Output directory path")
    parser_list.add_argument("--traces-dir", default="traces", help="Traces directory path")

    # 4. Show parser
    parser_show = subparsers.add_parser("show", help="Display structured metadata for an assessment")
    parser_show.add_argument("assessment_id", help="Persisted assessment ID")
    parser_show.add_argument("--output-dir", default="data", help="Output directory path")
    parser_show.add_argument("--traces-dir", default="traces", help="Traces directory path")

    # 5. Compare parser
    parser_compare = subparsers.add_parser("compare", help="Compare two persisted assessments")
    parser_compare.add_argument("previous_id", help="Previous assessment ID")
    parser_compare.add_argument("current_id", help="Current assessment ID")
    parser_compare.add_argument("--output-dir", default="data", help="Output directory path")
    parser_compare.add_argument("--traces-dir", default="traces", help="Traces directory path")

    # 6. Baseline parser
    parser_baseline = subparsers.add_parser("baseline", help="Manage baseline assessment identification")
    baseline_sub = parser_baseline.add_subparsers(dest="subcommand", required=True)

    parser_base_set = baseline_sub.add_parser("set", help="Set baseline assessment ID")
    parser_base_set.add_argument("assessment_id", help="Assessment ID to set as baseline")
    parser_base_set.add_argument("--output-dir", default="data", help="Output directory path")
    parser_base_set.add_argument("--traces-dir", default="traces", help="Traces directory path")

    parser_base_get = baseline_sub.add_parser("get", help="Get baseline assessment ID")
    parser_base_get.add_argument("--output-dir", default="data", help="Output directory path")

    parser_base_clear = baseline_sub.add_parser("clear", help="Clear baseline assessment ID")
    parser_base_clear.add_argument("--output-dir", default="data", help="Output directory path")

    # 7. Artifacts parser
    parser_artifacts = subparsers.add_parser("artifacts", help="Manage assessment artifacts")
    artifacts_sub = parser_artifacts.add_subparsers(dest="subcommand", required=True)

    parser_art_list = artifacts_sub.add_parser("list", help="List persisted assessments")
    parser_art_list.add_argument("--output-dir", default="data", help="Output directory path")
    parser_art_list.add_argument("--traces-dir", default="traces", help="Traces directory path")

    parser_art_verify = artifacts_sub.add_parser("verify", help="Verify integrity of an assessment and its references")
    parser_art_verify.add_argument("assessment_id", help="Assessment ID to verify")
    parser_art_verify.add_argument("--output-dir", default="data", help="Output directory path")
    parser_art_verify.add_argument("--traces-dir", default="traces", help="Traces directory path")

    # 8. Watch parser
    parser_watch = subparsers.add_parser("watch", help="Continuous-mode trigger (one-shot cron execution)")
    parser_watch.add_argument("--agent", help="Agent adapter ID")
    parser_watch.add_argument("--agent-type", choices=["built-in", "http", "python"], default="built-in", help="Type of agent to evaluate")
    parser_watch.add_argument("--agent-url", help="HTTP endpoint URL for HTTP agent (e.g. http://localhost:5000/chat)")
    parser_watch.add_argument("--agent-method", default="POST", help="HTTP method for HTTP agent")
    parser_watch.add_argument("--agent-timeout", type=float, default=10.0, help="Timeout in seconds for HTTP agent request")
    parser_watch.add_argument("--agent-input-field", default="message", help="Request input JSON field path for HTTP agent")
    parser_watch.add_argument("--agent-output-field", default="response", help="Response output JSON field path for HTTP agent")
    parser_watch.add_argument("--agent-path", help="Python file path for custom Python agent")
    parser_watch.add_argument("--agent-class", help="Python class name to load for custom Python agent")
    parser_watch.add_argument("--version", help="Override agent version")
    parser_watch.add_argument("--max-scenarios", type=int, help="Maximum scenarios to run")
    parser_watch.add_argument("--timeout", type=float, help="Timeout in seconds per scenario")
    parser_watch.add_argument("--fail-fast", action="store_true", help="Fail fast on first scenario error")
    parser_watch.add_argument("--no-persistence", action="store_true", help="Disable assessment persistence")
    parser_watch.add_argument("--output-dir", default="data", help="Output directory path")
    parser_watch.add_argument("--traces-dir", default="traces", help="Traces directory path")
    parser_watch.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="Output format")
    # Gate options for watch
    parser_watch.add_argument("--fail-on-regressed", type=str_to_bool, default=True)
    parser_watch.add_argument("--fail-on-new-high-critical", action="store_true", default=False)
    parser_watch.add_argument("--fail-on-severity-increases", action="store_true", default=False)
    parser_watch.add_argument("--score-delta-threshold", type=float, default=None)
    parser_watch.add_argument("--allow-stable", type=str_to_bool, default=True)
    parser_watch.add_argument("--allow-improved", type=str_to_bool, default=True)
    parser_watch.add_argument("--inconclusive-as-fail", action="store_true", default=False)

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # Help or invalid arguments raise SystemExit.
        # If it was -h/--help (code 0), return 0. Otherwise return 4 (invalid configuration/CLI usage).
        return 0 if exc.code == 0 else 4

    if args.command == "assess":
        return await handle_assess(args)
    elif args.command == "report":
        return handle_report(args)
    elif args.command == "list":
        return handle_list(args)
    elif args.command == "show":
        return handle_show(args)
    elif args.command == "compare":
        return handle_compare(args)
    elif args.command == "baseline":
        if args.subcommand == "set":
            return handle_baseline_set(args)
        elif args.subcommand == "get":
            return handle_baseline_get(args)
        elif args.subcommand == "clear":
            return handle_baseline_clear(args)
    elif args.command == "artifacts":
        if args.subcommand == "list":
            return handle_artifacts_list(args)
        elif args.subcommand == "verify":
            return handle_artifacts_verify(args)
    elif args.command == "watch":
        return await handle_watch(args)

    return 0


def main(argv: list[str] | None = None) -> None:
    """CLI Synchronous entrypoint."""
    sys.exit(asyncio.run(async_main(argv)))


if __name__ == "__main__":
    main()
