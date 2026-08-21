"""
Persistence helpers for ExecutionRun.
"""

from __future__ import annotations

import json
from pathlib import Path
from packages.core.models.execution import ExecutionRun


def _validate_filename(filename: str) -> str:
    """Validate filename to prevent path traversal attempts."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise ValueError(f"Invalid identifier or path traversal detected: {filename}")
    return filename


def save_run(run: ExecutionRun, runs_dir: str | Path = "runs") -> Path:
    """
    Serialize an ExecutionRun to JSON and write it to the runs directory.

    Args:
        run: The execution run to save.
        runs_dir: Directory to write execution runs into (default: 'runs/').

    Returns:
        Path to the written file.
    """
    filename = f"{run.run_id}.json"
    _validate_filename(filename)

    runs_path = Path(runs_dir)
    runs_path.mkdir(parents=True, exist_ok=True)

    filepath = runs_path / filename


    run_data = run.model_dump(mode="json")
    
    # Atomic write pattern: write to tmp file first and then rename
    temp_filepath = filepath.with_suffix(".tmp")
    try:
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2, default=str)
        temp_filepath.rename(filepath)
    except Exception:
        if temp_filepath.exists():
            temp_filepath.unlink()
        raise

    return filepath


def load_run(filepath: str | Path) -> ExecutionRun:
    """
    Load an ExecutionRun from a JSON file.

    Args:
        filepath: Path to the execution run JSON file.

    Returns:
        Deserialized ExecutionRun object.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as an ExecutionRun.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"ExecutionRun file not found: {filepath}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse ExecutionRun JSON: {exc}")

    try:
        return ExecutionRun.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Failed to validate ExecutionRun data schema: {exc}")
