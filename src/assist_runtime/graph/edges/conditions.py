"""
Conditional edge functions for the LangGraph orchestration graph.

Each function reads the current ``GraphState`` and returns the **name**
of the next node to route to.  These are used with
``graph.add_conditional_edges(source_node, condition_fn, mapping)``.
"""

from __future__ import annotations

import logging
from typing import Literal

from assist_runtime.graph.state import GraphState

logger = logging.getLogger(__name__)

# Type aliases for the possible routing targets
PlannerRoute = Literal["tool_router", "responder", "error_handler"]
ReflectionRoute = Literal["planner", "responder", "error_handler"]


def route_after_planner(state: GraphState) -> PlannerRoute:
    """
    Conditional edge after the **planner** node.

    Reads ``state["next_node"]`` which the planner sets to one of:
    - ``"tool_router"`` — plan requires tool execution
    - ``"responder"``   — conversational response / objective already met
    - ``"error_handler"`` — an error occurred during planning

    Falls back to ``"responder"`` if ``next_node`` is not set.
    """
    next_node = state.get("next_node")

    if next_node in ("tool_router", "responder", "error_handler"):
        logger.debug("route_after_planner → %s", next_node)
        return next_node  # type: ignore[return-value]

    # Safety fallback — if planner didn't set next_node, go to responder
    logger.warning(
        "route_after_planner: unexpected next_node=%r, defaulting to 'responder'",
        next_node,
    )
    return "responder"


def route_after_reflection(state: GraphState) -> ReflectionRoute:
    """
    Conditional edge after the **reflection** node.

    Reads ``state["next_node"]`` which the reflection node sets to one of:
    - ``"planner"``       — more work needed, loop back
    - ``"responder"``     — objective is met, synthesise final answer
    - ``"error_handler"`` — max iterations exceeded or reflection error

    Falls back to ``"error_handler"`` if ``next_node`` is not set.
    """
    next_node = state.get("next_node")

    if next_node in ("planner", "responder", "error_handler"):
        logger.debug("route_after_reflection → %s", next_node)
        return next_node  # type: ignore[return-value]

    # Safety fallback — if reflection didn't set next_node, treat as error
    logger.warning(
        "route_after_reflection: unexpected next_node=%r, defaulting to 'error_handler'",
        next_node,
    )
    return "error_handler"
