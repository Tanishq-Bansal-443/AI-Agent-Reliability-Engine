"""
Profiler package.

Analyzes agents to produce structured AgentProfile objects.
Phase 0: Interface definitions only.
Phase 2: Full implementation with deterministic + LLM-assisted profiling.
"""

from packages.profiler.base import BaseProfiler, StaticProfiler, LLMProfiler

__all__ = ["BaseProfiler", "StaticProfiler", "LLMProfiler"]
