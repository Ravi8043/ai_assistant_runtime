"""
Responder node — synthesises the final user-facing response.

Reached in two scenarios:
1. **No tools needed**: the planner decided the query is conversational and
   routed directly here.
2. **After tool execution**: reflection determined the objective is met and
   all tool outputs are available in state.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from langchain_core.messages import AIMessage

from assist_runtime.graph.state import GraphState
from assist_runtime.llm.client import UnifiedLLMClient

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Prompt template
# -------------------------------------------------------------------------

_RESPONDER_PROMPT = """\
You are a helpful AI assistant named Jarvis. Your job is to produce a clear,
well-structured final answer for the user.

## User's original request
{input_text}

## Conversation history
{history}

## Execution context
{execution_context}

## Instructions
- Synthesise all available information into a single, coherent response.
- If tools were executed, incorporate their results naturally — do NOT
  just dump raw JSON.
- Be concise but thorough.  Use markdown formatting where helpful.
- If an error occurred during execution, acknowledge it and explain what
  you were able to accomplish.
- Do NOT mention internal implementation details (plans, steps, tool names)
  unless directly relevant to the user's question.

Respond now:
"""


def create_responder_node(
    llm_client: UnifiedLLMClient,
) -> Any:
    """
    Factory that returns the responder node function.

    Parameters
    ----------
    llm_client:
        The unified LLM client used to generate the final response.
    """

    async def responder_node(state: GraphState) -> dict[str, Any]:
        """
        Generate the final user-facing response and terminate the workflow.
        """
        try:
            # ---- Build execution context summary ----
            execution_parts: list[str] = []

            plan = state.get("current_plan")
            if plan is not None:
                execution_parts.append(f"Objective: {plan.objective}")
                completed = [s for s in plan.steps if s.status == "completed"]
                if completed:
                    execution_parts.append(
                        f"Completed {len(completed)}/{len(plan.steps)} planned steps."
                    )

            tool_output = state.get("tool_output")
            if tool_output is not None:
                if isinstance(tool_output, (dict, list)):
                    execution_parts.append(
                        f"Last tool output:\n```json\n{json.dumps(tool_output, indent=2, default=str)}\n```"
                    )
                else:
                    execution_parts.append(f"Last tool output:\n{tool_output}")

            error = state.get("error")
            if error:
                execution_parts.append(f"Error encountered: {error}")

            execution_context = "\n".join(execution_parts) if execution_parts else "No tools were used."

            # ---- Build conversation history summary ----
            messages = state.get("messages", [])
            history_lines: list[str] = []
            for msg in messages[-10:]:  # Last 10 messages for context window
                role = getattr(msg, "type", "unknown")
                content = getattr(msg, "content", "")
                if content:
                    history_lines.append(f"[{role}]: {content[:500]}")

            history = "\n".join(history_lines) if history_lines else "No prior conversation."

            # ---- Call LLM ----
            prompt = _RESPONDER_PROMPT.format(
                input_text=state.get("input_text", ""),
                history=history,
                execution_context=execution_context,
            )

            response = await llm_client.generate(prompt=prompt)

            logger.info("Responder generated final response (%d chars)", len(response))

            return {
                "final_response": response,
                "is_complete": True,
                "messages": [AIMessage(content=response)],
            }

        except Exception as exc:
            logger.exception("Responder node failed")
            return {
                "error": f"Responder failed: {exc}",
                "next_node": "error_handler",
                "final_response": None,
                "is_complete": False,
                "messages": [
                    AIMessage(content=f"[RESPONDER ERROR] {exc}")
                ],
            }

    return responder_node
