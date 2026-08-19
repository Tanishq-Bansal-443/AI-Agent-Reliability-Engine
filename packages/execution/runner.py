"""
ScenarioExecutor and ExecutionRunner implementations.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any
from uuid import uuid4

from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.execution import (
    ScenarioExecutionResult,
    ChallengePackExecutionResult,
    ChallengePackExecutionStats,
    ExecutionRun,
)
from packages.core.models.scenario import Scenario, ChallengePack, ConversationTurn
from packages.core.models.trace import ExecutionStatus, StepType, Trace
from packages.execution.base import BaseScenarioExecutor, BaseExecutionRunner
from packages.sandbox.base import BaseSandbox
from packages.sandbox.local_mock import LocalMockSandbox
from packages.shared.config import get_settings
from packages.tracing.recorder import TraceRecorder, save_trace


class ScenarioExecutor(BaseScenarioExecutor):
    """
    ScenarioExecutor manages the execution of a single scenario.

    It orchestrates multi-turn conversations by sending inputs to the agent
    one turn at a time, invoking the sandbox for each turn, and collecting
    all results into a consolidated master trace.
    """

    def __init__(self, sandbox: BaseSandbox | None = None) -> None:
        self.sandbox = sandbox or LocalMockSandbox()

    async def execute(
        self,
        scenario: Scenario,
        adapter: BaseAgentAdapter,
        challenge_pack_id: str | None = None,
        execution_run_id: str | None = None,
    ) -> ScenarioExecutionResult:
        started_at = datetime.now(timezone.utc)

        # 1. Reset sandbox environment to clean state for this scenario execution
        await self.sandbox.reset()

        # 2. Extract user turns
        user_turns = [turn for turn in scenario.turns if turn.role == "user"]
        if not user_turns:
            user_turns = [ConversationTurn(role="user", content=scenario.initial_message)]

        # 3. Create master trace recorder
        run_id = str(uuid4())
        recorder = TraceRecorder(
            run_id=run_id,
            agent_id=adapter.agent_id,
            agent_version=adapter.agent_version,
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            challenge_pack_id=challenge_pack_id,
            execution_run_id=execution_run_id,
        )

        history: list[ConversationTurn] = []
        final_response: str | None = None
        overall_status = ExecutionStatus.SUCCESS
        overall_error: str | None = None

        # 4. Multi-turn execution loop
        for idx, user_turn in enumerate(user_turns):
            # Record user input event in the master trace
            recorder.record_event(
                step_type=StepType.USER_INPUT,
                input_data={"message": user_turn.content, "scenario": scenario.name},
                output_data={},
            )

            # Add user turn to history
            history.append(user_turn)

            # Construct temporary scenario for this turn with the history accumulated so far
            temp_scenario = scenario.model_copy(deep=True)
            temp_scenario.turns = history.copy()
            temp_scenario.initial_message = user_turn.content

            try:
                # Execute turn in the sandbox
                turn_trace = await self.sandbox.execute(temp_scenario, adapter)

                # Copy events from turn trace (skipping USER_INPUT to avoid duplicate user messages)
                is_last_turn = (idx == len(user_turns) - 1)
                assistant_text = ""

                for event in turn_trace.events:
                    if event.type == StepType.USER_INPUT:
                        continue

                    event_type = event.type
                    # Convert intermediate turn responses to MODEL_OUTPUT
                    if event.type == StepType.FINAL_RESPONSE and not is_last_turn:
                        event_type = StepType.MODEL_OUTPUT

                    recorder.record_event(
                        step_type=event_type,
                        input_data=event.input_data,
                        output_data=event.output_data,
                        duration_ms=event.duration_ms,
                        metadata=event.metadata,
                    )

                    # Capture the assistant response
                    if event.type == StepType.FINAL_RESPONSE:
                        assistant_text = event.output_data.get("response", "")
                        if is_last_turn:
                            final_response = assistant_text

                # Append assistant's turn to conversation history for future turns
                if turn_trace.status not in (ExecutionStatus.TIMEOUT, ExecutionStatus.ERROR):
                    history.append(ConversationTurn(role="assistant", content=assistant_text))
                else:
                    overall_status = turn_trace.status
                    overall_error = turn_trace.error
                    break

            except Exception as exc:
                overall_status = ExecutionStatus.ERROR
                overall_error = str(exc)
                recorder.record_event(
                    step_type=StepType.ERROR,
                    input_data={},
                    output_data={"error": str(exc)},
                )
                break

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Build master Trace object
        master_trace = recorder.finish(
            status=overall_status,
            error=overall_error,
            metadata={
                "sandbox_type": self.sandbox.sandbox_type,
                "turns_executed": len(history) // 2,
                "timeout_seconds": scenario.resource_limits.timeout_seconds,
            },
        )

        # Build execution status
        exec_status_map = {
            ExecutionStatus.SUCCESS: ExecutionStatus.COMPLETED,
            ExecutionStatus.COMPLETED: ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILURE: ExecutionStatus.FAILED,
            ExecutionStatus.FAILED: ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT: ExecutionStatus.TIMEOUT,
            ExecutionStatus.ERROR: ExecutionStatus.ERROR,
        }
        exec_status = exec_status_map.get(overall_status, ExecutionStatus.ERROR)

        return ScenarioExecutionResult(
            scenario_id=scenario.id,
            challenge_pack_id=challenge_pack_id,
            execution_run_id=execution_run_id,
            execution_status=exec_status,
            trace=master_trace,
            final_response=final_response,
            error=overall_error,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            metadata={
                "sandbox_type": self.sandbox.sandbox_type,
            },
        )


class ExecutionRunner(BaseExecutionRunner):
    """
    ExecutionRunner manages the execution of a full ChallengePack.

    Executes scenarios in deterministic order, isolates environment state,
    and calculates aggregate execution stats.
    """

    def __init__(
        self,
        executor: BaseScenarioExecutor | None = None,
        max_scenarios: int | None = None,
        fail_fast: bool = False,
        persist: bool = True,
        runs_dir: str | Path | None = None,
        traces_dir: str | Path | None = None,
    ) -> None:
        self.executor = executor or ScenarioExecutor()
        self.max_scenarios = max_scenarios
        self.fail_fast = fail_fast
        self.persist = persist
        self.runs_dir = runs_dir
        self.traces_dir = traces_dir

    async def run(
        self,
        challenge_pack: ChallengePack,
        adapter: BaseAgentAdapter,
        per_scenario_timeout: int | None = None,
    ) -> ChallengePackExecutionResult:
        started_at = datetime.now(timezone.utc)

        # Scenarios executed in deterministic order (as defined in ChallengePack)
        scenarios = challenge_pack.scenarios
        if self.max_scenarios is not None:
            scenarios = scenarios[:self.max_scenarios]

        # 1. Create a single authoritative run ID and the ExecutionRun metadata
        run_id = str(uuid4())
        execution_run = ExecutionRun(
            run_id=run_id,
            challenge_pack_id=challenge_pack.id,
            agent_id=adapter.agent_id,
            agent_version=adapter.agent_version,
            status=ExecutionStatus.RUNNING,
            started_at=started_at,
            scenario_ids=[s.id for s in scenarios],
            metadata={
                "fail_fast": self.fail_fast,
                "max_scenarios": self.max_scenarios,
                "per_scenario_timeout": per_scenario_timeout,
            },
        )

        scenario_results: list[ScenarioExecutionResult] = []
        trace_references: dict[str, str] = {}

        total_scenarios = len(scenarios)
        pending_scenarios = total_scenarios
        running_scenarios = 0
        completed_scenarios = 0
        failed_scenarios = 0
        timeout_scenarios = 0
        error_scenarios = 0

        for scenario in scenarios:
            # If fail_fast is enabled and we have encountered any failure/timeout/error, abort
            if self.fail_fast and (failed_scenarios > 0 or timeout_scenarios > 0 or error_scenarios > 0):
                break

            pending_scenarios -= 1
            running_scenarios += 1

            # Prepare scenario with optional timeout override
            scenario_to_run = scenario
            if per_scenario_timeout is not None:
                scenario_to_run = scenario.model_copy(deep=True)
                scenario_to_run.resource_limits = scenario.resource_limits.model_copy(deep=True)
                scenario_to_run.resource_limits.timeout_seconds = per_scenario_timeout

            # Execute the scenario and pass down the single authoritative run_id
            result = await self.executor.execute(
                scenario_to_run,
                adapter,
                challenge_pack_id=challenge_pack.id,
                execution_run_id=run_id,
            )
            scenario_results.append(result)
            trace_references[scenario.id] = result.trace.run_id

            # Persist Trace immediately if enabled
            if self.persist:
                t_dir = self.traces_dir or get_settings().traces_dir
                save_trace(result.trace, traces_dir=t_dir)

            running_scenarios -= 1

            # Update stats
            if result.execution_status == ExecutionStatus.COMPLETED:
                completed_scenarios += 1
            elif result.execution_status == ExecutionStatus.FAILED:
                failed_scenarios += 1
            elif result.execution_status == ExecutionStatus.TIMEOUT:
                timeout_scenarios += 1
            elif result.execution_status == ExecutionStatus.ERROR:
                error_scenarios += 1

            # Check fail-fast again after executing
            if self.fail_fast and result.execution_status in (
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMEOUT,
                ExecutionStatus.ERROR,
            ):
                break

        completed_at = datetime.now(timezone.utc)
        total_duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Compile overall execution status
        # If any scenario fails, times out, or errors, the pack run is marked FAILED.
        if failed_scenarios > 0 or timeout_scenarios > 0 or error_scenarios > 0:
            overall_status = ExecutionStatus.FAILED
        else:
            overall_status = ExecutionStatus.COMPLETED

        stats = ChallengePackExecutionStats(
            total_scenarios=total_scenarios,
            pending_scenarios=pending_scenarios,
            running_scenarios=running_scenarios,
            completed_scenarios=completed_scenarios,
            failed_scenarios=failed_scenarios,
            timeout_scenarios=timeout_scenarios,
            error_scenarios=error_scenarios,
            total_duration_ms=total_duration_ms,
        )

        # Update and finalize the ExecutionRun object
        execution_run.status = overall_status
        execution_run.completed_at = completed_at
        execution_run.duration_ms = total_duration_ms
        execution_run.trace_references = trace_references
        execution_run.stats = stats

        # Persist ExecutionRun if enabled
        if self.persist:
            r_dir = self.runs_dir or get_settings().runs_dir
            save_run(execution_run, runs_dir=r_dir)

        return ChallengePackExecutionResult(
            run_id=run_id,
            challenge_pack_id=challenge_pack.id,
            agent_id=adapter.agent_id,
            agent_version=adapter.agent_version,
            execution_status=overall_status,
            scenario_results=scenario_results,
            stats=stats,
            trace_references=trace_references,
            metadata={
                "fail_fast": self.fail_fast,
                "max_scenarios": self.max_scenarios,
                "per_scenario_timeout": per_scenario_timeout,
            },
        )


def save_run(run: ExecutionRun, runs_dir: str | Path = "runs") -> Path:
    """
    Serialize an ExecutionRun to JSON and write it to the runs directory.

    Args:
        run: The ExecutionRun to save.
        runs_dir: Directory to write runs into (default: 'runs/').

    Returns:
        Path to the written file.
    """
    runs_path = Path(runs_dir)
    runs_path.mkdir(parents=True, exist_ok=True)

    filename = f"{run.run_id}.json"
    filepath = runs_path / filename

    run_data = run.model_dump(mode="json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2, default=str)

    return filepath


def load_run(filepath: str | Path) -> ExecutionRun:
    """
    Load an ExecutionRun from a JSON file.

    Args:
        filepath: Path to the run JSON file.

    Returns:
        Deserialized ExecutionRun object.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as an ExecutionRun.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Run file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return ExecutionRun.model_validate(data)
