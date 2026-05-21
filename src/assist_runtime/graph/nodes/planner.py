"""
Planner node — the brain of the agent.

Responsibilities:
1. **First invocation** (no existing plan): Analyse the user's request and
   generate a structured ``ExecutionPlan`` with ordered ``PlanStep`` objects.
2. **Subsequent invocations** (looping back from reflection): Read the
   existing plan + tool outputs, advance ``current_step_index``, or revise
   the plan if reflection flagged issues.
3. Set ``next_node`` to ``"tool_router"`` (needs tools) or ``"responder"``
   (conversational / objective already met).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, cast

from langchain_core.messages import AIMessage, HumanMessage

from assist_runtime.graph.state import ExecutionPlan, GraphState, PlanStep
from assist_runtime.llm.client import UnifiedLLMClient
from assist_runtime.llm.parsing.structured import StructuredOutputParser
from assist_runtime.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Prompt templates
# -------------------------------------------------------------------------

_INITIAL_PLAN_PROMPT = """\
You are an expert AI planning agent. Your job is to analyse the user's
request and decide the best strategy to fulfil it.

## Available tools
{tool_descriptions}

## User request
{input_text}

## Instructions
1. If the request can be answered conversationally (greetings, general
   knowledge, opinions, etc.) WITHOUT any tool, respond with:
   ```json
   {{
     "requires_tools": false,
     "objective": "<one-line summary of the user's goal>",
     "steps": []
   }}
   ```

2. If the request requires one or more tool calls, create a step-by-step
   plan.  Each step MUST include:
- task
- tool_suggested
- tool_input

tool_input must contain the exact arguments required for the tool.

Examples:

{{
  "step_id": 0,
  "task": "Read ORCHESTRATION.md",
  "tool_suggested": "read_file",
  "tool_input": {{
    "path": "ORCHESTRATION.md"
  }}
}}

{{
  "step_id": 1,
  "task": "List current directory",
  "tool_suggested": "list_dir",
  "tool_input": {{
    "path": "."
  }}
}}

