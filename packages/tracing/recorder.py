"""
TraceRecorder — captures execution events and produces a Trace.

Used by the sandbox to record everything that happens during
agent execution. Produces Trace objects that are serializable to JSON.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.core.models.trace import ExecutionStatus, StepType, Trace, TraceEvent
from packages.tracing.sanitizer import sanitize_data, sanitize_string


def _validate_filename(filename: str) -> str:
    """Validate filename to prevent path traversal attempts."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise ValueError(f"Invalid identifier or path traversal detected: {filename}")
    return filename


class TraceRecorder:
    """
    Records execution events during a sandbox run and produces a Trace.

    Usage:
        recorder = TraceRecorder(run_id=..., agent_id=..., ...)
        recorder.record_event(StepType.USER_INPUT, ...)
        recorder.record_event(StepType.TOOL_CALL, ...)
        trace = recorder.finish(status=ExecutionStatus.SUCCESS)
    """

    def __init__(
        self,
        run_id: str,
        agent_id: str,
        agent_version: str,
        scenario_id: str,
        scenario_name: str = "",
    ) -> None:
        self._run_id = run_id
        self._agent_id = agent_id
        self._agent_version = agent_version
        self._scenario_id = scenario_id
        self._scenario_name = scenario_name
        self._events: list[TraceEvent] = []
        self._step_counter = 0
        self._started_at = datetime.now(timezone.utc)

    def record_event(
        self,
        step_type: StepType,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        duration_ms: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> TraceEvent:
        """
        Record a single execution event.
        """
        sanitized_input = sanitize_data(input_data)
        sanitized_output = sanitize_data(output_data)
        sanitized_metadata = sanitize_data(metadata or {})

        event = TraceEvent(
            step_index=self._step_counter,
            type=step_type,
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            input_data=sanitized_input,
            output_data=sanitized_output,
            metadata=sanitized_metadata,
        )
        self._events.append(event)
        self._step_counter += 1
        return event

    def finish(
        self,
        status: ExecutionStatus = ExecutionStatus.SUCCESS,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        """
        Finalize the trace and return the complete Trace object.
        """
        completed_at = datetime.now(timezone.utc)
        sanitized_error = sanitize_string(error) if error else None
        sanitized_metadata = sanitize_data(metadata or {})

        return Trace(
            run_id=self._run_id,
            agent_id=self._agent_id,
            agent_version=self._agent_version,
            scenario_id=self._scenario_id,
            scenario_name=self._scenario_name,
            started_at=self._started_at,
            completed_at=completed_at,
            events=self._events,
            status=status,
            error=sanitized_error,
            metadata=sanitized_metadata,
        )


def save_trace(trace: Trace, traces_dir: str | Path = "traces") -> Path:
    """
    Serialize a Trace to JSON and write it to the traces directory.
    Uses atomic writes and path-safety checks.
    """
    filename = f"{trace.run_id}.json"
    _validate_filename(filename)

    traces_path = Path(traces_dir)
    traces_path.mkdir(parents=True, exist_ok=True)

    filepath = traces_path / filename
    temp_filepath = filepath.with_suffix(".tmp")

    trace_data = trace.model_dump(mode="json")
    sanitized_trace_data = sanitize_data(trace_data)

    try:
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(sanitized_trace_data, f, indent=2, default=str)
        temp_filepath.rename(filepath)
    except Exception:
        if temp_filepath.exists():
            temp_filepath.unlink()
        raise

    return filepath


def load_trace(filepath: str | Path) -> Trace:
    """
    Load a Trace from a JSON file.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {filepath}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse trace JSON in {filepath}: {exc}")

    try:
        return Trace.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Failed to validate Trace schema in {filepath}: {exc}")

