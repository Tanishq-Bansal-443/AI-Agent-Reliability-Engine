"""
LocalMockSandbox — in-process sandbox for Phase 0/1.

Provides a controlled execution environment with:
- Fake customer support state (orders, email log)
- Mock tool implementations for get_order_status, refund_order, send_email
- Execution timeout enforcement
- Complete trace capture via TraceRecorder
- Zero real external calls

This sandbox is NOT a security boundary. It is a development and testing tool.
See ADR-004 in DECISIONS.md.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from packages.core.models.agent import AgentInput, Message
from packages.core.models.scenario import Scenario
from packages.core.models.trace import ExecutionStatus, StepType, Trace, TraceEvent
from packages.sandbox.base import BaseSandbox
from packages.sandbox.tool_runtime import ToolRegistry, ToolRuntime
from packages.tracing.recorder import TraceRecorder


# ---------------------------------------------------------------------------
# Fake environment state
# ---------------------------------------------------------------------------

class FakeOrder:
    """A fake order in the mock customer support environment."""

    def __init__(
        self,
        order_id: str,
        customer_id: str,
        product: str,
        status: str,
        amount: float,
        refundable: bool = True,
    ) -> None:
        self.order_id = order_id
        self.customer_id = customer_id
        self.product = product
        self.status = status
        self.amount = amount
        self.refundable = refundable
        self.refunded = False


class FakeEnvironment:
    """
    The fake customer-support environment state.

    Provides the mock data and logic that sandboxed tool implementations
    will read from and write to. Completely isolated from the real world.
    """

    def __init__(self) -> None:
        self.orders: dict[str, FakeOrder] = {}
        self.email_log: list[dict[str, str]] = []
        self.event_log: list[dict[str, Any]] = []
        self._populate_initial_state()

    def _populate_initial_state(self) -> None:
        """Seed the environment with realistic fake data."""
        orders = [
            FakeOrder("ORD-1001", "CUST-001", "Wireless Headphones", "delivered", 89.99),
            FakeOrder("ORD-1002", "CUST-002", "Laptop Stand", "shipped", 45.00),
            FakeOrder("ORD-1003", "CUST-003", "USB-C Hub", "processing", 29.99),
            FakeOrder("ORD-4812", "CUST-004", "Mechanical Keyboard", "delivered", 149.99),
            FakeOrder("ORD-9999", "CUST-005", "Premium Subscription", "active", 299.00, refundable=False),
        ]
        for order in orders:
            self.orders[order.order_id] = order

    def reset(self) -> None:
        """Reset to initial state."""
        self.orders.clear()
        self.email_log.clear()
        self.event_log.clear()
        self._populate_initial_state()

    def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Record an environment-level event."""
        self.event_log.append({"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})


def _build_tool_registry(env: FakeEnvironment, recorder: TraceRecorder) -> ToolRegistry:
    """
    Build a ToolRegistry with mock customer-support tool implementations.

    All implementations operate against the FakeEnvironment.
    None of them make real external calls.
    """
    registry = ToolRegistry()

    def get_order_status(order_id: str) -> dict[str, Any]:
        """Look up the status of an order."""
        order = env.orders.get(order_id)
        if order is None:
            return {"error": f"Order {order_id} not found.", "found": False}
        env.log_event("order_status_lookup", {"order_id": order_id})
        return {
            "found": True,
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "product": order.product,
            "status": order.status,
            "amount": order.amount,
            "refunded": order.refunded,
        }

    def refund_order(order_id: str) -> dict[str, Any]:
        """
        Issue a refund for an order.

        This is a destructive, sensitive operation.
        The agent must verify customer identity before calling this.
        """
        order = env.orders.get(order_id)
        if order is None:
            return {"error": f"Order {order_id} not found.", "success": False}
        if not order.refundable:
            return {
                "error": f"Order {order_id} is not eligible for a refund.",
                "success": False,
            }
        if order.refunded:
            return {
                "error": f"Order {order_id} has already been refunded.",
                "success": False,
            }

        order.refunded = True
        order.status = "refunded"
        env.log_event(
            "refund_issued",
            {"order_id": order_id, "amount": order.amount, "customer_id": order.customer_id},
        )
        return {
            "success": True,
            "order_id": order_id,
            "refund_amount": order.amount,
            "message": f"Refund of ${order.amount:.2f} issued for order {order_id}.",
        }

    def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
        """
        Send an email notification.

        This is a sensitive operation — emails go to real customers in production.
        In the mock environment, emails are logged but not sent.
        """
        email = {"to": to, "subject": subject, "body": body, "sent_at": datetime.now(timezone.utc).isoformat()}
        env.email_log.append(email)
        env.log_event("email_sent", {"to": to, "subject": subject})
        return {
            "success": True,
            "message": f"Email sent to {to}: {subject}",
        }

    registry.register("get_order_status", get_order_status)
    registry.register("refund_order", refund_order)
    registry.register("send_email", send_email)

    return registry


# ---------------------------------------------------------------------------
# LocalMockSandbox
# ---------------------------------------------------------------------------

class LocalMockSandbox(BaseSandbox):
    """
    In-process sandbox for Phase 0/1 evaluation.

    Provides a controlled execution environment backed by FakeEnvironment.
    All tool calls are routed through ToolRuntime — no monkey-patching.

    This sandbox is for development and MVP testing only.
    It is NOT a real security boundary (see ADR-004).
    """

    def __init__(self) -> None:
        self._env = FakeEnvironment()

    @property
    def sandbox_type(self) -> str:
        return "local_mock"

    @property
    def environment(self) -> FakeEnvironment:
        """Access the fake environment (for test inspection)."""
        return self._env

    async def reset(self) -> None:
        """Reset the fake environment to its initial state."""
        self._env.reset()

    async def execute(
        self,
        scenario: Scenario,
        adapter: "BaseAgentAdapter",  # type: ignore[name-defined]
    ) -> Trace:
        """
        Execute one turn/scenario against one adapter in the mock environment.

        Flow:
            1. Create a fresh TraceRecorder.
            2. Build ToolRegistry with mock implementations.
            3. Create ToolRuntime wrapping the registry.
            4. Build AgentInput from the scenario.
            5. Run the adapter, capturing events.
            6. Handle timeouts and errors.
            7. Return the completed Trace.
        """
        run_id = str(uuid4())
        recorder = TraceRecorder(
            run_id=run_id,
            agent_id=adapter.agent_id,
            agent_version=adapter.agent_version,
            scenario_id=scenario.id,
            scenario_name=scenario.name,
        )

        # Record the current user input for this execution step
        user_message = scenario.turns[-1].content if scenario.turns else scenario.initial_message
        recorder.record_event(
            step_type=StepType.USER_INPUT,
            input_data={"message": user_message, "scenario": scenario.name},
            output_data={},
        )

        # Build tool infrastructure
        registry = _build_tool_registry(self._env, recorder)
        runtime = ToolRuntime(registry)

        # Build agent input from scenario.turns if present, otherwise fall back to initial_message
        if scenario.turns:
            messages = [Message(role=t.role, content=t.content) for t in scenario.turns]
        else:
            messages = [Message(role="user", content=scenario.initial_message)]

        agent_input = AgentInput(
            conversation_id=run_id,
            messages=messages,
            metadata={
                "scenario_id": scenario.id,
                "scenario_name": scenario.name,
                "sandbox_type": self.sandbox_type,
            },
        )

        # Enforce sandbox execution timeout
        timeout = scenario.resource_limits.timeout_seconds
        start_env_event_count = len(self._env.event_log)
        
        exc_to_raise = None
        agent_output = None
        try:
            agent_output = await asyncio.wait_for(
                adapter.run(agent_input, runtime),
                timeout=float(timeout),
            )
        except asyncio.TimeoutError as e:
            exc_to_raise = e
        except Exception as e:
            exc_to_raise = e

        # Record tool calls from the runtime
        for tool_call in runtime.call_history:
            recorder.record_event(
                step_type=StepType.TOOL_CALL,
                input_data={
                    "tool_name": tool_call.tool_name,
                    "arguments": tool_call.arguments,
                },
                output_data={},
                duration_ms=0,
            )
            recorder.record_event(
                step_type=StepType.TOOL_RESULT,
                input_data={"tool_name": tool_call.tool_name},
                output_data={
                    "result": tool_call.result,
                    "error": tool_call.error,
                    "success": tool_call.success,
                },
                duration_ms=tool_call.duration_ms,
            )

        # Record environment changes that occurred during this turn
        new_env_events = self._env.event_log[start_env_event_count:]
        for env_event in new_env_events:
            recorder.record_event(
                step_type=StepType.ENVIRONMENT_CHANGE,
                input_data={},
                output_data=env_event,
            )

        if exc_to_raise is not None:
            if isinstance(exc_to_raise, asyncio.TimeoutError):
                recorder.record_event(
                    step_type=StepType.ERROR,
                    input_data={},
                    output_data={"error": f"Scenario execution timed out after {timeout} seconds."},
                )
                return recorder.finish(
                    status=ExecutionStatus.TIMEOUT,
                    error=f"Scenario execution timed out after {timeout} seconds.",
                )
            else:
                recorder.record_event(
                    step_type=StepType.ERROR,
                    input_data={},
                    output_data={"error": str(exc_to_raise)},
                )
                return recorder.finish(
                    status=ExecutionStatus.ERROR,
                    error=str(exc_to_raise),
                )

        # Record final response
        recorder.record_event(
            step_type=StepType.FINAL_RESPONSE,
            input_data={},
            output_data={
                "response": agent_output.response,
                "tool_calls_made": [
                    {"tool": tc.tool_name, "args": tc.arguments}
                    for tc in agent_output.tool_calls_made
                ],
            },
        )

        return recorder.finish(status=ExecutionStatus.SUCCESS)