Respond ONLY with valid JSON. Do not include any reasoning, conversational text, or markdown formatting (like ```json). Just the raw JSON object starting with {{ and ending with }}.
"""

_REPLAN_PROMPT = """\
You are an expert AI planning agent reviewing an in-progress execution.

## Original objective
{objective}

## Current plan (with statuses)
{plan_json}

## Latest tool output
{tool_output}

## Reflection feedback
{reflection_feedback}

## Available tools
{tool_descriptions}

## Instructions
Decide what to do next.  Respond with **valid JSON only**:

- If the objective is already satisfied, respond:
  ```json
  {{"action": "complete"}}
  ```

- If the current plan still has pending steps and no revision is needed,
  respond:
  ```json
  {{"action": "continue"}}
  ```

- If the plan needs revision (steps failed, new information changes
  the approach, etc.), respond with a **full replacement plan**:
  ```json
  {{
    "action": "revise",
    "objective": "<updated objective if needed>",
    "steps": [
      {{"step_id": 0, "task": "...", "tool_suggested": "...", "tool_input": {{"key": "value"}}}},
      ...
    ]
  }}
  ```

Respond ONLY with valid JSON. Do not include any reasoning, conversational text, or markdown formatting. Just the raw JSON object starting with {{ and ending with }}.
"""


def _format_tool_descriptions(registry: ToolRegistry) -> str:
    """Build a human-readable list of available tools for the LLM prompt."""
    tools = registry.get_all_tools()
    if not tools:
        return "(no tools registered)"
    lines: list[str] = []
    for name, tool in tools.items():
        lines.append(f"- **{name}**: {tool.description}")
    return "\n".join(lines)


def create_planner_node(
    llm_client: UnifiedLLMClient,
    parser: StructuredOutputParser,
    tool_registry: ToolRegistry,
) -> Any:
    """
    Factory that returns the planner node function.

    Parameters
    ----------
    llm_client:
        Unified LLM client for generating plans.
    parser:
        Structured output parser for extracting JSON from LLM responses.
    tool_registry:
        Tool registry used to build the tool descriptions prompt section.
    """

    async def planner_node(state: GraphState) -> dict[str, Any]:
        """
        Generate or advance the execution plan.
        """
        try:
            existing_plan = state.get("current_plan")
            tool_descs = _format_tool_descriptions(tool_registry)

            # ---------------------------------------------------------
            # CASE 1: First invocation — no plan exists yet
            # ---------------------------------------------------------
            if existing_plan is None:
                prompt = _INITIAL_PLAN_PROMPT.format(
                    tool_descriptions=tool_descs,
                    input_text=state.get("input_text", ""),
                )

                raw_response = await llm_client.generate(prompt=prompt)
                parsed = parser.parse(raw_response)

                if parsed is None:
                    logger.warning(
                        "Planner returned unparsable output, falling back to responder"
                    )
                    return {
                        "next_node": "responder",
                        "messages": [
                            HumanMessage(content=state.get("input_text", "")),
                            AIMessage(content="[PLANNER] Could not generate a structured plan; routing to direct response."),
                        ],
                    }
                requires_tools = parsed.get("requires_tools", False)

                if not requires_tools or not parsed.get("steps"):
                    # Conversational — no tools needed
                    logger.info("Planner decided: no tools required")
                    return {
                        "next_node": "responder",
                        "current_plan": ExecutionPlan(
                            objective=parsed.get("objective", state.get("input_text", "")),
                            steps=[],
                            revised_count=0,
                        ),
                        "messages": [
                            HumanMessage(content=state.get("input_text", "")),
                            AIMessage(content=f"[PLANNER] No tools needed. Objective: {parsed.get('objective', '')}"),
                        ],
                    }

                # Tools required — build execution plan
                raw_steps = cast(list[dict[str, Any]], parsed.get("steps", []))
                plan = ExecutionPlan(
                    objective=parsed.get("objective", "Unknown objective"),
                    steps=[
                        PlanStep(
                            step_id=s.get("step_id", idx),
                            task=s.get("task", "Unknown task"),
                            tool_suggested=s.get("tool_suggested"),
                            tool_input=s.get("tool_input"),
                            status="pending",
                        )
                        for idx, s in enumerate(raw_steps)
                    ],
                    revised_count=0,
                )

                logger.info(
                    "Planner created plan with %d steps: %s",
                    len(plan.steps),
                    plan.objective,
                )

                return {
                    "current_plan": plan,
                    "current_step_index": 0,  # Reducer will set to 0 on first pass
                    "next_node": "tool_router",
                    "is_complete": False,
                    "messages": [
                        HumanMessage(content=state.get("input_text", "")),
                        AIMessage(
                            content=(
                                f"[PLANNER] Created plan with {len(plan.steps)} step(s). "
                                f"Objective: {plan.objective}"
                            )
                        ),
                    ],
                }

            # ---------------------------------------------------------
            # CASE 2: Subsequent invocation — plan already exists
            # ---------------------------------------------------------
            current_idx = state.get("current_step_index", 0)

            # Gather context for replan prompt
            tool_output = state.get("tool_output")
            tool_output_str = (
                json.dumps(tool_output, indent=2, default=str)
                if isinstance(tool_output, (dict, list))
                else str(tool_output or "N/A")
            )

            # Extract last reflection message if present
            messages = state.get("messages", [])
            reflection_feedback = "No reflection feedback available."
            for msg in reversed(messages):
                content = getattr(msg, "content", "")
                if "[REFLECTION]" in content:
                    reflection_feedback = content
                    break

            prompt = _REPLAN_PROMPT.format(
                objective=existing_plan.objective,
                plan_json=json.dumps(
                    existing_plan.model_dump(), indent=2, default=str
                ),
                tool_output=tool_output_str,
                reflection_feedback=reflection_feedback,
                tool_descriptions=tool_descs,
            )

            raw_response = await llm_client.generate(prompt=prompt)
            parsed = parser.parse(raw_response)

            if parsed is None:
                logger.warning("Replan output unparsable — continuing with existing plan")
                parsed = {"action": "continue"}

            action = parsed.get("action", "continue")

            # ---- Action: complete ----
            if action == "complete":
                logger.info("Planner determined objective is met")
                return {
                    "next_node": "responder",
                    "is_complete": True,
                    "messages": [
                        AIMessage(content="[PLANNER] Objective satisfied — routing to responder."),
                    ],
                }

            # ---- Action: revise ----
            if action == "revise":
                revised_steps = cast(list[dict[str, Any]], parsed.get("steps", []))
                revised_plan = ExecutionPlan(
                    objective=parsed.get("objective", existing_plan.objective),
                    steps=[
                        PlanStep(
                            step_id=s.get("step_id", idx),
                            task=s.get("task", "Unknown task"),
                            tool_suggested=s.get("tool_suggested"),
                            tool_input=s.get("tool_input"),
                            status="pending",
                        )
                        for idx, s in enumerate(revised_steps)
                    ],
                    revised_count=existing_plan.revised_count + 1,
                )

                logger.info(
                    "Planner revised plan (revision #%d) with %d steps",
                    revised_plan.revised_count,
                    len(revised_plan.steps),
                )

                # Reset step index: we use a negative offset to reset to 0
                # because the reducer is additive.
                reset_offset = -current_idx

                return {
                    "current_plan": revised_plan,
                    "current_step_index": reset_offset,
                    "next_node": "tool_router",
                    "is_complete": False,
                    "messages": [
                        AIMessage(
                            content=(
                                f"[PLANNER] Revised plan (#{revised_plan.revised_count}) "
                                f"with {len(revised_plan.steps)} step(s)."
                            )
                        ),
                    ],
                }

            # ---- Action: continue (default) ----
            # Advance to the next pending step
            next_idx = len(existing_plan.steps)
            for i, step in enumerate(existing_plan.steps):
                if i >= current_idx and step.status == "pending":
                    next_idx = i
                    break

            if next_idx >= len(existing_plan.steps):
                # All steps done — route to responder
                logger.info("All plan steps completed — routing to responder")
                return {
                    "next_node": "responder",
                    "is_complete": True,
                    "messages": [
                        AIMessage(content="[PLANNER] All steps completed — routing to responder."),
                    ],
                }

            # Calculate the additive offset needed for the reducer
            index_delta = next_idx - current_idx

            logger.info(
                "Planner continuing to step %d/%d: %s",
                next_idx,
                len(existing_plan.steps),
                existing_plan.steps[next_idx].task,
            )

            return {
                "current_step_index": index_delta,
                "next_node": "tool_router",
                "is_complete": False,
                "messages": [
                    AIMessage(
                        content=(
                            f"[PLANNER] Continuing to step {next_idx}: "
                            f"{existing_plan.steps[next_idx].task}"
                        )
                    ),
                ],
            }

        except Exception as exc:
            logger.exception("Planner node failed")
            return {
                "error": f"Planner failed: {exc}",
                "next_node": "error_handler",
                "messages": [
                    AIMessage(content=f"[PLANNER ERROR] {exc}"),
                ],
            }

    return planner_node
