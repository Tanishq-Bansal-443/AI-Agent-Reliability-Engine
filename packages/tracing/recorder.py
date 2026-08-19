"""
TraceRecorder — captures execution events and produces a Trace.

Used by the sandbox to record everything that happens during
agent execution. Produces Trace objects that are serializable to JSON.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.core.models.trace import ExecutionStatus, StepType, Trace, TraceEvent


def sanitize_string(text: str | None) -> str | None:
    """
    Redact sensitive keys, credentials, or tokens from string values.
    """
    if not text:
        return text
    # Redact Google/Gemini API keys
    text = re.sub(r"AIzaSy[A-Za-z0-9-_]{33}", "[REDACTED_GEMINI_KEY]", text)
    # Redact OpenAI API keys (sk-... or sk-proj-...)
    text = re.sub(r"sk-[A-Za-z0-9-_]{32,}", "[REDACTED_OPENAI_KEY]", text)
    # Redact credentials/passwords patterns
    text = re.sub(r"(password|passwd|pwd|key|secret|token)=\s*[^\s&;]+", r"\1=[REDACTED]", text, flags=re.IGNORECASE)
    return text


def sanitize_data(data: Any) -> Any:
    """
    Recursively sanitize string values in data structures.
    """
    if isinstance(data, str):
        return sanitize_string(data)
    elif isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(x) for x in data]
    return data


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
        challenge_pack_id: str | None = None,
        execution_run_id: str | None = None,
    ) -> None:
        self._run_id = run_id
        self._agent_id = agent_id
        self._agent_version = agent_version
        self._scenario_id = scenario_id
        self._scenario_name = scenario_name
        self._challenge_pack_id = challenge_pack_id
        self._execution_run_id = execution_run_id
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

        Args:
            step_type: The type of event.
            input_data: Structured input for this step.
            output_data: Structured output from this step.
            duration_ms: How long this step took.
            metadata: Additional event metadata.

        Returns:
            The recorded TraceEvent.
        """
        event = TraceEvent(
            step_index=self._step_counter,
            type=step_type,
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            input_data=sanitize_data(input_data),
            output_data=sanitize_data(output_data),
            metadata=sanitize_data(metadata or {}),
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

        Args:
            status: Final execution status.
            error: Error message if status is error or timeout.
            metadata: Additional trace-level metadata.

        Returns:
            Complete, serializable Trace.
        """
        completed_at = datetime.now(timezone.utc)
        sanitized_error = sanitize_string(error)
        return Trace(
            run_id=self._run_id,
            agent_id=self._agent_id,
            agent_version=self._agent_version,
            scenario_id=self._scenario_id,
            scenario_name=self._scenario_name,
            challenge_pack_id=self._challenge_pack_id,
            execution_run_id=self._execution_run_id,
            started_at=self._started_at,
            completed_at=completed_at,
            events=self._events,
            status=status,
            error=sanitized_error,
            metadata=metadata or {},
        )


def save_trace(trace: Trace, traces_dir: str | Path = "traces") -> Path:
    """
    Serialize a Trace to JSON and write it to the traces directory.

    Args:
        trace: The trace to save.
        traces_dir: Directory to write traces into (default: 'traces/').

    Returns:
        Path to the written file.
    """
    traces_path = Path(traces_dir)
    traces_path.mkdir(parents=True, exist_ok=True)

    filename = f"{trace.run_id}.json"
    filepath = traces_path / filename

    trace_data = trace.model_dump(mode="json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, default=str)

    return filepath


def load_trace(filepath: str | Path) -> Trace:
    """
    Load a Trace from a JSON file.

    Args:
        filepath: Path to the trace JSON file.

    Returns:
        Deserialized Trace object.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as a Trace.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Trace.model_validate(data)
