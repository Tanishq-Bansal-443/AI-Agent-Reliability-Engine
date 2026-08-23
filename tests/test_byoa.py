"""
Unit tests for the Bring Your Own Agent (BYOA) capability.
Covers:
- HTTPAgentAdapter execution, timeout, connection failure, HTTP errors, and JSON errors.
- Python dynamic loader validation on valid and invalid adapters.
- CLI argument resolving logic.
- Demo agent backward compatibility.
"""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agents.demo_customer_support.adapter import DemoAgentAdapter
from packages.agent_adapters.http import HTTPAgentAdapter
from packages.agent_adapters.python import load_python_agent
from packages.cli.main import resolve_agent_adapter_cli
from packages.core.models.agent import AgentInput, AgentOutput, Message
from packages.sandbox.tool_runtime import ToolRegistry, ToolRuntime


# ---------------------------------------------------------------------------
# HTTP Agent Adapter Tests
# ---------------------------------------------------------------------------

class TestHTTPAgentAdapter:
    """Tests for the HTTPAgentAdapter class."""

    def test_init_validation(self) -> None:
        """Validate init URL and method constraints."""
        # Valid init
        adapter = HTTPAgentAdapter("http://example.com/chat", method="POST")
        assert adapter.endpoint_url == "http://example.com/chat"
        assert adapter.method == "POST"

        # Invalid URL scheme
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            HTTPAgentAdapter("ftp://example.com/chat")

        # Invalid URL format
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            HTTPAgentAdapter("not-a-url")

        # Invalid HTTP Method
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            HTTPAgentAdapter("http://example.com/chat", method="DELETE")

    def test_get_agent_and_profile(self) -> None:
        """Verify the definition and profile structure of the HTTP agent."""
        adapter = HTTPAgentAdapter("http://localhost:5000/chat", agent_id="my_http_agent", agent_name="Custom API")
        agent = adapter.get_agent()
        profile = adapter.get_profile()

        assert agent.id == "my_http_agent"
        assert agent.name == "Custom API"
        assert len(agent.tools) == 3
        assert profile.agent_id == "my_http_agent"
        assert len(profile.risk_surface.attack_families) >= 1

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_run_success(self, mock_post: MagicMock) -> None:
        """Test successful HTTP exchange with custom request/response JSON paths."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "100"}
        mock_response.text = '{"data": {"reply": "Hello User!"}}'
        mock_response.json.return_value = {"data": {"reply": "Hello User!"}}
        mock_post.return_value = mock_response

        adapter = HTTPAgentAdapter(
            endpoint_url="http://localhost:5000/chat",
            request_input_field="input.text",
            response_output_field="data.reply"
        )
        
        agent_input = AgentInput(
            conversation_id="conv-123",
            messages=[Message(role="user", content="Hi there")]
        )
        runtime = ToolRuntime(ToolRegistry())
        output = await adapter.run(agent_input, runtime)

        assert output.error is None
        assert output.response == "Hello User!"
        assert output.metadata.get("status_code") == 200

        # Assert correct request structure passed to HTTP client
        mock_post.assert_called_once_with(
            "http://localhost:5000/chat",
            json={"input": {"text": "Hi there"}}
        )

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_run_timeout(self, mock_post: MagicMock) -> None:
        """Verify timeout handler returns a graceful error in output."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        adapter = HTTPAgentAdapter("http://localhost:5000/chat", timeout=5.0)
        agent_input = AgentInput(conversation_id="c", messages=[Message(role="user", content="Hi")])
        runtime = ToolRuntime(ToolRegistry())
        output = await adapter.run(agent_input, runtime)

        assert output.response == ""
        assert output.error is not None
        assert "Timeout" in output.error

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_run_connection_failure(self, mock_post: MagicMock) -> None:
        """Verify connection failure returns a graceful error."""
        mock_post.side_effect = httpx.ConnectError("Failed to resolve")

        adapter = HTTPAgentAdapter("http://localhost:5000/chat")
        agent_input = AgentInput(conversation_id="c", messages=[Message(role="user", content="Hi")])
        runtime = ToolRuntime(ToolRegistry())
        output = await adapter.run(agent_input, runtime)

        assert output.response == ""
        assert output.error is not None
        assert "Connection Error" in output.error

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_run_http_error(self, mock_post: MagicMock) -> None:
        """Verify non-200 responses are handled gracefully."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        # raise_for_status throws HTTPStatusError
        request = httpx.Request("POST", "http://localhost:5000/chat")
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=request, response=mock_response
        )
        mock_post.return_value = mock_response

        adapter = HTTPAgentAdapter("http://localhost:5000/chat")
        agent_input = AgentInput(conversation_id="c", messages=[Message(role="user", content="Hi")])
        runtime = ToolRuntime(ToolRegistry())
        output = await adapter.run(agent_input, runtime)

        assert output.response == ""
        assert output.error is not None
        assert "HTTP Error" in output.error
        assert "500" in output.error

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_run_malformed_json(self, mock_post: MagicMock) -> None:
        """Verify malformed JSON payload returns a validation/json error."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "20"}
        mock_response.text = "invalid json payload"
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_post.return_value = mock_response

        adapter = HTTPAgentAdapter("http://localhost:5000/chat")
        agent_input = AgentInput(conversation_id="c", messages=[Message(role="user", content="Hi")])
        runtime = ToolRuntime(ToolRegistry())
        output = await adapter.run(agent_input, runtime)

        assert output.response == ""
        assert output.error is not None
        assert "JSON" in output.error

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_run_oversized_response(self, mock_post: MagicMock) -> None:
        """Verify that response size exceeding 1MB limit triggers size validation error."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-length": str(1024 * 1024 + 10)}
        mock_post.return_value = mock_response

        adapter = HTTPAgentAdapter("http://localhost:5000/chat")
        agent_input = AgentInput(conversation_id="c", messages=[Message(role="user", content="Hi")])
        runtime = ToolRuntime(ToolRegistry())
        output = await adapter.run(agent_input, runtime)

        assert output.response == ""
        assert output.error is not None
        assert "size" in output.error.lower()


# ---------------------------------------------------------------------------
# Python Dynamic Loader Tests
# ---------------------------------------------------------------------------

class TestPythonAgentLoader:
    """Tests for the dynamic loader and validation under packages/agent_adapters/python.py."""

    def test_loader_valid_template(self, tmp_path: Path) -> None:
        """Test loading a structurally correct custom Python agent adapter."""
        # Create a valid Python agent adapter script
        code = """
