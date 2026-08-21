"""
Baseline store management.
"""

from __future__ import annotations

import json
from pathlib import Path
from packages.artifacts.store import ArtifactStore


class BaselineStore:
    """
    Manages a deterministic baseline store.
    Stores only the assessment ID reference.
    """

    def __init__(self, base_dir: str | Path = "data") -> None:
        self.base_dir = Path(base_dir)
        self.filepath = self.base_dir / "baseline.json"

    def set_baseline(self, assessment_id: str, store: ArtifactStore) -> None:
        """
        Validate that the referenced assessment exists and write it to the baseline file.
        """
        # Validate assessment exists - raises FileNotFoundError if it doesn't
        store.load_assessment(assessment_id)

        self.base_dir.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump({"assessment_id": assessment_id}, f, indent=2)

    def get_baseline(self) -> str | None:
        """
        Retrieve the stored baseline assessment ID if it exists.
        """
        if not self.filepath.exists():
            return None
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("assessment_id")
        except Exception:
            return None

    def clear_baseline(self) -> None:
        """
        Clear the baseline assessment ID reference.
        """
        if self.filepath.exists():
            self.filepath.unlink()
