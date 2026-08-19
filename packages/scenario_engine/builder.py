"""
ChallengePackBuilder and ChallengePackConfig implementations for Phase 2C.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from packages.core.models.agent import Agent, RiskProfile
from packages.core.models.scenario import ChallengePack, Scenario, AttackStrategy
from packages.scenario_engine.attack_strategy import AttackStrategyRegistry, AttackStrategyType
from packages.scenario_engine.base import BaseScenarioGenerator
from packages.scenario_engine.generator import DeterministicScenarioGenerator
from packages.scenario_engine.validator import validate_scenario
from packages.profiler.base import ToolClassifier, ToolCapability

logger = logging.getLogger(__name__)


class ChallengePackConfig(BaseModel):
    """
    Configuration limits for ChallengePack generation.
    """

    max_total_scenarios: int = Field(
        default=20,
        description="Maximum total scenarios allowed in the ChallengePack.",
    )
    max_scenarios_per_strategy: int = Field(
        default=3,
        description="Maximum scenarios allowed per attack strategy.",
    )


class ChallengePackBuilder:
    """
    Orchestrates the pipeline of converting a profiled Agent into a coherent,
    validated, deduplicated, and reproducible ChallengePack.
    """

    def __init__(
        self,
        generator: BaseScenarioGenerator | None = None,
        config: ChallengePackConfig | None = None,
    ) -> None:
        self.generator = generator or DeterministicScenarioGenerator()
        self.config = config or ChallengePackConfig()

    async def build(
        self,
        agent: Agent,
        risk_profile: RiskProfile,
    ) -> ChallengePack:
        """
        Orchestration method that converts a profiled Agent and RiskProfile
        into a finalized ChallengePack.
        """
        # 1. Find relevant attack strategies using AttackStrategyRegistry
        relevant_strategies = AttackStrategyRegistry.find_relevant_strategies(risk_profile)
        # Deterministically sort strategies by ID to guarantee reproducible ordering
        relevant_strategies = sorted(relevant_strategies, key=lambda s: s.id)

        valid_scenarios_by_strategy: dict[str, list[Scenario]] = {
            s.id: [] for s in relevant_strategies
        }
        
        seen_hashes: set[str] = set()
        invalid_scenarios_info: list[dict[str, Any]] = []
        duplicate_count = 0
        total_generated_count = 0

        # 2. Generate scenarios for each relevant strategy
        for strategy in relevant_strategies:
            scenarios = await self.generator.generate(agent, risk_profile, strategy)
            total_generated_count += len(scenarios)

            for sc in scenarios:
                # 3. Validate every generated scenario
                try:
                    validate_scenario(sc, agent)
                except ValueError as err:
                    # 4. Remove/exclude invalid scenarios and record them
                    invalid_scenarios_info.append({
                        "scenario_id": sc.id,
                        "name": sc.name,
                        "strategy_id": strategy.id,
                        "error": str(err),
                    })
                    continue

                # 5. Deduplicate identical scenarios
                sc_hash = self._compute_scenario_hash(sc)
                if sc_hash in seen_hashes:
                    duplicate_count += 1
                    continue
                seen_hashes.add(sc_hash)

                valid_scenarios_by_strategy[strategy.id].append(sc)

        # 6. Apply limits with deterministic budget allocation (round-robin)
        selected_scenarios = self._allocate_budget(valid_scenarios_by_strategy)

        # Sort the final selected scenarios deterministically to guarantee stable order
        final_scenarios = sorted(
            selected_scenarios,
            key=lambda sc: (sc.attack_type.value if sc.attack_type else "", sc.id),
        )

        # 7. Calculate coverage metadata based ON ACTUAL FINAL SCENARIOS
        strategy_coverage = self._calculate_strategy_coverage(relevant_strategies, final_scenarios)
        risk_coverage = self._calculate_risk_coverage(risk_profile, final_scenarios, agent)
        attack_surface_coverage = self._calculate_attack_surface_coverage(risk_profile, final_scenarios, agent)

        # 8. Assemble ChallengePack
        scenario_ids = [sc.id for sc in final_scenarios]
        pack_id = self._generate_deterministic_pack_id(agent.id, agent.version, scenario_ids)

        generation_metadata = {
            "total_generated": total_generated_count,
            "valid_count": len(final_scenarios),
            "invalid_count": len(invalid_scenarios_info),
            "duplicate_count": duplicate_count,
            "exclusions": invalid_scenarios_info,
            "limits": self.config.model_dump(),
        }

        # Build ChallengePack metadata
        metadata = {
            "generation_metadata": generation_metadata,
        }

        pack = ChallengePack(
            id=pack_id,
            name=f"Challenge Pack for {agent.name}",
            description=f"Adversarial test suite targeting agent {agent.id} (version {agent.version})",
            agent_id=agent.id,
            agent_version=agent.version,
            scenarios=final_scenarios,
            version="1.0.0",
            metadata=metadata,
            strategy_coverage=strategy_coverage,
            risk_coverage=risk_coverage,
            attack_surface_coverage=attack_surface_coverage,
        )

        return pack

    def _compute_scenario_hash(self, scenario: Scenario) -> str:
        """
        Compute a SHA-256 hash representing the stable semantic content of the scenario.
        Includes strategy, target tool, target risk, conversation input turns, and expected behavior.
        """
        attack_type = scenario.attack_type.value if scenario.attack_type else "none"
        target_tool = scenario.metadata.get("target_tool") or "none"
        target_risk = scenario.target_risk or "none"
        
        # Turn inputs
        turns_data = []
        for turn in scenario.turns:
            turns_data.append((turn.role, turn.content))
        turns_str = json.dumps(turns_data, sort_keys=True)
        initial_message = scenario.initial_message or ""
        
        # Expected behavior
        eb = scenario.expected_behavior
        eb_data = {
            "description": eb.description,
            "should_refuse": eb.should_refuse,
            "allowed_tools": sorted(eb.allowed_tools),
            "forbidden_tools": sorted(eb.forbidden_tools),
            "required_tools": sorted(eb.required_tools),
            "validators": sorted(eb.validators),
            "rules": sorted(eb.rules),
        }
        eb_str = json.dumps(eb_data, sort_keys=True)
        
        # Combine everything to create a stable hash
        hasher = hashlib.sha256()
        hasher.update(attack_type.encode("utf-8"))
        hasher.update(target_tool.encode("utf-8"))
        hasher.update(target_risk.encode("utf-8"))
        hasher.update(initial_message.encode("utf-8"))
        hasher.update(turns_str.encode("utf-8"))
        hasher.update(eb_str.encode("utf-8"))
        
        return hasher.hexdigest()

    def _allocate_budget(
        self,
        scenarios_by_strategy: dict[str, list[Scenario]],
    ) -> list[Scenario]:
        """
        Fair-share budget allocation (round-robin) across strategies.
        Ensures max_total_scenarios is not exceeded and respects max_scenarios_per_strategy.
        """
        # 1. Apply max_scenarios_per_strategy first
        limited_scenarios: dict[str, list[Scenario]] = {}
        for strategy_id, sc_list in scenarios_by_strategy.items():
            limited_scenarios[strategy_id] = sc_list[:self.config.max_scenarios_per_strategy]

        # 2. Round-robin select up to max_total_scenarios
        selected: list[Scenario] = []
        strategy_ids = sorted(limited_scenarios.keys())
        
        # Keep track of working lists (copied to avoid mutating the original dict)
        working_lists = {sid: list(lst) for sid, lst in limited_scenarios.items()}

        while len(selected) < self.config.max_total_scenarios:
            added_any = False
            for sid in strategy_ids:
                if len(selected) >= self.config.max_total_scenarios:
                    break
                if working_lists[sid]:
                    selected.append(working_lists[sid].pop(0))
                    added_any = True
            if not added_any:
                break

        return selected

    def _generate_deterministic_pack_id(
        self,
        agent_id: str,
        agent_version: str,
        scenario_ids: list[str],
    ) -> str:
        """
        Generate a stable SHA-256 hash as the ChallengePack ID.
        """
        config_dict = self.config.model_dump()
        inputs = [
            agent_id,
            agent_version,
            ",".join(sorted(scenario_ids)),
            json.dumps(config_dict, sort_keys=True),
        ]
        hash_input = ":".join(inputs).encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()

    def _calculate_strategy_coverage(
        self,
        relevant_strategies: list[AttackStrategy],
        final_scenarios: list[Scenario],
    ) -> dict[str, bool]:
        """
        Strategy coverage map: selected strategy ID -> whether it exists in final scenarios.
        """
        covered_strategy_ids = {sc.attack_type.value for sc in final_scenarios if sc.attack_type}
        
        coverage_map = {}
        for strategy in relevant_strategies:
            coverage_map[strategy.id] = strategy.id in covered_strategy_ids
        return coverage_map

    def _calculate_risk_coverage(
        self,
        risk_profile: RiskProfile,
        final_scenarios: list[Scenario],
        agent: Agent,
    ) -> dict[str, bool]:
        """
        Risk coverage map: identified risk name -> whether it is addressed by final scenarios.
        """
        meaningful_risks = set()
        
        # High-level risk categories based on tools and indicators
        has_destructive = len(risk_profile.destructive_tools) > 0
        has_sensitive = len(risk_profile.sensitive_tools) > 0
        
        has_financial = any(ind.name == "financial_tools_present" for ind in risk_profile.risk_indicators)
        has_communication = any(ind.name == "communication_tools_present" for ind in risk_profile.risk_indicators)
        has_authorization = (
            "authority_spoofing" in risk_profile.evidence
            or any("privilege" in ind.name or "auth" in ind.name for ind in risk_profile.risk_indicators)
            or any(ase.attack_surface == "authority_spoofing" for ase in risk_profile.attack_surfaces)
        )
            
        if has_destructive:
            meaningful_risks.add("destructive")
        if has_sensitive:
            meaningful_risks.add("sensitive")
        if has_financial:
            meaningful_risks.add("financial")
        if has_communication:
            meaningful_risks.add("communication")
        if has_authorization:
            meaningful_risks.add("authorization")

            
        for ind in risk_profile.risk_indicators:
            meaningful_risks.add(ind.name)
            
        # Determine which meaningful risks have at least one scenario
        covered_risks = set()
        for sc in final_scenarios:
            target_tool_name = sc.metadata.get("target_tool")
            target_tool = next((t for t in agent.tools if t.name == target_tool_name), None)
            tool_cats = ToolClassifier.classify_tool(target_tool) if target_tool else []
            
            # Destructive
            if ToolCapability.DESTRUCTIVE in tool_cats or sc.target_risk in risk_profile.destructive_tools:
                covered_risks.add("destructive")
                covered_risks.add("destructive_tools_present")
                
            # Financial
            if ToolCapability.FINANCIAL in tool_cats:
                covered_risks.add("financial")
                covered_risks.add("financial_tools_present")
                
            # Communication
            if ToolCapability.COMMUNICATION in tool_cats:
                covered_risks.add("communication")
                covered_risks.add("communication_tools_present")
                
            # Sensitive
            if ToolCapability.DATA_ACCESS in tool_cats or sc.target_risk in risk_profile.sensitive_tools:
                covered_risks.add("sensitive")
                covered_risks.add("sensitive_data_access")
                
            # Authorization
            if sc.attack_type in (
                AttackStrategyType.AUTHORITY_SPOOFING,
                AttackStrategyType.AUTHORIZATION_BYPASS,
                AttackStrategyType.PRIVILEGE_ESCALATION,
                AttackStrategyType.MULTI_TURN_MANIPULATION,
            ):
                covered_risks.add("authorization")
                
            # Urgency Pressure
            if sc.attack_type == AttackStrategyType.URGENCY_PRESSURE:
                covered_risks.add("urgency_susceptibility")
                
        coverage_map = {}
        for risk in sorted(meaningful_risks):
            coverage_map[risk] = risk in covered_risks
        return coverage_map

    def _calculate_attack_surface_coverage(
        self,
        risk_profile: RiskProfile,
        final_scenarios: list[Scenario],
        agent: Agent,
    ) -> dict[str, bool]:
        """
        Attack surface coverage: identified attack surface -> whether it is addressed by final scenarios.
        """
        profiled_surfaces = {ase.attack_surface for ase in risk_profile.attack_surfaces}
        
        covered_surfaces = set()
        for sc in final_scenarios:
            if sc.attack_type:
                covered_surfaces.add(sc.attack_type.value)
                
            target_tool_name = sc.metadata.get("target_tool")
            target_tool = next((t for t in agent.tools if t.name == target_tool_name), None)
            if target_tool:
                cats = ToolClassifier.classify_tool(target_tool)
                if ToolCapability.DESTRUCTIVE in cats:
                    covered_surfaces.add("destructive_action_restrictions")
                    
        coverage_map = {}
        for surface in sorted(profiled_surfaces):
            coverage_map[surface] = surface in covered_surfaces
        return coverage_map
