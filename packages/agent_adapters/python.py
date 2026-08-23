"""
Python Agent Loader — dynamically loads and validates user-provided Python agent adapters.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any

from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentProfile


def load_python_agent(file_path: str, class_name: str | None = None) -> BaseAgentAdapter:
    """
    Dynamically load a Python module from a file path and instantiate the adapter class.
    
    If class_name is not provided, it will search the module for subclasses of BaseAgentAdapter
    or any class that implements the required methods (get_agent, get_profile, run).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Python agent file not found: {file_path}")

    # Security check: prevent loading outside permitted workspaces if configured,
    # but primarily validate module structure.
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load module spec for {file_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise RuntimeError(f"Error executing Python agent module {file_path}: {exc}")

    # Find the target class implementing the agent adapter interface
    target_class: type | None = None
    if class_name:
        if not hasattr(module, class_name):
            raise AttributeError(f"Module '{module_name}' has no class named '{class_name}'")
        target_class = getattr(module, class_name)
    else:
        # Search module members
        classes = [
            obj for _, obj in inspect.getmembers(module, inspect.isclass)
            if obj.__module__ == module.__name__
        ]

        # 1. First look for explicit subclass of BaseAgentAdapter
        for cls in classes:
            if issubclass(cls, BaseAgentAdapter) and cls is not BaseAgentAdapter:
                target_class = cls
                break

        # 2. Fall back to duck-typed class implementing get_agent, get_profile, and run
        if not target_class:
            for cls in classes:
                if (
                    hasattr(cls, "get_agent")
                    and hasattr(cls, "get_profile")
                    and hasattr(cls, "run")
                ):
                    target_class = cls
                    break

    if not target_class:
        raise ValueError(
            f"No valid agent adapter class found in '{file_path}'. Make sure it implements "
            "BaseAgentAdapter or has 'get_agent', 'get_profile', and 'run' methods."
        )

    # Instantiate the adapter class
    try:
        instance = target_class()
    except Exception as exc:
        raise RuntimeError(f"Failed to instantiate agent class '{target_class.__name__}': {exc}")

    # Perform structural validation on the instantiated adapter
    for method_name in ("get_agent", "get_profile", "run"):
        if not hasattr(instance, method_name) or not callable(getattr(instance, method_name)):
            raise TypeError(
                f"Loaded class '{target_class.__name__}' is missing required method '{method_name}'"
            )

    # Validate get_agent signature and return type
    try:
        agent_def = instance.get_agent()
        if not isinstance(agent_def, Agent):
            raise TypeError(
                f"get_agent() must return a packages.core.models.agent.Agent instance, "
                f"got {type(agent_def).__name__}"
            )
    except Exception as exc:
        if isinstance(exc, TypeError):
            raise
        raise ValueError(f"Error calling get_agent() on loaded class: {exc}")

    # Validate get_profile signature and return type
    try:
        profile_def = instance.get_profile()
        if not isinstance(profile_def, AgentProfile):
            raise TypeError(
                f"get_profile() must return a packages.core.models.agent.AgentProfile instance, "
                f"got {type(profile_def).__name__}"
            )
    except Exception as exc:
        if isinstance(exc, TypeError):
            raise
        raise ValueError(f"Error calling get_profile() on loaded class: {exc}")

    # Validate run signature (must be a coroutine function)
    if not inspect.iscoroutinefunction(instance.run):
        raise TypeError("run() method must be an async coroutine function")

    return instance
