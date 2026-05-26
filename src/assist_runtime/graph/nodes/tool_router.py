"""
Tool router node — validates and routes the current plan step
to the tool executor.

The planner is responsible for generating:
- tool_suggested
- tool_input

This node ONLY:
- validates tool existence
- extracts tool payload
- routes execution
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from assist_runtime.graph.state import GraphState
from assist_runtime.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def create_tool_router_node(
    tool_registry: ToolRegistry,
) -> Any:

    async def tool_router_node(
        state: GraphState
    ) -> dict[str, Any]:

        try:

            plan = state.get("current_plan")

            step_index = state.get(
                "current_step_index",
                0
            )

            if plan is None:

                return {
                    "error": "No execution plan found.",
                    "next_node": "error_handler",
                    "messages": [
                        AIMessage(
                            content="[TOOL_ROUTER ERROR] Missing execution plan."
                        )
                    ]
                }

            if step_index >= len(plan.steps):

                return {
                    "error": (
                        f"Step index {step_index} "
                        f"out of range."
                    ),
                    "next_node": "error_handler",
                    "messages": [
                        AIMessage(
                            content=(
                                f"[TOOL_ROUTER ERROR] "
                                f"Invalid step index: {step_index}"
                            )
                        )
                    ]
                }

            current_step = plan.steps[step_index]

            tool_name = current_step.tool_suggested

            tool_input = current_step.tool_input or {}

            if not tool_name:

                return {
                    "error": (
                        f"Step {step_index} "
                        f"does not specify a tool."
                    ),
                    "next_node": "error_handler",
                    "messages": [
                        AIMessage(
                            content=(
                                f"[TOOL_ROUTER ERROR] "
                                f"No tool specified for step {step_index}"
                            )
                        )
                    ]
                }

            tool = tool_registry.get_tool(
                tool_name
            )

            if tool is None:

                return {
                    "error": (
                        f"Tool '{tool_name}' "
                        f"is not registered."
                    ),
                    "next_node": "error_handler",
                    "messages": [
                        AIMessage(
                            content=(
                                f"[TOOL_ROUTER ERROR] "
                                f"Tool '{tool_name}' not found."
                            )
                        )
                    ]
                }

            current_step.status = "running"

            logger.info(
                "Routing tool '%s' with input: %s",
                tool_name,
                tool_input
            )

            return {

                "selected_tool": tool_name,

                "tool_input": tool_input,

                "next_node": "tool_executor",

                "messages": [
                    AIMessage(
                        content=(
                            f"[TOOL_ROUTER] "
                            f"Executing '{tool_name}' "
                            f"for step {step_index}"
                        )
                    )
                ]
            }

        except Exception as exc:

            logger.exception(
                "Tool router node failed"
            )

            return {
                "error": f"Tool router failed: {exc}",
                "next_node": "error_handler",
                "messages": [
                    AIMessage(
                        content=(
                            f"[TOOL_ROUTER ERROR] {exc}"
                        )
                    )
                ]
            }

    return tool_router_node