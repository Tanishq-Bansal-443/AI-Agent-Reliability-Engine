"""
FastAPI application for the AI Agent Reliability Engine.

Phase 0: Health endpoint + evaluate scaffold.
Later phases will add full evaluation, results, and regression endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AI Agent Reliability Engine",
    description=(
        "An AI-powered reliability engine that understands an agent's capabilities, "
        "automatically generates targeted adversarial tests, safely executes them, "
        "explains failures, scores risk, and continuously converts discovered failures "
        "into regression tests."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Allow the Next.js frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status. 'ok' when healthy.")
    version: str = Field(description="API version.")
    timestamp: str = Field(description="Current server timestamp (ISO 8601).")


class EvaluateRequest(BaseModel):
    """Request body for the evaluate endpoint (Phase 0 scaffold)."""

    agent_id: str = Field(
        description="Identifier of the agent to evaluate.",
        examples=["demo-customer-support-v1"],
    )
    scenario_id: str | None = Field(
        default=None,
        description="Optional specific scenario ID to run.",
    )
    challenge_pack_id: str | None = Field(
        default=None,
        description="Optional challenge pack ID to run.",
    )


class EvaluateResponse(BaseModel):
    """Response from the evaluate endpoint (Phase 0 scaffold)."""

    run_id: str = Field(description="Unique evaluation run identifier.")
    agent_id: str = Field(description="Agent that was evaluated.")
    status: str = Field(description="Evaluation status.")
    message: str = Field(description="Human-readable status message.")
    timestamp: str = Field(description="When the evaluation was initiated.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the service health status. Use this to verify the API is running.",
    tags=["System"],
)
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Returns 200 when the service is running and healthy.
    """
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@app.post(
    "/api/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate an agent (scaffold)",
    description=(
        "Phase 0 scaffold. Accepts an agent identifier and returns a placeholder response. "
        "Full evaluation pipeline will be implemented in Phase 4-5."
    ),
    tags=["Evaluation"],
)
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """
    Evaluate an agent against a challenge pack.

    Phase 0: Returns a placeholder response.
    Phase 4+: Will run the full evaluation pipeline.
    """
    import uuid

    return EvaluateResponse(
        run_id=str(uuid.uuid4()),
        agent_id=request.agent_id,
        status="queued",
        message=(
            f"Evaluation of agent '{request.agent_id}' has been queued. "
            f"Full evaluation pipeline will be available in a future phase."
        ),
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
