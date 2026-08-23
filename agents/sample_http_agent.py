"""
Sample HTTP Agent — a minimal FastAPI agent for testing the Bring Your Own Agent (BYOA) feature.

Start with:
    python -m agents.sample_http_agent
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Sample HTTP Agent",
    description="A tiny external agent endpoint that can be queried by the Reliability Engine.",
    version="1.0.0"
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Handle incoming messages.
    Includes simple predefined logic to satisfy scenario expectations (e.g. status vs refund).
    """
    msg_lower = request.message.lower()

    if "refund" in msg_lower and "immediately" in msg_lower:
        # Simulate vulnerable behavior or quick agreement to refund
        reply = "I have successfully processed a refund of $149.99 for your order as requested."
    elif "status" in msg_lower:
        reply = "I checked your order ORD-1002. Its current status is: shipped."
    else:
        reply = f"Hello! I am your custom HTTP agent. I received your message: '{request.message}'"

    return ChatResponse(response=reply)


if __name__ == "__main__":
    print("Starting sample HTTP agent on http://127.0.0.1:5000")
    uvicorn.run(app, host="127.0.0.1", port=5000)
