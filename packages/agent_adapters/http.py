"""
HTTPAgentAdapter — wraps an external HTTP/API agent for evaluation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile, RiskSurface

logger = logging.getLogger(__name__)


class HTTPAgentAdapter(BaseAgentAdapter):
    """
    Adapter exposing an external HTTP/API agent through the BaseAgentAdapter interface.

    Allows configuration of:
    - endpoint_url: The URL to query (e.g. http://localhost:5000/chat)
    - method: HTTP method (GET, POST, PUT)
    - timeout: Timeout in seconds
    - request_input_field: JSON field to place the user message in (e.g. "message" or "input.text")
    - response_output_field: JSON field to read the response from (e.g. "response" or "output.text")
    """

    def __init__(
        self,
        endpoint_url: str,
        method: str = "POST",
        timeout: float = 10.0,
        request_input_field: str = "message",
        response_output_field: str = "response",
        agent_id: str = "http_agent",
        agent_name: str = "HTTP/API Agent",
        system_prompt: str | None = None,
        tools: list[Any] | None = None,
    ) -> None:
        # Validate endpoint URL scheme
        parsed = urlparse(endpoint_url)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme: '{parsed.scheme}'. Must be http or https.")
        
        # If no path is specified or path is root, default to /chat for sample endpoint compatibility
        if not parsed.path or parsed.path == "/":
            endpoint_url = f"{parsed.scheme}://{parsed.netloc}/chat"
            parsed = urlparse(endpoint_url)

        self.endpoint_url = endpoint_url
        self.method = method.upper()
        if self.method not in ("GET", "POST", "PUT"):
            raise ValueError(f"Unsupported HTTP method: '{method}'")
            
        self.timeout = timeout
        self.request_input_field = request_input_field
        self.response_output_field = response_output_field
        self._agent_id = agent_id
        self._agent_name = agent_name
        self.system_prompt = system_prompt
        self.tools = tools

    def get_agent(self) -> Agent:
        """Return the canonical agent definition."""
        # 1. Use explicitly provided prompt and tools if configured
        if self.system_prompt is not None and self.tools is not None:
            return Agent(
                id=self._agent_id,
                name=self._agent_name,
                description=f"External HTTP/API agent at {self.endpoint_url}",
                system_prompt=self.system_prompt,
                tools=self.tools,
                version="1.0.0",
                metadata={
                    "endpoint_url": self.endpoint_url,
                    "method": self.method,
                    "timeout": self.timeout,
                    "request_input_field": self.request_input_field,
                    "response_output_field": self.response_output_field,
                }
            )

        # 2. Try to fetch agent definition from base_url/agent or base_url/metadata
        try:
            parsed = urlparse(self.endpoint_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Query GET base_url/agent first, fallback to base_url/metadata
            for path in ("/agent", "/metadata"):
                try:
                    with httpx.Client(timeout=2.0) as client:
                        res = client.get(f"{base_url}{path}")
                        if res.status_code == 200:
                            data = res.json()
                            tools = []
                            for t_data in data.get("tools", []):
                                from packages.core.models.agent import Tool
                                tools.append(Tool.model_validate(t_data))
                            
                            return Agent(
                                id=data.get("id", self._agent_id),
                                name=data.get("name", self._agent_name),
                                description=data.get("description", f"External HTTP/API agent at {self.endpoint_url}"),
                                system_prompt=data.get("system_prompt", "External HTTP Agent, evaluated over HTTP."),
                                tools=tools,
                                version=data.get("version", "1.0.0"),
                                metadata={
                                    "endpoint_url": self.endpoint_url,
                                    "method": self.method,
                                    "timeout": self.timeout,
                                    "request_input_field": self.request_input_field,
                                    "response_output_field": self.response_output_field,
                                    **data.get("metadata", {})
                                }
                            )
                except Exception:
                    continue
        except Exception as exc:
            logger.debug(f"Failed to query HTTP agent metadata: {exc}")

        # 3. Default fallback to customer support prompt and tools to ensure E2E pipeline generates scenarios
        from agents.demo_customer_support.agent import SYSTEM_PROMPT
        from agents.demo_customer_support.tools import CUSTOMER_SUPPORT_TOOLS
        return Agent(
            id=self._agent_id,
            name=self._agent_name,
            description=f"External HTTP/API agent at {self.endpoint_url}",
            system_prompt=SYSTEM_PROMPT,
            tools=CUSTOMER_SUPPORT_TOOLS,
            version="1.0.0",
            metadata={
                "endpoint_url": self.endpoint_url,
                "method": self.method,
                "timeout": self.timeout,
                "request_input_field": self.request_input_field,
                "response_output_field": self.response_output_field,
            }
        )

    def get_profile(self) -> AgentProfile:
        """Return the agent's capability profile."""
        import asyncio
        from packages.profiler.base import StaticProfiler
        from packages.core.models.agent import Constraint, RiskSurface

        agent = self.get_agent()
        profiler = StaticProfiler()
        
        try:
            coro = profiler.profile(agent)
            coro.send(None)
        except StopIteration as exc:
            risk_profile = exc.value
        except Exception:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
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
                risk_profile = loop.run_until_complete(profiler.profile(agent))
            except Exception:
                risk_profile = asyncio.run(profiler.profile(agent))

        return self._build_profile_from_risk(risk_profile)

    def _build_profile_from_risk(self, risk_profile: Any) -> AgentProfile:
        from packages.core.models.agent import Constraint, RiskSurface
        from packages.core.models.scenario import AttackStrategyType
        
        agent = self.get_agent()
        
        constraints = []
        if "authority_spoofing" in risk_profile.evidence:
            constraints.append(Constraint(
                name="identity_verification_required",
                description="Agent must verify customer identity before sensitive operations.",
                constraint_type="authorization",
                enforced_by_prompt=True,
            ))
        if any(kw in agent.system_prompt.lower() for kw in ["do not", "never", "must not", "prohibited"]):
            constraints.append(Constraint(
                name="policy_restrictions",
                description="Agent has explicit policy restrictions in system prompt.",
                constraint_type="policy",
                enforced_by_prompt=True,
            ))

        attack_families = [surf.attack_surface for surf in risk_profile.attack_surfaces]
        if "prompt_injection" not in attack_families:
            attack_families.append("prompt_injection")
        if risk_profile.destructive_tools and AttackStrategyType.PROMPT_INJECTION.value not in attack_families:
            attack_families.append(AttackStrategyType.PROMPT_INJECTION.value)
        if risk_profile.sensitive_tools and AttackStrategyType.DATA_EXFILTRATION.value not in attack_families:
            attack_families.append(AttackStrategyType.DATA_EXFILTRATION.value)

        risk_surface = RiskSurface(
            tools=[t.name for t in agent.tools],
            capabilities=[c.name for c in risk_profile.capabilities],
            constraints=[c.name for c in constraints],
            attack_families=attack_families,
            destructive_tools=risk_profile.destructive_tools,
            sensitive_tools=risk_profile.sensitive_tools,
        )

        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            description=agent.description,
            capabilities=risk_profile.capabilities,
            tools=agent.tools,
            constraints=constraints,
            risk_surface=risk_surface,
        )

    async def run(
        self,
        agent_input: AgentInput,
        runtime: Any,  # ToolRuntime
    ) -> AgentOutput:
        """
        Run the external HTTP agent against the scenario input.
        """
        # Security constraints
        max_response_size = 1024 * 1024  # 1MB response limit
        
        user_message = ""
        if agent_input.messages:
            user_message = agent_input.messages[-1].content

        # Nest input payload if requested
        payload: dict[str, Any] = {}
        self._set_nested_value(payload, self.request_input_field, user_message)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.method == "GET":
                    response = await client.get(self.endpoint_url, params=payload)
                elif self.method == "POST":
                    response = await client.post(self.endpoint_url, json=payload)
                elif self.method == "PUT":
                    response = await client.put(self.endpoint_url, json=payload)
                else:
                    raise ValueError(f"Unsupported HTTP method: {self.method}")

                # Handle HTTP errors
                response.raise_for_status()

                # Enforce response size limits
                content_len = response.headers.get("content-length")
                if content_len and int(content_len) > max_response_size:
                    raise ValueError(f"Response size exceeds limit of {max_response_size} bytes")

                body = response.text
                if len(body.encode("utf-8")) > max_response_size:
                    raise ValueError(f"Response size exceeds limit of {max_response_size} bytes")

                # Try parsing JSON
                try:
                    res_json = response.json()
                except (json.JSONDecodeError, ValueError) as exc:
                    raise ValueError(f"Response is not valid JSON: {exc}")

                # Extract response field (supports nested path)
                agent_response = self._get_nested_value(res_json, self.response_output_field)
                if agent_response is None:
                    raise ValueError(
                        f"Response field '{self.response_output_field}' not found in response: {res_json}"
                    )

                if not isinstance(agent_response, str):
                    agent_response = str(agent_response)

                return AgentOutput(
                    response=agent_response,
                    tool_calls_made=[],
                    metadata={"status_code": response.status_code}
                )

        except httpx.TimeoutException as exc:
            logger.error(f"HTTP agent request timed out: {exc}")
            return AgentOutput(
                response="",
                error=f"Timeout: HTTP request timed out after {self.timeout} seconds.",
                tool_calls_made=[]
            )
        except httpx.ConnectError as exc:
            logger.error(f"HTTP agent connection failed: {exc}")
            return AgentOutput(
                response="",
                error="Connection Error: Failed to connect to the HTTP agent endpoint.",
                tool_calls_made=[]
            )
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP agent returned error status: {exc.response.status_code}")
            return AgentOutput(
                response="",
                error=f"HTTP Error: Server returned status {exc.response.status_code}.",
                tool_calls_made=[]
            )
        except Exception as exc:
            logger.error(f"HTTP agent execution error: {exc}")
            return AgentOutput(
                response="",
                error=f"Execution Error: {str(exc)}",
                tool_calls_made=[]
            )

    def _set_nested_value(self, d: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested dictionary value using dot notation (e.g. 'a.b.c')."""
        parts = path.split(".")
        current = d
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    def _get_nested_value(self, d: Any, path: str) -> Any | None:
        """Get a nested value from a dictionary using dot notation (e.g. 'a.b.c')."""
        if not isinstance(d, dict):
            return None
        parts = path.split(".")
        current = d
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
