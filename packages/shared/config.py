"""
Project-wide configuration.

All configuration is read from environment variables.
Use get_settings() to access configuration throughout the application.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    See .env.example for all available variables.
    """

    # LLM Provider API Keys
    gemini_api_key: str = Field(default="", description="Gemini API key.")
    openai_api_key: str = Field(default="", description="OpenAI API key.")

    # FastAPI
    api_host: str = Field(default="0.0.0.0", description="API host.")
    api_port: int = Field(default=8000, description="API port.")
    api_debug: bool = Field(default=False, description="Enable debug mode.")

    # Storage
    sqlite_db_path: str = Field(
        default="./data/aare.db",
        description="Path to the SQLite database file.",
    )
    traces_dir: str = Field(
        default="./traces",
        description="Directory for trace JSON files.",
    )
    runs_dir: str = Field(
        default="./runs",
        description="Directory for execution run JSON files.",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level.")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def traces_path(self) -> Path:
        """Resolved path to the traces directory."""
        return Path(self.traces_dir).resolve()

    @property
    def runs_path(self) -> Path:
        """Resolved path to the runs directory."""
        return Path(self.runs_dir).resolve()

    @property
    def db_path(self) -> Path:
        """Resolved path to the SQLite database."""
        return Path(self.sqlite_db_path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings.

    Uses lru_cache so settings are only loaded once per process.
    """
    return Settings()
