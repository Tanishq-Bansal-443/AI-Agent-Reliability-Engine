"""
Agent adapters package.

Contains the BaseAgentAdapter abstraction and all concrete adapter implementations.
The evaluation engine only depends on BaseAgentAdapter, never on concrete adapters.

See ADR-008 in DECISIONS.md.
"""

from packages.agent_adapters.base import BaseAgentAdapter

__all__ = ["BaseAgentAdapter"]
