"""
Tests for the FastAPI application.

Verifies:
- Health endpoint returns 200
- Health response has expected structure
- Evaluate endpoint accepts valid requests
- API docs endpoint is accessible
"""

import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# Ensure the API can import packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.api.main import app


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_ok_status(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_returns_version(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        data = response.json()
        assert "version" in data
        assert data["version"]

    @pytest.mark.asyncio
    async def test_health_returns_timestamp(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        data = response.json()
        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO 8601

    @pytest.mark.asyncio
    async def test_health_returns_json(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        assert "application/json" in response.headers["content-type"]


class TestEvaluateEndpoint:
    """Tests for POST /api/evaluate (Phase 0 scaffold)."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_200(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={"agent_id": "demo-customer-support-v1"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_evaluate_returns_run_id(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={"agent_id": "demo-customer-support-v1"},
            )

        data = response.json()
        assert "run_id" in data
        assert data["run_id"]

    @pytest.mark.asyncio
    async def test_evaluate_echoes_agent_id(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={"agent_id": "my-test-agent"},
            )

        data = response.json()
        assert data["agent_id"] == "my-test-agent"

    @pytest.mark.asyncio
    async def test_evaluate_returns_status(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={"agent_id": "demo-agent"},
            )

        data = response.json()
        assert "status" in data
        assert data["status"]

    @pytest.mark.asyncio
    async def test_evaluate_with_scenario_id(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={
                    "agent_id": "demo-agent",
                    "scenario_id": "authority-spoof-001",
                },
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_evaluate_requires_agent_id(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={},  # Missing agent_id
            )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_evaluate_http_agent_requires_url(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={
                    "agent_id": "test_http_agent",
                    "agent_type": "http",
                },
            )
        assert response.status_code == 400
        assert "endpoint_url is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_evaluate_python_agent_requires_path(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/evaluate",
                json={
                    "agent_id": "test_py_agent",
                    "agent_type": "python",
                },
            )
        assert response.status_code == 400
        assert "agent_path is required" in response.json()["detail"]


class TestApiDocs:
    """Tests for OpenAPI documentation endpoints."""

    @pytest.mark.asyncio
    async def test_openapi_json_accessible(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data

    @pytest.mark.asyncio
    async def test_docs_accessible(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/docs")

        assert response.status_code == 200
