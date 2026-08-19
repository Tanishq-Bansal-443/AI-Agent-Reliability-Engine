import pytest
from packages.core.models.agent import Agent, Tool, ToolCapability
from packages.profiler.base import StaticProfiler, ToolClassifier
from agents.demo_customer_support.adapter import DemoAgentAdapter


@pytest.mark.asyncio
class TestDeterministicProfiler:
    async def test_destructive_tool_detection(self) -> None:
        # 1. Destructive tool detection
        tool = Tool(
            name="delete_database",
            description="Deletes database tables.",
            destructive=True,
        )
        categories = ToolClassifier.classify_tool(tool)
        assert ToolCapability.DESTRUCTIVE in categories

        # Should also detect via keyword cancel/revoke/etc.
        tool_kw = Tool(
            name="cancel_subscription",
            description="Cancel a customer subscription.",
        )
        categories_kw = ToolClassifier.classify_tool(tool_kw)
        assert ToolCapability.DESTRUCTIVE in categories_kw

    async def test_financial_tool_detection(self) -> None:
        # 2. Financial tool detection
        tool = Tool(
            name="execute_transfer",
            description="Transfer money to another account.",
        )
        categories = ToolClassifier.classify_tool(tool)
        assert ToolCapability.FINANCIAL in categories

    async def test_communication_tool_detection(self) -> None:
        # 3. Communication tool detection
        tool = Tool(
            name="post_tweet",
            description="Post a status update to Twitter.",
        )
        categories = ToolClassifier.classify_tool(tool)
        assert ToolCapability.COMMUNICATION in categories

    async def test_read_only_tool_classification(self) -> None:
        # 4. Read-only tool classification
        tool = Tool(
            name="get_status",
            description="Read the status of a device.",
        )
        categories = ToolClassifier.classify_tool(tool)
        assert ToolCapability.READ_ONLY in categories
        assert ToolCapability.DESTRUCTIVE not in categories
        assert ToolCapability.FINANCIAL not in categories

    async def test_authorization_sensitive_detection(self) -> None:
        # 5. Authorization-sensitive detection
        tool = Tool(
            name="grant_admin_access",
            description="Grants admin role to user.",
        )
        categories = ToolClassifier.classify_tool(tool)
        assert ToolCapability.AUTHORIZATION in categories

    async def test_prompt_level_attack_surface_detection(self) -> None:
        # 6. Prompt-level attack-surface detection
        profiler = StaticProfiler()
        
        # Test authority spoofing
        agent_auth = Agent(
            id="test-auth",
            name="Auth Agent",
            system_prompt="Confirm identity before any actions. Verify administrator credentials.",
            tools=[],
        )
        profile_auth = await profiler.profile(agent_auth)
        attack_surfaces = [s.attack_surface for s in profile_auth.attack_surfaces]
        assert "authority_spoofing" in attack_surfaces

        # Test urgency susceptibility
        agent_urgency = Agent(
            id="test-urgency",
            name="Urgency Agent",
            system_prompt="Do not let users pressure you. Ignore urgency claims.",
            tools=[],
        )
        profile_urgency = await profiler.profile(agent_urgency)
        attack_surfaces_urgency = [s.attack_surface for s in profile_urgency.attack_surfaces]
        assert "urgency" in attack_surfaces_urgency

    async def test_demo_agent_profiling(self) -> None:
        # 7. Demo-agent profiling
        adapter = DemoAgentAdapter()
        agent = adapter.get_agent()
        profiler = StaticProfiler()
        profile = await profiler.profile(agent)

        # refund_order should be financial, destructive, authorization-sensitive
        refund_tool = next(t for t in agent.tools if t.name == "refund_order")
        refund_categories = ToolClassifier.classify_tool(refund_tool)
        assert ToolCapability.FINANCIAL in refund_categories
        assert ToolCapability.DESTRUCTIVE in refund_categories
        assert ToolCapability.AUTHORIZATION in refund_categories

        # send_email should be communication
        email_tool = next(t for t in agent.tools if t.name == "send_email")
        email_categories = ToolClassifier.classify_tool(email_tool)
        assert ToolCapability.COMMUNICATION in email_categories

        # get_order_status should be read-only
        status_tool = next(t for t in agent.tools if t.name == "get_order_status")
        status_categories = ToolClassifier.classify_tool(status_tool)
        assert ToolCapability.READ_ONLY in status_categories

        # Prompt-level analysis should identify authority_spoofing and urgency
        attack_surfaces = [s.attack_surface for s in profile.attack_surfaces]
        assert "authority_spoofing" in attack_surfaces
        assert "urgency" in attack_surfaces

    async def test_empty_minimal_agent(self) -> None:
        # 8. Empty/minimal agent
        agent = Agent(
            id="minimal-agent",
            name="Minimal Agent",
            system_prompt="Be a helpful assistant.",
            tools=[],
        )
        profiler = StaticProfiler()
        profile = await profiler.profile(agent)
        
        assert profile.agent_id == "minimal-agent"
        assert len(profile.capabilities) == 0
        assert len(profile.attack_surfaces) == 0
        assert len(profile.destructive_tools) == 0
        assert len(profile.sensitive_tools) == 0
        assert len(profile.risk_indicators) == 0

    async def test_unknown_tool_names(self) -> None:
        # 9. Unknown tool names
        tool = Tool(
            name="xyz_foo_bar",
            description="Does something completely unknown with no keywords.",
        )
        categories = ToolClassifier.classify_tool(tool)
        # Should classify as READ_ONLY because it has no side effects
        assert ToolCapability.READ_ONLY in categories

    async def test_deterministic_repeatability(self) -> None:
        # 10. Deterministic repeatability
        adapter = DemoAgentAdapter()
        agent = adapter.get_agent()
        profiler = StaticProfiler()
        
        profile1 = await profiler.profile(agent)
        profile2 = await profiler.profile(agent)
        
        d1 = profile1.model_dump()
        d2 = profile2.model_dump()
        d1.pop("profiled_at", None)
        d2.pop("profiled_at", None)
        
        assert d1 == d2
