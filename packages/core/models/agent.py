"""
Agent domain models.

Defines the canonical representation of an agent, its tools,
capabilities, constraints, and profile.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    """Supported parameter types for tool definitions."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """A single parameter in a tool's parameter schema."""

    name: str = Field(description="Parameter name.")
    type: ParameterType = Field(description="Parameter data type.")
    description: str = Field(description="Human-readable description of the parameter.")
    required: bool = Field(default=True, description="Whether this parameter is required.")
    enum_values: list[str] | None = Field(
        default=None,
        description="Allowed values for string enums.",
    )

    model_config = {"frozen": True}


class Tool(BaseModel):
    """
    A tool that an agent can invoke.

    Tools are the primary surface area for agent reliability testing.
    Destructive and sensitive tools receive heightened scrutiny.
    """

    name: str = Field(description="Unique tool name. Used as the function call identifier.")
    description: str = Field(description="Human-readable description of what the tool does.")
    parameters: list[ToolParameter] = Field(
        default_factory=list,
        description="Ordered list of parameters this tool accepts.",
    )
    destructive: bool = Field(
        default=False,
        description="Whether this tool has irreversible side effects (e.g., refund, delete).",
    )
    sensitive: bool = Field(
        default=False,
        description="Whether this tool accesses or modifies sensitive data.",
    )

    model_config = {"frozen": True}

    def to_function_schema(self) -> dict[str, Any]:
        """
        Produce a JSON-schema-compatible function definition.
        Suitable for passing to LLM provider function-calling APIs.
        """
        properties: dict[str, Any] = {}
        required_params: list[str] = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.enum_values:
                prop["enum"] = param.enum_values
            properties[param.name] = prop
            if param.required:
                required_params.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_params,
            },
        }


class AgentVersion(BaseModel):
    """A versioned snapshot of an agent configuration."""

    agent_id: str = Field(description="Stable agent identifier.")
    version: str = Field(description="Semantic version string, e.g. '1.0.0'.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this version was recorded.",
    )
    notes: str | None = Field(default=None, description="Optional release notes.")


class Agent(BaseModel):
    """
    The canonical agent definition.

    Represents an agent's identity, configuration, and tool set.
    This is the stable contract that the evaluation engine works with.
    """

    id: str = Field(description="Globally unique agent identifier.")
    name: str = Field(description="Human-readable agent name.")
    description: str = Field(default="", description="What this agent does.")
    system_prompt: str = Field(description="The system prompt that configures the agent.")
    tools: list[Tool] = Field(default_factory=list, description="Tools available to this agent.")
    version: str = Field(default="1.0.0", description="Current version of this agent.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata for downstream use.",
    )


class Capability(BaseModel):
    """
    A capability identified during agent profiling.

    Capabilities map to potential attack surfaces.
    """

    name: str = Field(description="Short capability name.")
    description: str = Field(description="What this capability allows the agent to do.")
    risk_level: str = Field(
        default="medium",
        description="Estimated risk level: low, medium, high, critical.",
    )
    related_tools: list[str] = Field(
        default_factory=list,
        description="Tool names that implement this capability.",
    )


class Constraint(BaseModel):
    """
    A behavioral constraint the agent is supposed to follow.

    Constraints are checked by the evaluator to detect violations.
    """

    name: str = Field(description="Short constraint identifier.")
    description: str = Field(description="What the agent must or must not do.")
    constraint_type: str = Field(
        default="policy",
        description="Type: policy, safety, authorization, format.",
    )
    enforced_by_prompt: bool = Field(
        default=True,
        description="Whether this constraint is stated in the system prompt.",
    )


class RiskSurface(BaseModel):
    """
    The aggregate risk surface derived from an agent's profile.

    Summarizes what attack families are relevant for this agent.
    """

    tools: list[str] = Field(
        default_factory=list,
        description="Names of tools that represent risk surface.",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Names of capabilities that represent risk surface.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Names of constraints that are testable.",
    )
    attack_families: list[str] = Field(
        default_factory=list,
        description="Relevant attack families for this agent.",
    )
    destructive_tools: list[str] = Field(
        default_factory=list,
        description="Subset of tools that are destructive.",
    )
    sensitive_tools: list[str] = Field(
        default_factory=list,
        description="Subset of tools that access sensitive data.",
    )


class AgentProfile(BaseModel):
    """
    The structured profile produced by the profiler.

    Drives scenario generation and attack strategy selection.
    """

    agent_id: str = Field(description="Agent being profiled.")
    name: str = Field(description="Agent name.")
    description: str = Field(default="", description="Agent description.")
    capabilities: list[Capability] = Field(default_factory=list)
    tools: list[Tool] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    risk_surface: RiskSurface = Field(default_factory=RiskSurface)
    profiled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(BaseModel):
    """A single message in an agent conversation."""

    role: str = Field(description="Message role: user, assistant, or system.")
    content: str = Field(description="Message content.")


class ToolCallRecord(BaseModel):
    """Record of a single tool call made during an execution."""

    tool_name: str = Field(description="Name of the tool that was called.")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the tool.",
    )
    result: Any = Field(default=None, description="Result returned by the tool.")
    error: str | None = Field(default=None, description="Error message if the call failed.")


class AgentInput(BaseModel):
    """Input provided to an agent for one execution."""

    conversation_id: str = Field(description="Unique identifier for this conversation.")
    messages: list[Message] = Field(description="Conversation history including the new input.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context passed to the agent.",
    )


class AgentOutput(BaseModel):
    """Output produced by an agent after processing one input."""

    response: str = Field(description="The agent's final text response.")
    tool_calls_made: list[ToolCallRecord] = Field(
        default_factory=list,
        description="All tool calls made during this execution.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional output metadata.",
    )
    error: str | None = Field(
        default=None,
        description="Error message if the agent failed to produce output.",
    )