from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile, RiskSurface
from datetime import datetime, timezone

class MyValidAdapter(BaseAgentAdapter):
    def get_agent(self) -> Agent:
        return Agent(id="valid_py", name="Valid Python", system_prompt="Help", tools=[])
        
    def get_profile(self) -> AgentProfile:
        agent = self.get_agent()
        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            tools=[],
            capabilities=[],
            constraints=[],
            risk_surface=RiskSurface(tools=[], capabilities=[], constraints=[], attack_families=[]),
            profiled_at=datetime.now(timezone.utc)
        )
        
    async def run(self, agent_input: AgentInput, runtime) -> AgentOutput:
        return AgentOutput(response="Echo: Done", tool_calls_made=[])
"""
        filepath = tmp_path / "valid_agent.py"
        filepath.write_text(code, encoding="utf-8")

        # Load it
        adapter = load_python_agent(str(filepath), class_name="MyValidAdapter")
        assert adapter is not None
        assert adapter.agent_id == "valid_py"

        # Load without class name (should discover automatically)
        adapter_discovered = load_python_agent(str(filepath))
        assert adapter_discovered.agent_id == "valid_py"

    def test_loader_invalid_file_raises(self) -> None:
        """Loader must raise FileNotFoundError for nonexistent paths."""
        with pytest.raises(FileNotFoundError):
            load_python_agent("nonexistent_agent_file.py")

    def test_loader_missing_methods_raises(self, tmp_path: Path) -> None:
        """Loader must reject classes missing get_agent, get_profile, or run."""
        code = """
class MyInvalidAdapter:
    def get_agent(self):
        return None
    # get_profile and run are missing
"""
        filepath = tmp_path / "invalid_agent.py"
        filepath.write_text(code, encoding="utf-8")

        with pytest.raises(ValueError, match="No valid agent adapter class found"):
            load_python_agent(str(filepath))

    def test_loader_non_coroutine_run_raises(self, tmp_path: Path) -> None:
        """Loader must reject adapters where run() is synchronous."""
        code = """
