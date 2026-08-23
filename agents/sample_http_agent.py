import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
@app.post("/", response_model=ChatResponse)
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


@app.get("/agent")
@app.get("/metadata")
async def get_agent_details():
    """
    Expose prompt and tools of the agent to the profiler.
    """
    from agents.demo_customer_support.agent import SYSTEM_PROMPT
    from agents.demo_customer_support.tools import CUSTOMER_SUPPORT_TOOLS
    return {
        "id": "sample_http_agent",
        "name": "Sample HTTP Agent",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [t.model_dump() for t in CUSTOMER_SUPPORT_TOOLS],
        "version": "1.0.0"
    }


if __name__ == "__main__":
    print("Starting sample HTTP agent on http://127.0.0.1:5000")
    uvicorn.run(app, host="127.0.0.1", port=5000)
