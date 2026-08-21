"""
ArtifactStore implementation for persisting and loading engine execution results.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Type, TypeVar
from pydantic import BaseModel

from packages.artifacts.models import ReliabilityAssessmentArtifact

ModelT = TypeVar("ModelT", bound=BaseModel)


class ArtifactStore:
    """
    Persistence abstraction for AI Agent Reliability Engine artifacts.

    Enforces a strict directory structure:
    data/
        assessments/
            <assessment_id>.json
        challenge_packs/
            <pack_id>.json
        runs/
            <run_id>.json
        traces/
            <trace_id>.json
        evaluations/
            <run_id>.json
        reliability/
            <assessment_id>.json
        regression/
            <assessment_id>.json
        adaptive/
            <assessment_id>.json
    """

    def __init__(self, base_dir: str | Path = "data", traces_dir: str | Path = "traces") -> None:
        self.base_dir = Path(base_dir)
        self.traces_dir = Path(traces_dir)

        # Standard directories layout
        self.dirs = {
            "assessments": self.base_dir / "assessments",
            "challenge_packs": self.base_dir / "challenge_packs",
            "runs": self.base_dir / "runs",
            "traces": self.traces_dir,
            "evaluations": self.base_dir / "evaluations",
            "reliability": self.base_dir / "reliability",
            "regression": self.base_dir / "regression",
            "adaptive": self.base_dir / "adaptive",
        }

    def _get_path(self, sub_dir: str, filename: str) -> Path:
        if sub_dir == "traces":
            return self.traces_dir / filename
        return self.dirs.get(sub_dir, self.base_dir / sub_dir) / filename

    def save_artifact(self, model: BaseModel, sub_dir: str, filename: str) -> Path:
        """
        Atomic write helper to serialize a Pydantic model to a JSON file.
        """
        directory = self.dirs.get(sub_dir, self.base_dir / sub_dir)
        directory.mkdir(parents=True, exist_ok=True)

        filepath = directory / filename
        temp_filepath = filepath.with_suffix(".tmp")

        try:
            data = model.model_dump(mode="json")
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            temp_filepath.rename(filepath)
        except Exception:
            if temp_filepath.exists():
                temp_filepath.unlink()
            raise

        return filepath

    def load_artifact(self, model_cls: Type[ModelT], sub_dir: str, filename: str) -> ModelT:
        """
        Load and deserialize a Pydantic model from a JSON file.
        """
        filepath = self._get_path(sub_dir, filename)
        if not filepath.exists():
            raise FileNotFoundError(f"Artifact file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON in {filepath}: {exc}")

        try:
            return model_cls.model_validate(data)
        except Exception as exc:
            raise ValueError(f"Failed to validate model schema for {model_cls.__name__} in {filepath}: {exc}")

    def save_assessment(self, artifact: ReliabilityAssessmentArtifact) -> Path:
        """
        Calculate integrity hash and save top-level assessment artifact.
        """
        artifact.content_hash = ""
        hash_val = self.compute_model_hash(artifact)
        artifact.content_hash = hash_val

        return self.save_artifact(artifact, "assessments", f"{artifact.assessment_id}.json")

    def load_assessment(self, assessment_id: str) -> ReliabilityAssessmentArtifact:
        """
        Load top-level assessment and verify its SHA-256 integrity hash.
        """
        artifact = self.load_artifact(
            ReliabilityAssessmentArtifact, "assessments", f"{assessment_id}.json"
        )

        stored_hash = artifact.content_hash
        artifact.content_hash = ""
        computed_hash = self.compute_model_hash(artifact)
        artifact.content_hash = stored_hash

        if stored_hash != computed_hash:
            raise ValueError(
                f"Integrity checksum check failed for assessment {assessment_id}: stored hash "
                f"'{stored_hash}' does not match computed hash '{computed_hash}'."
            )

        return artifact

    def list_assessments(self) -> list[str]:
        """
        List all assessment IDs currently saved.
        """
        dir_path = self.dirs["assessments"]
        if not dir_path.exists():
            return []

        return sorted([p.stem for p in dir_path.glob("*.json")])

    @staticmethod
    def compute_model_hash(model: BaseModel) -> str:
        """
        Generate a stable SHA-256 hash of a Pydantic model's JSON representation.
        """
        data = model.model_dump(mode="json")
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
