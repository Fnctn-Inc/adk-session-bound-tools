from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import AsyncIterator
from types import MappingProxyType

from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

APP_NAME = "adk_session_bound_tools"
ORDERS = MappingProxyType(
    {
        ("alex", "ord-1001"): "in_transit",
        ("robin", "ord-2001"): "delivered",
    }
)


def lookup_order_status(order_id: str, tool_context: ToolContext) -> dict[str, str]:
    """Look up delivery status for an order belonging to the current caller."""
    # ADK supplies this context from the session identified by the application.
    status = ORDERS.get((tool_context.user_id, order_id))
    if status is None:
        return {"outcome": "not_found"}
    return {"outcome": "found", "order_id": order_id, "delivery_status": status}


class OrderFixtureModel(BaseLlm):
    """Request a real ADK tool call from the supplied order reference."""

    model: str = "offline-order-fixture"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncIterator[LlmResponse]:
        latest = (llm_request.contents[-1].parts or [])[-1]
        if latest.function_response is not None:
            part = types.Part.from_text(
                text=json.dumps(latest.function_response.response)
            )
        else:
            part = types.Part.from_function_call(
                name="lookup_order_status", args={"order_id": latest.text or ""}
            )
        yield LlmResponse(
            content=types.Content(role="model", parts=[part]),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=0, candidates_token_count=0, total_token_count=0
            ),
        )


def build_runner() -> Runner:
    agent = LlmAgent(
        name=APP_NAME,
        model=OrderFixtureModel(),
        instruction="Look up delivery status for the requested order.",
        tools=[FunctionTool(lookup_order_status)],
    )
    return Runner(
        app_name=APP_NAME, agent=agent, session_service=InMemorySessionService()
    )


async def run_lookup(
    runner: Runner, *, user_id: str, session_id: str, order_id: str
) -> dict[str, str]:
    """Run the agent and return the actual tool response from its event stream."""
    message = types.Content(role="user", parts=[types.Part.from_text(text=order_id)])
    result = None
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message
    ):
        for reply in event.get_function_responses():
            if reply.name == "lookup_order_status":
                result = reply.response
    if result is None:
        raise RuntimeError("The agent did not return an order lookup result")
    return result


async def run_demo(caller: str, order_ids: list[str]) -> None:
    runner = build_runner()
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=caller
    )
    for order_id in order_ids:
        result = await run_lookup(
            runner, user_id=caller, session_id=session.id, order_id=order_id
        )
        print(f"{order_id}: {json.dumps(result, sort_keys=True)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline ADK order lookup.")
    parser.add_argument(
        "--caller", choices=("alex", "robin"), default="alex", help="Demo caller"
    )
    parser.add_argument(
        "order_ids",
        metavar="ORDER_ID",
        nargs="*",
        help="Order references to look up",
    )
    args = parser.parse_args()
    asyncio.run(
        run_demo(args.caller, args.order_ids or ["ord-1001", "ord-2001", "ord-9999"])
    )


if __name__ == "__main__":
    main()
