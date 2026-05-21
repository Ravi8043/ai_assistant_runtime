"""
Reflection node — LLM-powered evaluation of tool execution results.

Sits after ``tool_executor`` in the graph and decides:
- **Objective met** → route to ``responder``
- **More steps remain, no revision needed** → route back to ``planner``
- **Plan needs revision** → route back to ``planner`` with revision flag
- **Max iterations exceeded** → route to ``error_handler``
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from langchain_core.messages import AIMessage

from assist_runtime.graph.state import GraphState
from assist_runtime.llm.client import UnifiedLLMClient
from assist_runtime.llm.parsing.structured import StructuredOutputParser

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Prompt template
# -------------------------------------------------------------------------

_REFLECTION_PROMPT = """\
You are a critical evaluation agent. Your job is to assess whether a tool
execution successfully accomplished its intended task and whether the
overall objective has been met.

## Overall objective
{objective}

## Current step that was just executed
Step {step_index}: {step_task}
Tool used: {tool_name}

## Tool output
{tool_output}

## Execution Error
{error}

## Full plan status
{plan_status}

## Remaining steps
{remaining_steps}

## Instructions
Evaluate the tool output and respond with **valid JSON only**:

```json
{{
  "is_objective_met": <true if the OVERALL objective is fully satisfied, false otherwise>,
  "step_succeeded": <true if this specific step accomplished its task>,
  "should_revise_plan": <true if the plan needs changes based on new information>,
  "reasoning": "<brief explanation of your assessment>"
}}
```

Be strict: ``is_objective_met`` should only be true when the user's original
request is fully answered.  Even if the current step succeeded, there may
be more steps remaining.

Respond ONLY with valid JSON.
"""


def create_reflection_node(
    llm_client: UnifiedLLMClient,
    parser: StructuredOutputParser,
    max_iterations: int = 10,
) -> Any:
    """
    Factory that returns the reflection node function.

    Parameters
    ----------
    llm_client:
        Unified LLM client for evaluation.
    parser:
        Structured output parser for extracting JSON.
    max_iterations:
        Safety guard — forces termination if the loop count reaches this limit.
    """

    async def reflection_node(state: GraphState) -> dict[str, Any]:
        """
        Evaluate the latest tool output and decide the next routing action.
        """
        try:
            # ---- Iteration guard (checked FIRST) ----
            current_iter = state.get("current_iteration", 0)
            configured_max = state.get("max_iterations", max_iterations)

            if current_iter >= configured_max:
                logger.warning(
                    "Max iterations reached (%d/%d) — forcing termination",
                    current_iter,
                    configured_max,
                )
                return {
                    "error": (
                        f"Maximum iteration limit reached ({current_iter}/{configured_max}). "
                        "The agent was unable to complete the objective within the "
                        "allowed number of tool calls."
                    ),
                    "next_node": "error_handler",
                    "messages": [
                        AIMessage(
                            content=(
                                f"[REFLECTION] Max iterations exceeded "
                                f"({current_iter}/{configured_max})."
                            )
                        ),
                    ],
                }

            # ---- Gather context ----
            plan = state.get("current_plan")
            step_index = state.get("current_step_index", 0)
            tool_output = state.get("tool_output")

            if plan is None:
                return {
                    "error": "Reflection called but no plan exists.",
                    "next_node": "error_handler",
                    "messages": [
                        AIMessage(content="[REFLECTION ERROR] No plan available."),
                    ],
                }

            current_step = (
                plan.steps[step_index]
                if 0 <= step_index < len(plan.steps)
                else None
            )

            # Format tool output
            if isinstance(tool_output, (dict, list)):
                tool_output_str = json.dumps(tool_output, indent=2, default=str)
            else:
                tool_output_str = str(tool_output or "No output")

            # Build plan status summary
            plan_status_lines: list[str] = []
            for s in plan.steps:
                plan_status_lines.append(
                    f"  Step {s.step_id} [{s.status}]: {s.task} (tool: {s.tool_suggested})"
                )
            plan_status = "\n".join(plan_status_lines)

            # Build remaining steps summary
            remaining = [
                s for s in plan.steps
                if s.status == "pending"
            ]
            remaining_str = (
                "\n".join(f"  - Step {s.step_id}: {s.task}" for s in remaining)
                if remaining
                else "None — all steps have been executed."
            )

            # ---- Call LLM for evaluation ----
            prompt = _REFLECTION_PROMPT.format(
                objective=plan.objective,
                step_index=step_index,
                step_task=current_step.task if current_step else "Unknown",
                tool_name=state.get("selected_tool", "Unknown"),
                tool_output=tool_output_str[:2000],  # Truncate for context window
                error=state.get("error") or "None",
                plan_status=plan_status,
                remaining_steps=remaining_str,
            )

            raw_response = await llm_client.generate(prompt=prompt)
            parsed = parser.parse(raw_response)

            if parsed is None:
                logger.warning(
                    "Reflection output unparsable — defaulting to continue"
                )
                parsed = {
                    "is_objective_met": False,
                    "step_succeeded": True,
                    "should_revise_plan": False,
                    "reasoning": "Could not parse reflection output; continuing.",
                }

            is_objective_met = parsed.get("is_objective_met", False)
            should_revise = parsed.get("should_revise_plan", False)
            reasoning = parsed.get("reasoning", "")

            logger.info(
                "Reflection result: objective_met=%s, revise=%s, reasoning=%s",
                is_objective_met,
                should_revise,
                reasoning[:100],
            )

            # ---- Routing decision ----
            if is_objective_met:
                return {
                    "next_node": "responder",
                    "is_complete": True,
                    "messages": [
                        AIMessage(
                            content=(
                                f"[REFLECTION] Objective met. {reasoning}"
                            )
                        ),
                    ],
                }

            # More work needed — loop back to planner
            # (planner will either advance to next step or revise the plan)
            return {
                "next_node": "planner",
                "is_complete": False,
                "messages": [
                    AIMessage(
                        content=(
                            f"[REFLECTION] {'Revision needed. ' if should_revise else 'Continuing. '}"
                            f"{reasoning}"
                        )
                    ),
                ],
            }

        except Exception as exc:
            logger.exception("Reflection node failed")
            return {
                "error": f"Reflection failed: {exc}",
                "next_node": "error_handler",
                "messages": [
                    AIMessage(content=f"[REFLECTION ERROR] {exc}"),
                ],
            }

    return reflection_node
