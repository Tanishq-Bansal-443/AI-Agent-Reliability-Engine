
from __future__ import annotations

import re
from abc import ABC, abstractmethod

from packages.core.models.agent import (
    Agent,
    RiskProfile,
    Capability,
    Constraint,
    Tool,
    ToolCapability,
    AttackSurfaceEvidence,
    RiskIndicator,
)
from packages.core.models.scenario import AttackStrategy


class BaseProfiler(ABC):
    """
    Abstract profiler that analyzes an Agent and produces a RiskProfile.

    The profile drives scenario generation and attack strategy selection.

    See ARCHITECTURE.md §6 for the full profiler architecture.
    """

    @abstractmethod
    async def profile(self, agent: Agent) -> RiskProfile:
        """
        Analyze an Agent and produce a structured RiskProfile.

        Args:
            agent: The agent to profile.

        Returns:
            RiskProfile describing the agent's capabilities and risk surface.
        """
        ...


class ToolClassifier:
    """Classifies tools into ToolCapability categories using deterministic rules."""

    CATEGORIES = {
        ToolCapability.DESTRUCTIVE: {
            "delete", "remove", "destroy", "cancel", "revoke", "terminate", "close"
        },
        ToolCapability.FINANCIAL: {
            "refund", "transfer", "payment", "charge", "purchase", "withdraw", "payout"
        },
        ToolCapability.COMMUNICATION: {
            "send_email", "send_message", "notify", "publish", "post", "email", "message", "sms"
        },
        ToolCapability.AUTHORIZATION: {
            "admin", "authorize", "permission", "role", "credential", "password", "access", "authentication", "auth", "login", "verify"
        },
        ToolCapability.DATA_ACCESS: {
            "customer", "user", "account", "database", "private", "sensitive", "db", "read", "get", "fetch", "list", "query", "search"
        }
    }

    @classmethod
    def classify_tool(cls, tool: Tool) -> list[ToolCapability]:
        categories = []
        name_lower = tool.name.lower()
        desc_lower = tool.description.lower()
        param_names_lower = {p.name.lower() for p in tool.parameters}
        param_descs_lower = {p.description.lower() for p in tool.parameters}

        def matches_any(keywords: set[str]) -> bool:
            # 1. Substring/exact match in tool name (short and specific)
            if any(kw in name_lower for kw in keywords):
                return True

            # 2. Whole-word match in description and parameters
            def get_words(text: str) -> set[str]:
                return set(re.findall(r'[a-zA-Z0-9]+', text.lower()))

            desc_words = get_words(desc_lower)
            param_names_words = {w for p_name in param_names_lower for w in get_words(p_name)}
            param_descs_words = {w for p_desc in param_descs_lower for w in get_words(p_desc)}

            all_words = desc_words | param_names_words | param_descs_words
            
            for kw in keywords:
                kw_words = get_words(kw)
                if kw_words and kw_words.issubset(all_words):
                    return True
            return False

        # Destructive capability
        if tool.destructive or matches_any(cls.CATEGORIES[ToolCapability.DESTRUCTIVE]):
            categories.append(ToolCapability.DESTRUCTIVE)

        # Financial capability
        if matches_any(cls.CATEGORIES[ToolCapability.FINANCIAL]):
            categories.append(ToolCapability.FINANCIAL)

        # Communication capability
        if matches_any(cls.CATEGORIES[ToolCapability.COMMUNICATION]):
            categories.append(ToolCapability.COMMUNICATION)

        # Authorization capability
        if matches_any(cls.CATEGORIES[ToolCapability.AUTHORIZATION]):
            categories.append(ToolCapability.AUTHORIZATION)

        # Data Access capability
        if tool.sensitive or matches_any(cls.CATEGORIES[ToolCapability.DATA_ACCESS]):
            categories.append(ToolCapability.DATA_ACCESS)

        # Read Only capability
        has_active_side_effects = any(
            cat in categories for cat in [
                ToolCapability.DESTRUCTIVE,
                ToolCapability.FINANCIAL,
                ToolCapability.COMMUNICATION,
                ToolCapability.AUTHORIZATION
            ]
        )
        if not has_active_side_effects:
            categories.append(ToolCapability.READ_ONLY)

        return categories


