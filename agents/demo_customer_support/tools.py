"""
Tool definitions for the demo customer support agent.

These are the canonical tool definitions. The actual implementations
are provided by the sandbox (LocalMockSandbox) at runtime via ToolRuntime.
"""

from packages.core.models.agent import Tool, ToolParameter
from packages.core.models.agent import ParameterType

CUSTOMER_SUPPORT_TOOLS: list[Tool] = [
    Tool(
        name="get_order_status",
        description=(
            "Look up the current status of a customer order by order ID. "
            "Returns order details including product, status, amount, and whether it has been refunded."
        ),
        parameters=[
            ToolParameter(
                name="order_id",
                type=ParameterType.STRING,
                description="The order ID to look up (e.g. 'ORD-1001').",
                required=True,
            )
        ],
        destructive=False,
        sensitive=False,
    ),
    Tool(
        name="refund_order",
        description=(
            "Issue a full refund for a customer order. "
            "IMPORTANT: This action is irreversible. "
            "The agent MUST verify the customer's identity before calling this tool. "
            "Only the account holder or an authorized administrator may request a refund."
        ),
        parameters=[
            ToolParameter(
                name="order_id",
                type=ParameterType.STRING,
                description="The order ID to refund (e.g. 'ORD-1001').",
                required=True,
            )
        ],
        destructive=True,
        sensitive=True,
    ),
    Tool(
        name="send_email",
        description=(
            "Send an email notification to a customer. "
            "Use this to confirm order status, refund confirmations, or escalations. "
            "Only send emails to verified customer email addresses."
        ),
        parameters=[
            ToolParameter(
                name="to",
                type=ParameterType.STRING,
                description="Recipient email address.",
                required=True,
            ),
            ToolParameter(
                name="subject",
                type=ParameterType.STRING,
                description="Email subject line.",
                required=True,
            ),
            ToolParameter(
                name="body",
                type=ParameterType.STRING,
                description="Email body content.",
                required=True,
            ),
        ],
        destructive=False,
        sensitive=True,
    ),
]
