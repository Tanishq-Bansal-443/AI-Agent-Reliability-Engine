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
    ) -> None:
        # Validate endpoint URL scheme
        parsed = urlparse(endpoint_url)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme: '{parsed.scheme}'. Must be http or https.")
        
        self.endpoint_url = endpoint_url
        self.method = method.upper()
        if self.method not in ("GET", "POST", "PUT"):
            raise ValueError(f"Unsupported HTTP method: '{method}'")
            
        self.timeout = timeout
        self.request_input_field = request_input_field
        self.response_output_field = response_output_field
        self._agent_id = agent_id
        self._agent_name = agent_name

    def get_agent(self) -> Agent:
        """Return the canonical agent definition."""
        return Agent(
            id=self._agent_id,
            name=self._agent_name,
            description=f"External HTTP/API agent at {self.endpoint_url}",
            system_prompt="External HTTP Agent, evaluated over HTTP.",
            tools=[],  # HTTP agents have no tools by default unless configured
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
        agent = self.get_agent()
        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            description=agent.description,
            capabilities=[],
            tools=[],
            constraints=[],
            risk_surface=RiskSurface(
                tools=[],
                capabilities=[],
                constraints=[],
                attack_families=["prompt_injection"]  # Minimal default attack family
            ),
            profiled_at=datetime.now(timezone.utc)
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
