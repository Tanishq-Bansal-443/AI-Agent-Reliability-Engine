"""
Adaptive Regression Intelligence Analyzer.
"""

from __future__ import annotations

import hashlib
from typing import Any

from packages.core.models.scenario import AttackStrategy, AttackStrategyType, RiskLevel, ChallengePack, Scenario
from packages.core.models.agent import Tool, ToolCapability
from packages.core.models.evaluation import ChallengePackEvaluationResult, EvaluationVerdict, Severity
from packages.core.models.reliability import ReliabilityAssessment, ReliabilityFinding
from packages.core.models.regression import RegressionFinding, RegressionReport, FailureChangeType
from packages.core.models.adaptive import AdaptivePriority, AdaptiveRecommendation, AdaptiveTestPlan
from packages.scenario_engine.attack_strategy import AttackStrategyRegistry
from packages.profiler.base import ToolClassifier


def _matches_strategy(
    strategy_id: str,
    category: str,
    attack_surfaces: list[str],
    title: str,
    description: str,
) -> bool:
    """
    Deterministically determines if a finding maps to a given strategy ID.
    """
    # 1. Direct match on strategy ID in attack surfaces
    if strategy_id in attack_surfaces:
        return True
    
    # 2. Normalize and check category
    strategy_id_clean = strategy_id.lower().replace("_", "").replace("-", "")
    category_clean = category.lower().replace("_", "").replace("-", "")
    if strategy_id_clean in category_clean or category_clean in strategy_id_clean:
        return True

    # 3. Check title/description
    title_clean = title.lower()
    desc_clean = description.lower()
    strategy_id_spaced = strategy_id.lower().replace("_", " ").replace("-", " ")
    
    if strategy_id_spaced in title_clean or strategy_id in title_clean:
        return True
    if strategy_id_spaced in desc_clean or strategy_id in desc_clean:
        return True
        
    return False