from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile, RiskSurface
from datetime import datetime, timezone

class MySyncRunAdapter(BaseAgentAdapter):
    def get_agent(self) -> Agent:
        return Agent(id="sync_py", name="Sync Python", system_prompt="Help", tools=[])
        
    def get_profile(self) -> AgentProfile:
        agent = self.get_agent()
        return AgentProfile(
            agent_id=agent.id,
            name=agent.name,
            tools=[],
            capabilities=[],
            constraints=[],
            risk_surface=RiskSurface(tools=[], capabilities=[], constraints=[], attack_families=[]),
            profiled_at=datetime.now(timezone.utc)
        )
        
    def run(self, agent_input: AgentInput, runtime) -> AgentOutput:
        return AgentOutput(response="Sync response", tool_calls_made=[])
"""
        filepath = tmp_path / "sync_run_agent.py"
        filepath.write_text(code, encoding="utf-8")

        with pytest.raises(TypeError, match="run\\(\\) method must be an async coroutine"):
            load_python_agent(str(filepath))

    def test_loader_wrong_return_types_raises(self, tmp_path: Path) -> None:
        """Loader must reject adapters returning wrong types from metadata calls."""
        code = """
from packages.agent_adapters.base import BaseAgentAdapter

class WrongReturnTypeAdapter(BaseAgentAdapter):
    def get_agent(self):
        return "not-an-agent-object"  # Error
        
    def get_profile(self):
        return None
        
    async def run(self, agent_input, runtime):
        return None
"""
        filepath = tmp_path / "wrong_return_agent.py"
        filepath.write_text(code, encoding="utf-8")

        with pytest.raises(TypeError, match="get_agent\\(\\) must return a .*Agent instance"):
            load_python_agent(str(filepath))


# ---------------------------------------------------------------------------
# CLI & Demo Agent Compatibility Tests
# ---------------------------------------------------------------------------

class TestCLIAgentCompatibility:
    """Verify that CLI resolver works for built-in, HTTP, and Python agent types."""

    def test_resolve_demo_customer_support(self) -> None:
        """Demo customer support continues to resolve correctly."""
        args = argparse.Namespace(agent_type="built-in", agent="demo_customer_support")
        adapter = resolve_agent_adapter_cli(args)
        assert isinstance(adapter, DemoAgentAdapter)
        assert adapter.agent_id == "demo-customer-support-v1"

    def test_resolve_http_agent_cli(self) -> None:
        """CLI arguments translate to HTTPAgentAdapter."""
        args = argparse.Namespace(
            agent_type="http",
            agent_url="http://localhost:5000/chat",
            agent_method="POST",
            agent_timeout=15.0,
            agent_input_field="message",
            agent_output_field="response"
        )
        adapter = resolve_agent_adapter_cli(args)
        assert isinstance(adapter, HTTPAgentAdapter)
        assert adapter.endpoint_url == "http://localhost:5000/chat"
        assert adapter.method == "POST"
        assert adapter.timeout == 15.0

    def test_resolve_python_agent_cli(self, tmp_path: Path) -> None:
        """CLI arguments load Python files via dynamic loader."""
        code = """
from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile, RiskSurface
from datetime import datetime, timezone

class MyCliAdapter(BaseAgentAdapter):
    def get_agent(self) -> Agent:
        return Agent(id="cli_py", name="CLI Python", system_prompt="Help", tools=[])
    def get_profile(self) -> AgentProfile:
        agent = self.get_agent()
        return AgentProfile(
            agent_id=agent.id, name=agent.name, tools=[], capabilities=[], constraints=[],
            risk_surface=RiskSurface(tools=[], capabilities=[], constraints=[], attack_families=[]),
            profiled_at=datetime.now(timezone.utc)
        )
    async def run(self, agent_input, runtime) -> AgentOutput:
        return AgentOutput(response="cli", tool_calls_made=[])
"""
        filepath = tmp_path / "cli_agent.py"
        filepath.write_text(code, encoding="utf-8")

        args = argparse.Namespace(
            agent_type="python",
            agent_path=str(filepath),
            agent_class="MyCliAdapter"
        )
        adapter = resolve_agent_adapter_cli(args)
        assert adapter is not None
        assert adapter.agent_id == "cli_py"
