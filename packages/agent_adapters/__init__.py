"""
Agent adapters package.

Contains the BaseAgentAdapter abstraction and all concrete adapter implementations.
The evaluation engine only depends on BaseAgentAdapter, never on concrete adapters.

See ADR-008 in DECISIONS.md.
"""

from packages.agent_adapters.base import BaseAgentAdapter
from packages.agent_adapters.http import HTTPAgentAdapter
from packages.agent_adapters.python import load_python_agent

__all__ = ["BaseAgentAdapter", "HTTPAgentAdapter", "load_python_agent"]

