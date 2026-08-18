"""
Demo Customer Support Agent package.

A deliberately vulnerable customer-support agent for testing
the AI Agent Reliability Engine.

The agent is intentionally susceptible to authority spoofing and urgency attacks.
This vulnerability is NOT hardcoded into the evaluator — it arises from
the agent's behavior and is detected by the evaluation pipeline.
"""

from agents.demo_customer_support.agent import DemoCustomerSupportAgent
from agents.demo_customer_support.adapter import DemoAgentAdapter
from agents.demo_customer_support.tools import CUSTOMER_SUPPORT_TOOLS

__all__ = ["DemoCustomerSupportAgent", "DemoAgentAdapter", "CUSTOMER_SUPPORT_TOOLS"]
