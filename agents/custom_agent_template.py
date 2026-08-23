"""
Custom Python Agent Template — a template showing the minimum interface required.

To use your own Python agent, copy this file, implement the async `run` method,
and point the CLI to it:
    python -m packages.cli.main assess --agent-type python --agent-path agents/custom_agent_template.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile, RiskSurface, Tool, ToolParameter, ParameterType
from packages.sandbox.tool_runtime import ToolRuntime


class CustomAgentAdapter(BaseAgentAdapter):
    """
    Subclass BaseAgentAdapter and implement get_agent(), get_profile(), and run().
    """

    def get_agent(self) -> Agent:
        """
        Define your agent's identity, system prompt, and tools.
        """
        return Agent(
            id="custom_python_agent",
            name="Custom Python Agent",
            description="A template custom Python agent adapter.",
            system_prompt="You are a helpful assistant.",
            tools=[
                Tool(
                    name="get_order_status",
                    description="Check status of a customer order",
                    parameters=[
                        ToolParameter(
                            name="order_id",
                            type=ParameterType.STRING,
                            description="The order identifier, e.g. ORD-1001",
                            required=True
                        )
                    ]
                )
            ],
            version="1.0.0"
        )

    def get_profile(self) -> AgentProfile:
        """
        Define the risk capability profile.
        """
        agent = self.get_agent()
        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            description=agent.description,
            capabilities=[],
            tools=agent.tools,
            constraints=[],
            risk_surface=RiskSurface(
                tools=[t.name for t in agent.tools],
                capabilities=[],
                constraints=[],
                attack_families=["prompt_injection"]
            ),
            profiled_at=datetime.now(timezone.utc)
        )

    async def run(
        self,
        agent_input: AgentInput,
        runtime: ToolRuntime,
    ) -> AgentOutput:
        """
        Process the user input and return the agent's text response.

        CRITICAL SECURITY REQUIREMENT:
        All tool execution MUST go through the provided `runtime` object.
        Do not make direct/raw external API calls in your agent.
        """
        user_message = ""
        if agent_input.messages:
            user_message = agent_input.messages[-1].content

        # Example: call order status tool through sandboxed runtime
        # result = await runtime.execute("get_order_status", {"order_id": "ORD-4812"})

        # Implement your agent reasoning loop or API call here.
        # This template simply echoes the user input.
        response_text = f"Custom Python Agent received message: {user_message}"

        return AgentOutput(
            response=response_text,
            tool_calls_made=[],
            metadata={"processed_by": "CustomAgentAdapter"}
        )
