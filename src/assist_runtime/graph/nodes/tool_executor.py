"""
Tool executor node — actually runs the selected tool.

Delegates execution to the existing ``ToolExecutor`` infrastructure which
wraps the ``ToolRegistry``.  Captures the output (or exception) and
updates the plan step status accordingly.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from langchain_core.messages import AIMessage

from assist_runtime.graph.state import GraphState
from assist_runtime.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)


def create_tool_executor_node(
    tool_executor: ToolExecutor,
) -> Any:
    """
    Factory that returns the tool-executor node function.

    Parameters
    ----------
    tool_executor:
        The existing ``ToolExecutor`` instance that wraps ``ToolRegistry``.
    """

    async def tool_executor_node(state: GraphState) -> dict[str, Any]:
        """
        Run ``tool_executor.execute(selected_tool, tool_input)`` and store
        the result in state.
        """
        tool_name = state.get("selected_tool")
        tool_input = state.get("tool_input") or {}

        if not tool_name:
            return {
                "error": "Tool executor called but no tool selected.",
                "next_node": "error_handler",
                "current_iteration": 1,
                "messages": [
                    AIMessage(content="[TOOL_EXECUTOR ERROR] No tool selected."),
                ],
            }

        try:
            logger.info(
                "Executing tool '%s' with input: %s",
                tool_name,
                json.dumps(tool_input, default=str)[:300],
            )

            # ---- Run the tool ----
            result = tool_executor.execute(tool_name, tool_input)

            # ---- Update plan step status ----
            plan = state.get("current_plan")
            step_index = state.get("current_step_index", 0)
            if plan and 0 <= step_index < len(plan.steps):
                plan.steps[step_index].status = "completed"

            # Format result for message
            if isinstance(result, (dict, list)):
                result_str = json.dumps(result, indent=2, default=str)
            else:
                result_str = str(result)

            logger.info(
                "Tool '%s' succeeded (%d chars output)",
                tool_name,
                len(result_str),
            )

            return {
                "tool_output": result,
                "current_iteration": 1,     # Reducer adds 1 to total loop count
                "error": None,              # Clear any previous errors
                "messages": [
                    AIMessage(
                        content=(
                            f"[TOOL_EXECUTOR] Tool '{tool_name}' completed successfully.\n"
                            f"Output:\n{result_str[:1000]}"
                        )
                    ),
                ],
            }

        except Exception as exc:
            logger.exception("Tool '%s' execution failed", tool_name)

            # Mark step as failed
            plan = state.get("current_plan")
            step_index = state.get("current_step_index", 0)
            if plan and 0 <= step_index < len(plan.steps):
                plan.steps[step_index].status = "failed"

            return {
                "error": f"Tool '{tool_name}' crashed: {exc}",
                "tool_output": None,
                "current_iteration": 1,     # Count even on failure to prevent infinite loops
                "next_node": "error_handler",
                "messages": [
                    AIMessage(
                        content=f"[TOOL_EXECUTOR ERROR] Tool '{tool_name}' failed: {exc}"
                    ),
                ],
            }

    return tool_executor_node