def _generate_recommendation_id(
    strategy_id: str | None,
    target_tool: str | None,
    title: str,
    description: str,
    recommended_action: str,
) -> str:
    """
    Generate a stable, deterministic hash ID for a recommendation.
    """
    content = f"{strategy_id or ''}:{target_tool or ''}:{title}:{description}:{recommended_action}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AdaptiveRegressionAnalyzer:
    """
    Analyzes historical assessments, regression reports, and evaluations
    to adaptively build future test plans and prioritize attack strategies.
    """

    def build_test_plan(
        self,
        current_assessment: ReliabilityAssessment,
        regression_report: RegressionReport | None = None,
        current_evaluation: ChallengePackEvaluationResult | None = None,
        challenge_pack: ChallengePack | None = None,
        budget: int = 10,
    ) -> AdaptiveTestPlan:
        """
        Builds the deterministic AdaptiveTestPlan.
        """
        agent_id = current_assessment.agent_id
        agent_version = current_assessment.agent_version
        source_run_id = current_assessment.run_id
        prior_run_id = regression_report.previous_run_id if regression_report else None

        # 1. Identify all tools referenced in the active session
        all_tools: set[str] = set()
        for finding in current_assessment.findings:
            all_tools.update(finding.affected_tools)
        if regression_report:
            for finding in (
                regression_report.new_failures
                + regression_report.persistent_failures
                + regression_report.severity_changes
                + regression_report.fixed_failures
            ):
                all_tools.update(finding.current_tools)
                all_tools.update(finding.previous_tools)
        if challenge_pack:
            for sc in challenge_pack.scenarios:
                tool_name = sc.metadata.get("target_tool") or sc.target_risk
                if tool_name:
                    all_tools.add(tool_name)

        # Classify tools using existing ToolClassifier
        has_destructive_tool = False
        has_financial_tool = False
        has_auth_tool = False

        for t_name in sorted(list(all_tools)):
            dummy_tool = Tool(name=t_name, description="", parameters=[], destructive=False, sensitive=False)
            cats = ToolClassifier.classify_tool(dummy_tool)
            if ToolCapability.DESTRUCTIVE in cats:
                has_destructive_tool = True
            if ToolCapability.FINANCIAL in cats:
                has_financial_tool = True
            if ToolCapability.AUTHORIZATION in cats:
                has_auth_tool = True

        # 2. Iterate and calculate priorities for all registered strategies
        strategies = AttackStrategyRegistry.list_strategies()
        # Sort strategies by ID to ensure deterministic iteration
        strategies = sorted(strategies, key=lambda s: s.id)

        priorities: list[AdaptivePriority] = []

        for strategy in strategies:
            strat_id = strategy.id
            strat_bonuses: list[tuple[str, float]] = []
            strat_evidence: list[str] = []

            # A. NEW failure (+35)
            if regression_report:
                has_new = any(
                    _matches_strategy(strat_id, f.category, f.attack_surfaces, f.title, f.description)
                    for f in regression_report.new_failures
                )
                if has_new:
                    strat_bonuses.append(("NEW failure", 35.0))
                    strat_evidence.append("New failure detected on strategy.")

            # B. HIGH/CRITICAL severity increase (+30)
            if regression_report:
                has_sev_inc = any(
                    _matches_strategy(strat_id, f.category, f.attack_surfaces, f.title, f.description)
                    and f.change_type == FailureChangeType.SEVERITY_INCREASED
                    and f.current_severity in ("high", "critical")
                    for f in regression_report.severity_changes
                )
                if has_sev_inc:
                    strat_bonuses.append(("HIGH/CRITICAL severity increase", 30.0))
                    strat_evidence.append("Failure severity increased to HIGH/CRITICAL.")

            # C. PERSISTED failure (+20)
            has_persisted = False
            if regression_report:
                has_persisted = any(
                    _matches_strategy(strat_id, f.category, f.attack_surfaces, f.title, f.description)
                    for f in regression_report.persistent_failures
                )
            else:
                # Fallback to current assessment active findings if no report
                has_persisted = any(
                    _matches_strategy(strat_id, f.category, f.attack_surfaces, f.title, f.description)
                    for f in current_assessment.findings
                )

            if has_persisted:
                strat_bonuses.append(("PERSISTED failure", 20.0))
                strat_evidence.append("Persistent/active failure on strategy.")

            # D. Previously uncovered surface (+20)
            has_uncovered_surface = False
            for surf in current_assessment.uncovered_attack_surfaces:
                if surf in strategy.target_attack_surfaces or surf == strat_id:
                    has_uncovered_surface = True
            if challenge_pack:
                for surf, covered in challenge_pack.attack_surface_coverage.items():
                    if not covered and (surf in strategy.target_attack_surfaces or surf == strat_id):
                        has_uncovered_surface = True
            
            if has_uncovered_surface:
                strat_bonuses.append(("Previously uncovered surface", 20.0))
                strat_evidence.append("Strategy targets an uncovered attack surface.")

            # E. Previously uncovered strategy (+15)
            has_uncovered_strat = strat_id in current_assessment.uncovered_strategies
            if challenge_pack and strat_id in challenge_pack.strategy_coverage:
                if not challenge_pack.strategy_coverage[strat_id]:
                    has_uncovered_strat = True
            
            if has_uncovered_strat:
                strat_bonuses.append(("Previously uncovered strategy", 15.0))
                strat_evidence.append("Strategy was previously uncovered.")

            # F. Destructive capability bonus (+10)
            is_destructive_associated = strat_id in (
                AttackStrategyType.CONFIRMATION_BYPASS.value,
                AttackStrategyType.AUTHORIZATION_BYPASS.value,
                AttackStrategyType.AUTHORITY_SPOOFING.value,
                AttackStrategyType.URGENCY_PRESSURE.value,
                AttackStrategyType.AMBIGUITY_EXPLOITATION.value,
                AttackStrategyType.TOOL_MISUSE.value,
            )
            if has_destructive_tool and is_destructive_associated:
                strat_bonuses.append(("Destructive capability", 10.0))
                strat_evidence.append("Agent has destructive tools capability.")

            # G. Financial capability bonus (+10)
            is_financial_associated = strat_id in (
                AttackStrategyType.CONFIRMATION_BYPASS.value,
                AttackStrategyType.AUTHORIZATION_BYPASS.value,
                AttackStrategyType.AUTHORITY_SPOOFING.value,
                AttackStrategyType.URGENCY_PRESSURE.value,
                AttackStrategyType.AMBIGUITY_EXPLOITATION.value,
                AttackStrategyType.TOOL_MISUSE.value,
            )
            if has_financial_tool and is_financial_associated:
                strat_bonuses.append(("Financial capability", 10.0))
                strat_evidence.append("Agent has financial tools capability.")

            # H. Authorization-sensitive bonus (+10)
            is_auth_associated = strat_id in (
                AttackStrategyType.AUTHORITY_SPOOFING.value,
                AttackStrategyType.AUTHORIZATION_BYPASS.value,
                AttackStrategyType.PRIVILEGE_ESCALATION.value,
                AttackStrategyType.MULTI_TURN_MANIPULATION.value,
            )
            if has_auth_tool and is_auth_associated:
                strat_bonuses.append(("Authorization-sensitive", 10.0))
                strat_evidence.append("Agent has authorization tools capability.")

            # I. Multiple affected scenarios (+5)
            # Count scenarios evaluated/failed for this strategy
            affected_scenario_ids: set[str] = set()
            for finding in current_assessment.findings:
                if _matches_strategy(strat_id, finding.category, finding.attack_surfaces, finding.title, finding.description):
                    affected_scenario_ids.update(finding.affected_scenarios)
            if regression_report:
                for finding in (
                    regression_report.new_failures
                    + regression_report.persistent_failures
                    + regression_report.severity_changes
                ):
                    if _matches_strategy(strat_id, finding.category, finding.attack_surfaces, finding.title, finding.description):
                        affected_scenario_ids.update(finding.current_scenarios)
                        affected_scenario_ids.update(finding.previous_scenarios)
            if current_evaluation:
                for res in current_evaluation.scenario_results:
                    if res.verdict == EvaluationVerdict.FAIL:
                        # Find corresponding scenario strategy if possible
                        sc_strat = None
                        if challenge_pack:
                            sc = next((s for s in challenge_pack.scenarios if s.id == res.scenario_id), None)
                            if sc and sc.attack_type:
                                sc_strat = sc.attack_type.value
                        if sc_strat == strat_id:
                            affected_scenario_ids.add(res.scenario_id)

            if len(affected_scenario_ids) > 1:
                strat_bonuses.append(("Multiple affected scenarios", 5.0))
                strat_evidence.append(f"Multiple failed scenarios ({len(affected_scenario_ids)}) associated with strategy.")

            # Calculate total score and clamp/normalize to [0, 100]
            raw_score = sum(val for name, val in strat_bonuses)
            priority_score = min(100.0, max(0.0, float(raw_score)))

            # Expose reasoning
            if strat_bonuses:
                bonus_strings = [f"{name} (+{val})" for name, val in strat_bonuses]
                reason = f"Priority calculated from: {', '.join(bonus_strings)}."
            else:
                reason = "Strategy has no active failures or vulnerability indicators."

            # Determine risk level from score
            if priority_score >= 80.0:
                risk_level = RiskLevel.CRITICAL
            elif priority_score >= 50.0:
                risk_level = RiskLevel.HIGH
            elif priority_score >= 20.0:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            priorities.append(AdaptivePriority(
                strategy_id=strat_id,
                priority_score=priority_score,
                risk_level=risk_level,
                reason=reason,
                evidence=sorted(list(set(strat_evidence))),
                recommended_scenario_count=0,
                metadata={"bonuses": {name: val for name, val in strat_bonuses}},
            ))

        # 3. Budget Allocation using deterministic Largest Remainder Method
        relevant_priorities = [p for p in priorities if p.priority_score > 0.0]
        # Sort relevant priorities: score descending, then strategy_id ascending
        relevant_priorities = sorted(relevant_priorities, key=lambda p: (-p.priority_score, p.strategy_id))
        k = len(relevant_priorities)

        if budget <= 0 or k == 0:
            allocations = {p.strategy_id: 0 for p in priorities}
        elif budget <= k:
            # Budget is tight: allocate 1 to top B strategies, 0 to rest
            allocations = {p.strategy_id: 0 for p in priorities}
            for i in range(min(budget, k)):
                allocations[relevant_priorities[i].strategy_id] = 1
        else:
            # Budget is larger than k: everyone gets at least 1, distribute rest proportionally
            allocations = {p.strategy_id: 0 for p in priorities}
            for p in relevant_priorities:
                allocations[p.strategy_id] = 1

            remaining_budget = budget - k
            priority_sum = sum(p.priority_score for p in relevant_priorities)

            shares = []
            floors_sum = 0
            for p in relevant_priorities:
                share = remaining_budget * (p.priority_score / priority_sum)
                floor_val = int(share)
                floors_sum += floor_val
                shares.append((p.strategy_id, share, floor_val, share - floor_val))

            # Distribute floors
            for sid, _, floor_val, _ in shares:
                allocations[sid] += floor_val

            # Distribute remainder using largest fractional part with tie-breaker
            undistributed = remaining_budget - floors_sum
            # Sort by fractional part descending, strategy_id ascending
            shares_sorted = sorted(shares, key=lambda x: (-x[3], x[0]))

            for i in range(undistributed):
                allocations[shares_sorted[i][0]] += 1

        # Populate recommended_scenario_count in priorities
        for p in priorities:
            p.recommended_scenario_count = allocations[p.strategy_id]

        selected_strategies = sorted([p.strategy_id for p in priorities if allocations[p.strategy_id] > 0])

        # 4. Coverage Gap Detection
        coverage_gaps: list[str] = []

        # A. Strategy gaps
        for strat_id in current_assessment.uncovered_strategies:
            coverage_gaps.append(f"strategy_gap:{strat_id}")
        if challenge_pack:
            for strat_id, covered in sorted(challenge_pack.strategy_coverage.items()):
                if not covered:
                    gap_str = f"strategy_gap:{strat_id}"
                    if gap_str not in coverage_gaps:
                        coverage_gaps.append(gap_str)

        # B. Risk gaps
        if challenge_pack:
            for risk_name, covered in sorted(challenge_pack.risk_coverage.items()):
                if not covered:
                    coverage_gaps.append(f"risk_gap:{risk_name}")

        # C. Attack-surface gaps
        for surf in current_assessment.uncovered_attack_surfaces:
            coverage_gaps.append(f"attack_surface_gap:{surf}")
        if challenge_pack:
            for surf, covered in sorted(challenge_pack.attack_surface_coverage.items()):
                if not covered:
                    gap_str = f"attack_surface_gap:{surf}"
                    if gap_str not in coverage_gaps:
                        coverage_gaps.append(gap_str)

        # D. Regression gaps: previously problematic strategy has fewer than 2 evaluated scenarios
        # Count evaluated scenarios per strategy
        evaluated_scenarios_count: dict[str, int] = {s.id: 0 for s in strategies}
        if challenge_pack:
            for sc in challenge_pack.scenarios:
                if sc.attack_type:
                    evaluated_scenarios_count[sc.attack_type.value] += 1
        elif current_evaluation:
            # Fallback to current evaluation
            for res in current_evaluation.scenario_results:
                if res.was_evaluated:
                    # Lookup strategy if possible
                    pass

        # Identify previously problematic strategies
        problematic_strategies: set[str] = set()
        if regression_report:
            for finding in (
                regression_report.new_failures
                + regression_report.persistent_failures
                + regression_report.fixed_failures
            ):
                for strategy in strategies:
                    if _matches_strategy(strategy.id, finding.category, finding.attack_surfaces, finding.title, finding.description):
                        problematic_strategies.add(strategy.id)

        for strat_id in sorted(list(problematic_strategies)):
            if evaluated_scenarios_count[strat_id] < 2:
                coverage_gaps.append(f"regression_gap:{strat_id}")

        coverage_gaps = sorted(list(set(coverage_gaps)))

        # 5. Recommendations Generation
        recommendations: list[AdaptiveRecommendation] = []
        seen_rec_signatures: set[str] = set()

        for p in priorities:
            if p.priority_score <= 0.0:
                continue

            strat_id = p.strategy_id
            priority_val = p.priority_score

            # Tool target mapping for recommendation details
            matching_tools = set()
            for finding in current_assessment.findings:
                if _matches_strategy(strat_id, finding.category, finding.attack_surfaces, finding.title, finding.description):
                    matching_tools.update(finding.affected_tools)

            target_tool = sorted(list(matching_tools))[0] if matching_tools else None

            # Generate recommendations depending on priority state
            if f"regression_gap:{strat_id}" in coverage_gaps:
                title = f"Expand testing of problematic strategy: {strat_id}"
                description = f"Strategy '{strat_id}' was previously problematic but has insufficient scenario coverage."
                recommended_action = f"Add at least {2 - evaluated_scenarios_count.get(strat_id, 0)} scenarios targeting '{strat_id}'."
                reason = "Regression gap identified with insufficient historical verification."
            elif strat_id == AttackStrategyType.AUTHORITY_SPOOFING.value and target_tool:
                title = f"Increase authority spoofing coverage against {target_tool}"
                description = f"Agent failed to reject spoofed administrator requests when calling '{target_tool}'."
                recommended_action = f"Inject administrative impersonation prompts before invoking '{target_tool}'."
                reason = "Authority spoofing vulnerabilities detected on high-impact tools."
            elif strat_id == AttackStrategyType.CONFIRMATION_BYPASS.value:
                title = "Add scenarios for uncovered confirmation controls"
                description = "Agent executed irreversible operations without explicit confirmation constraints."
                recommended_action = "Incorporate required confirmation validation checks in test scenarios."
                reason = "Confirmation controls were bypassed in execution traces."
            elif p.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                title = f"Retest persistent failures for strategy: {strat_id}"
                description = f"High-risk vulnerability detected on strategy '{strat_id}'."
                recommended_action = f"Remediate prompt constraints and re-evaluate strategy '{strat_id}'."
                reason = "Persistent failure findings remain unresolved."
            else:
                title = f"Validate instructions boundaries on {strat_id}"
                description = f"Review agent safety and instruction following under strategy '{strat_id}'."
                recommended_action = f"Retest {strat_id} with diverse prompt configurations."
                reason = "Continuous regression tracking recommendation."

            sig = f"{strat_id}:{target_tool or ''}:{title}"
            if sig not in seen_rec_signatures:
                seen_rec_signatures.add(sig)
                rec_id = _generate_recommendation_id(
                    strategy_id=strat_id,
                    target_tool=target_tool,
                    title=title,
                    description=description,
                    recommended_action=recommended_action,
                )
                recommendations.append(AdaptiveRecommendation(
                    id=rec_id,
                    strategy_id=strat_id,
                    target_tool=target_tool,
                    title=title,
                    description=description,
                    priority=priority_val,
                    reason=reason,
                    recommended_action=recommended_action,
                    metadata={"strategy_priority": priority_val},
                ))

        # Sort recommendations: priority descending, title ascending, id ascending
        recommendations = sorted(recommendations, key=lambda r: (-r.priority, r.title, r.id))

        # Generate summary reasoning explanation
        num_selected = len(selected_strategies)
        summary = (
            f"Adaptive planner prioritized {num_selected} attack strategies with total budget {budget}. "
            f"Top priority strategy is '{relevant_priorities[0].strategy_id}' with score {relevant_priorities[0].priority_score:.1f} "
            f"due to: {relevant_priorities[0].reason}"
            if num_selected > 0 else f"No active priorities identified. General test pack recommended with budget {budget}."
        )

        return AdaptiveTestPlan(
            agent_id=agent_id,
            agent_version=agent_version,
            source_run_id=source_run_id,
            prior_run_id=prior_run_id,
            budget=budget,
            selected_strategies=selected_strategies,
            strategy_priorities=priorities,
            recommendations=recommendations,
            coverage_gaps=coverage_gaps,
            reasoning_summary=summary,
            metadata={"total_strategies": len(strategies), "budget_allocated": budget},
        )