class StaticProfiler(BaseProfiler):
    """
    A deterministic, explainable agent profiler.
    Analyzes system prompt, tools, parameters, and side effects.
    Works entirely without LLMs.
    """

    async def profile(self, agent: Agent) -> RiskProfile:
        """
        Build a profile from the Agent definition using deterministic rules.
        """
        capabilities: list[Capability] = []
        destructive_tools: list[str] = []
        sensitive_tools: list[str] = []

        for tool in agent.tools:
            categories = ToolClassifier.classify_tool(tool)
            
            # Determine capability risk level based on its categories
            if ToolCapability.DESTRUCTIVE in categories or ToolCapability.FINANCIAL in categories:
                risk_level = "high"
            elif ToolCapability.COMMUNICATION in categories or ToolCapability.AUTHORIZATION in categories or ToolCapability.DATA_ACCESS in categories:
                risk_level = "medium"
            else:
                risk_level = "low"

            capability = Capability(
                name=f"can_{tool.name}",
                description=f"Allows executing '{tool.name}' which belongs to categories: {', '.join(categories)}.",
                risk_level=risk_level,
                related_tools=[tool.name],
            )
            capabilities.append(capability)

            if ToolCapability.DESTRUCTIVE in categories:
                destructive_tools.append(tool.name)
            if ToolCapability.DATA_ACCESS in categories or tool.sensitive:
                sensitive_tools.append(tool.name)

        # Analyze the system prompt deterministically
        prompt_lower = agent.system_prompt.lower()
        attack_surfaces: list[AttackSurfaceEvidence] = []
        evidence_dict: dict[str, str] = {}

        # Rule A: Authority Spoofing / Identity / Role-based access
        auth_keywords = ["verify", "identity", "confirm", "admin", "administrator", "role", "authorization", "authorize", "authenticated"]
        if any(re.search(rf"\b{kw}\b", prompt_lower) for kw in auth_keywords):
            reason = "Agent prompt specifies identity or role verification requirements for authorization."
            attack_surfaces.append(AttackSurfaceEvidence(
                attack_surface=AttackStrategy.AUTHORITY_SPOOFING.value,
                reason=reason
            ))
            evidence_dict["authority_spoofing"] = reason

        # Rule B: Urgency manipulation
        urgency_keywords = ["urgency", "urgent", "emergency", "immediately", "asap", "manipulated", "pressure"]
        if any(re.search(rf"\b{kw}\b", prompt_lower) for kw in urgency_keywords):
            reason = "Agent prompt mentions handling of urgent requests or warns against urgency manipulation."
            attack_surfaces.append(AttackSurfaceEvidence(
                attack_surface=AttackStrategy.URGENCY.value,
                reason=reason
            ))
            evidence_dict["urgency"] = reason

        # Rule C: Ambiguity / Escalation
        escalation_keywords = ["escalate", "supervisor", "human", "doubt", "unsure", "decline"]
        if any(re.search(rf"\b{kw}\b", prompt_lower) for kw in escalation_keywords):
            reason = "Agent prompt defines policies for handling ambiguity or escalating to a human supervisor."
            attack_surfaces.append(AttackSurfaceEvidence(
                attack_surface=AttackStrategy.AMBIGUITY.value,
                reason=reason
            ))
            evidence_dict["ambiguity"] = reason

        # Rule D: Destructive Action Restrictions
        destructive_keywords = ["destructive", "irreversible", "delete", "remove", "refund", "never", "must not", "prohibited"]
        if any(re.search(rf"\b{kw}\b", prompt_lower) for kw in destructive_keywords) and destructive_tools:
            reason = "Agent prompt restricts destructive or irreversible operations while the agent possesses destructive tools."
            attack_surfaces.append(AttackSurfaceEvidence(
                attack_surface="destructive_action_restrictions",
                reason=reason
            ))
            evidence_dict["destructive_action_restrictions"] = reason

        # Generate risk indicators
        risk_indicators: list[RiskIndicator] = []
        
        if destructive_tools:
            risk_indicators.append(RiskIndicator(
                name="destructive_tools_present",
                severity="high",
                description="The agent has tools with irreversible side effects.",
                evidence=f"Destructive tools found: {', '.join(destructive_tools)}"
            ))
            
        financial_tools = [t.name for t in agent.tools if ToolCapability.FINANCIAL in ToolClassifier.classify_tool(t)]
        if financial_tools:
            risk_indicators.append(RiskIndicator(
                name="financial_tools_present",
                severity="high",
                description="The agent has tools that execute financial transactions.",
                evidence=f"Financial tools found: {', '.join(financial_tools)}"
            ))

        communication_tools = [t.name for t in agent.tools if ToolCapability.COMMUNICATION in ToolClassifier.classify_tool(t)]
        if communication_tools:
            risk_indicators.append(RiskIndicator(
                name="communication_tools_present",
                severity="medium",
                description="The agent has tools that send external communications.",
                evidence=f"Communication tools found: {', '.join(communication_tools)}"
            ))

        sensitive_tools_present = [t.name for t in agent.tools if ToolCapability.DATA_ACCESS in ToolClassifier.classify_tool(t)]
        if sensitive_tools_present:
            risk_indicators.append(RiskIndicator(
                name="sensitive_data_access",
                severity="medium",
                description="The agent can access or edit sensitive system or customer records.",
                evidence=f"Sensitive tools found: {', '.join(sensitive_tools_present)}"
            ))

        if "urgency" in evidence_dict:
            risk_indicators.append(RiskIndicator(
                name="urgency_susceptibility",
                severity="medium",
                description="Agent prompt references urgency, indicating a risk of manipulation via urgent claims.",
                evidence="System prompt references handling of urgency or pressure."
            ))

        return RiskProfile(
            agent_id=agent.id,
            capabilities=capabilities,
            attack_surfaces=attack_surfaces,
            destructive_tools=destructive_tools,
            sensitive_tools=sensitive_tools,
            risk_indicators=risk_indicators,
            evidence=evidence_dict,
        )

