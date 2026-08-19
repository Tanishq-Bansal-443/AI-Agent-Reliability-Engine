import pytest
from packages.core.models.scenario import AttackStrategy, AttackStrategyType, RiskLevel
from packages.core.models.agent import RiskProfile, Capability, AttackSurfaceEvidence, RiskIndicator
from packages.scenario_engine.attack_strategy import AttackStrategyRegistry


class TestAttackStrategyLibrary:
    """Focused tests for the Attack Strategy Library."""

    def test_strategy_model_validation(self) -> None:
        # 1. Strategy model validation (Pydantic instantiation, serialization, defaults)
        strategy = AttackStrategy(
            id="test_strategy",
            name="Test Strategy Name",
            description="Detailed description here.",
            target_risks=["risk1", "risk2"],
            target_attack_surfaces=["surface1"],
            generation_guidance="Generate this way.",
            expected_failure_modes=["failure1"],
            default_severity=RiskLevel.MEDIUM,
        )
        assert strategy.id == "test_strategy"
        assert strategy.default_severity == RiskLevel.MEDIUM
        
        # Check Pydantic serialization
        serialized = strategy.model_dump()
        assert serialized["id"] == "test_strategy"
        assert serialized["default_severity"] == "medium"
        
        # Check deserialization
        deserialized = AttackStrategy.model_validate(serialized)
        assert deserialized.name == "Test Strategy Name"

    def test_registry_contains_all_initial_strategies(self) -> None:
        # 2. Registry contains all 11 initial strategies
        strategies = AttackStrategyRegistry.list_strategies()
        assert len(strategies) == 11
        
        expected_ids = {
            "authority_spoofing",
            "urgency_pressure",
            "authorization_bypass",
            "confirmation_bypass",
            "privilege_escalation",
            "prompt_injection",
            "instruction_conflict",
            "ambiguity_exploitation",
            "tool_misuse",
            "data_exfiltration",
            "multi_turn_manipulation",
        }
        
        strategy_ids = {s.id for s in strategies}
        assert strategy_ids == expected_ids

    def test_lookup_by_strategy_id(self) -> None:
        # 3. Lookup by strategy ID
        strategy = AttackStrategyRegistry.get_strategy("authority_spoofing")
        assert strategy is not None
        assert strategy.id == "authority_spoofing"
        assert strategy.name == "Authority / Identity Spoofing"
        
        # Test lookup by Enum member
        strategy_enum = AttackStrategyRegistry.get_strategy(AttackStrategyType.URGENCY_PRESSURE)
        assert strategy_enum is not None
        assert strategy_enum.id == "urgency_pressure"
        
        # Test invalid lookup
        assert AttackStrategyRegistry.get_strategy("non_existent_id") is None

    def test_relevant_strategy_selection(self) -> None:
        # 4. Relevant strategy selection (explicit attack surface)
        profile = RiskProfile(
            agent_id="test-agent",
            attack_surfaces=[
                AttackSurfaceEvidence(attack_surface="authority_spoofing", reason="Prompt requests supervisor login.")
            ],
        )
        relevant = AttackStrategyRegistry.find_relevant_strategies(profile)
        relevant_ids = {s.id for s in relevant}
        assert "authority_spoofing" in relevant_ids
        
        # Check explanation
        with_reasons = AttackStrategyRegistry.find_relevant_strategies_with_reasons(profile)
        explanation = next(reason for strat, reason in with_reasons if strat.id == "authority_spoofing")
        assert explanation == "matched attack surface: authority_spoofing"

    def test_irrelevant_strategy_exclusion(self) -> None:
        # 5. Irrelevant strategy exclusion (does not automatically select unrelated strategies)
        profile = RiskProfile(
            agent_id="test-agent",
            attack_surfaces=[
                AttackSurfaceEvidence(attack_surface="authority_spoofing", reason="Prompt requests supervisor login.")
            ],
            destructive_tools=[],
            sensitive_tools=[],
        )
        relevant = AttackStrategyRegistry.find_relevant_strategies(profile)
        relevant_ids = {s.id for s in relevant}
        
        # Should include authority_spoofing but exclude data exfiltration or prompt injection
        assert "authority_spoofing" in relevant_ids
        assert "data_exfiltration" not in relevant_ids
        assert "prompt_injection" not in relevant_ids

    def test_authority_spoofing_selection(self) -> None:
        # 6. Authority spoofing selection (financial/destructive + authorization characteristics)
        profile = RiskProfile(
            agent_id="test-agent",
            capabilities=[
                Capability(
                    name="can_refund",
                    description="Allows executing authorization-sensitive refunds.",
                    related_tools=["refund_order"],
                )
            ],
            destructive_tools=["refund_order"],
        )
        with_reasons = AttackStrategyRegistry.find_relevant_strategies_with_reasons(profile)
        relevant_ids = {s.id for s, _ in with_reasons}
        
        # Should select authority_spoofing and authorization_bypass due to credentials/authorization capability
        assert "authority_spoofing" in relevant_ids
        assert "authorization_bypass" in relevant_ids
        
        # Verify matching reason
        auth_reason = next(reason for strat, reason in with_reasons if strat.id == "authority_spoofing")
        bypass_reason = next(reason for strat, reason in with_reasons if strat.id == "authorization_bypass")
        assert auth_reason == "matched authorization-sensitive + destructive capability"
        assert bypass_reason == "matched authorization-sensitive + destructive capability"

    def test_destructive_financial_risk_selection(self) -> None:
        # 7. Destructive/financial risk selection
        profile = RiskProfile(
            agent_id="test-agent",
            destructive_tools=["refund_order"],
            capabilities=[
                Capability(
                    name="can_refund",
                    description="Allows financial transactions.",
                    related_tools=["refund_order"],
                )
            ],
        )
        with_reasons = AttackStrategyRegistry.find_relevant_strategies_with_reasons(profile)
        relevant_ids = {s.id for s, _ in with_reasons}
        
        # Should select confirmation_bypass and urgency_pressure
        assert "confirmation_bypass" in relevant_ids
        assert "urgency_pressure" in relevant_ids
        
        confirm_reason = next(reason for strat, reason in with_reasons if strat.id == "confirmation_bypass")
        urgency_reason = next(reason for strat, reason in with_reasons if strat.id == "urgency_pressure")
        
        assert confirm_reason == "matched destructive tool: refund_order"
        assert urgency_reason == "matched urgency vector on high-impact tools"

    def test_data_access_risk_selection(self) -> None:
        # 8. Data-access risk selection
        profile = RiskProfile(
            agent_id="test-agent",
            sensitive_tools=["get_customer_db"],
            capabilities=[
                Capability(
                    name="can_read_db",
                    description="Allows data access to backend customer records.",
                    related_tools=["get_customer_db"],
                )
            ],
        )
        with_reasons = AttackStrategyRegistry.find_relevant_strategies_with_reasons(profile)
        relevant_ids = {s.id for s, _ in with_reasons}
        
        assert "data_exfiltration" in relevant_ids
        exfil_reason = next(reason for strat, reason in with_reasons if strat.id == "data_exfiltration")
        assert exfil_reason == "matched sensitive tool: get_customer_db"

    def test_empty_risk_profile(self) -> None:
        # 9. Empty RiskProfile (conservative selection)
        profile = RiskProfile(
            agent_id="empty-agent",
            capabilities=[],
            attack_surfaces=[],
            destructive_tools=[],
            sensitive_tools=[],
            risk_indicators=[],
            evidence={},
        )
        relevant = AttackStrategyRegistry.find_relevant_strategies(profile)
        assert len(relevant) == 0

    def test_deterministic_repeatability(self) -> None:
        # 10. Deterministic repeatability
        profile = RiskProfile(
            agent_id="repeatable-agent",
            attack_surfaces=[
                AttackSurfaceEvidence(attack_surface="authority_spoofing", reason="Verification policy."),
                AttackSurfaceEvidence(attack_surface="urgency_pressure", reason="Urgency warnings.")
            ],
            destructive_tools=["delete_database"],
            sensitive_tools=["fetch_passwords"],
            capabilities=[
                Capability(
                    name="admin_actions",
                    description="Allows executing authorization actions and data access.",
                    related_tools=["delete_database", "fetch_passwords"],
                )
            ],
        )
        
        results1 = AttackStrategyRegistry.find_relevant_strategies_with_reasons(profile)
        results2 = AttackStrategyRegistry.find_relevant_strategies_with_reasons(profile)
        
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1[0].id == r2[0].id
            assert r1[1] == r2[1]
