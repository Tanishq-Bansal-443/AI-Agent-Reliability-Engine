from __future__ import annotations

from datetime import datetime, timezone
from packages.core.models.agent import (
    Agent,
    RiskProfile,
    Capability,
    AttackSurfaceEvidence,
    RiskIndicator,
)
from packages.profiler.base import StaticProfiler, LLMProfiler


class AgentProfilerOrchestrator:
    """
    Orchestrates the profiling process for an agent.
    Combines deterministic (StaticProfiler) and semantic (LLMProfiler) profiles.
    """

    def __init__(
        self,
        static_profiler: StaticProfiler | None = None,
        llm_profiler: LLMProfiler | None = None,
    ) -> None:
        self.static_profiler = static_profiler or StaticProfiler()
        self.llm_profiler = llm_profiler

    async def profile_agent(self, agent: Agent) -> RiskProfile:
        """
        Orchestrate deterministic and optional LLM profiling to produce a unified RiskProfile.
        """
        # 1. Run deterministic profiling
        static_profile = await self.static_profiler.profile(agent)

        # 2. Run LLM profiling if available
        if self.llm_profiler:
            llm_profile = await self.llm_profiler.profile(agent, base_profile=static_profile)
        else:
            llm_profile = None

        return self._merge_profiles(static_profile, llm_profile)

    def _merge_profiles(
        self, static_profile: RiskProfile, llm_profile: RiskProfile | None
    ) -> RiskProfile:
        if not llm_profile:
            return static_profile

        # If LLMProfiler returns an empty/default profile, return deterministic profile directly
        is_empty = (
            not llm_profile.capabilities
            and not llm_profile.attack_surfaces
            and not llm_profile.destructive_tools
            and not llm_profile.sensitive_tools
            and not llm_profile.risk_indicators
            and not llm_profile.evidence
        )
        if is_empty:
            return static_profile

        # Merge capabilities
        merged_capabilities = self._merge_capabilities(
            static_profile.capabilities, llm_profile.capabilities
        )

        # Merge attack surfaces
        merged_attack_surfaces = self._merge_attack_surfaces(
            static_profile.attack_surfaces, llm_profile.attack_surfaces
        )

        # Merge destructive and sensitive tools
        merged_destructive = list(dict.fromkeys(
            static_profile.destructive_tools + llm_profile.destructive_tools
        ))
        merged_sensitive = list(dict.fromkeys(
            static_profile.sensitive_tools + llm_profile.sensitive_tools
        ))

        # Merge risk indicators
        merged_risk_indicators = self._merge_risk_indicators(
            static_profile.risk_indicators, llm_profile.risk_indicators
        )

        # Merge evidence dictionary (handles structural provenance)
        merged_evidence = self._merge_evidence(
            static_profile, llm_profile
        )

        return RiskProfile(
            agent_id=static_profile.agent_id,
            capabilities=merged_capabilities,
            attack_surfaces=merged_attack_surfaces,
            destructive_tools=merged_destructive,
            sensitive_tools=merged_sensitive,
            risk_indicators=merged_risk_indicators,
            evidence=merged_evidence,
            profiled_at=static_profile.profiled_at,
        )

    def _merge_capabilities(
        self, static_caps: list[Capability], llm_caps: list[Capability]
    ) -> list[Capability]:
        caps_dict: dict[str, Capability] = {c.name: c for c in static_caps}
        for llm_cap in llm_caps:
            if llm_cap.name in caps_dict:
                existing = caps_dict[llm_cap.name]
                # Combine description and risk level, merge tools
                merged_desc = f"deterministic: {existing.description}\nllm: {llm_cap.description}"
                merged_risk = self._max_level(existing.risk_level, llm_cap.risk_level)
                merged_tools = list(dict.fromkeys(existing.related_tools + llm_cap.related_tools))
                caps_dict[llm_cap.name] = Capability(
                    name=llm_cap.name,
                    description=merged_desc,
                    risk_level=merged_risk,
                    related_tools=merged_tools,
                )
            else:
                caps_dict[llm_cap.name] = llm_cap
        return list(caps_dict.values())

    def _merge_attack_surfaces(
        self, static_surfs: list[AttackSurfaceEvidence], llm_surfs: list[AttackSurfaceEvidence]
    ) -> list[AttackSurfaceEvidence]:
        surfs_dict: dict[str, AttackSurfaceEvidence] = {s.attack_surface: s for s in static_surfs}
        for llm_surf in llm_surfs:
            name = llm_surf.attack_surface
            if name in surfs_dict:
                existing = surfs_dict[name]
                merged_reason = f"deterministic: {existing.reason}\nllm: {llm_surf.reason}"
                surfs_dict[name] = AttackSurfaceEvidence(
                    attack_surface=name,
                    reason=merged_reason,
                )
            else:
                surfs_dict[name] = llm_surf
        return list(surfs_dict.values())

    def _merge_risk_indicators(
        self, static_inds: list[RiskIndicator], llm_inds: list[RiskIndicator]
    ) -> list[RiskIndicator]:
        inds_dict: dict[str, RiskIndicator] = {i.name: i for i in static_inds}
        for llm_ind in llm_inds:
            name = llm_ind.name
            if name in inds_dict:
                existing = inds_dict[name]
                merged_desc = f"deterministic: {existing.description}\nllm: {llm_ind.description}" if existing.description != llm_ind.description else existing.description
                merged_sev = self._max_level(existing.severity, llm_ind.severity)
                merged_evidence = f"deterministic: {existing.evidence}\nllm: {llm_ind.evidence}"
                inds_dict[name] = RiskIndicator(
                    name=name,
                    severity=merged_sev,
                    description=merged_desc,
                    evidence=merged_evidence,
                )
            else:
                inds_dict[name] = llm_ind
        return list(inds_dict.values())

    def _merge_evidence(
        self, static_profile: RiskProfile, llm_profile: RiskProfile
    ) -> dict[str, str]:
        merged = {}

        # 1. Start with explicit evidence dictionaries
        static_ev = static_profile.evidence
        llm_ev = llm_profile.evidence

        for k, v in static_ev.items():
            merged[f"deterministic:{k}"] = v
            merged[k] = v

        for k, v in llm_ev.items():
            merged[f"llm:{k}"] = v
            if k in merged:
                merged[k] = f"deterministic: {merged[k]}\nllm: {v}"
            else:
                merged[k] = v

        # 2. Add structural provenance for attack surfaces as evidence
        for surf in static_profile.attack_surfaces:
            k = surf.attack_surface
            merged[f"deterministic:{k}"] = surf.reason
            if k not in merged:
                merged[k] = surf.reason

        for surf in llm_profile.attack_surfaces:
            k = surf.attack_surface
            merged[f"llm:{k}"] = surf.reason
            if f"deterministic:{k}" in merged:
                merged[k] = f"deterministic: {merged[f'deterministic:{k}']}\nllm: {surf.reason}"
            else:
                merged[k] = surf.reason

        return merged

    def _max_level(self, lvl1: str, lvl2: str) -> str:
        levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        l1 = lvl1.lower()
        l2 = lvl2.lower()
        if levels.get(l1, 0) >= levels.get(l2, 0):
            return lvl1
        return lvl2
