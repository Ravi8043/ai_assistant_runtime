"""
Graph builder — wires up the complete LangGraph ``StateGraph``.

Provides a single ``build_graph(...)`` function that accepts all
dependencies, constructs the node/edge topology, and returns a compiled
graph ready for invocation.

Topology::

    START → planner ─┬─ tool_router → tool_executor → reflection ─┬─ planner (loop)
                     │                                             ├─ responder → END
                     ├─ responder → END                            └─ error_handler → END
                     └─ error_handler → END
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from assist_runtime.graph.state import GraphState

from langgraph.checkpoint.memory import InMemorySaver

# Node factories
from assist_runtime.graph.nodes.planner import create_planner_node
from assist_runtime.graph.nodes.tool_router import create_tool_router_node
from assist_runtime.graph.nodes.tool_executor import create_tool_executor_node
from assist_runtime.graph.nodes.reflection import create_reflection_node
from assist_runtime.graph.nodes.responder import create_responder_node
from assist_runtime.graph.nodes.error_node import create_error_handler_node

# Edge conditions
from assist_runtime.graph.edges.conditions import (
    route_after_planner,
    route_after_reflection,
)

# Dependencies
from assist_runtime.llm.client import UnifiedLLMClient
from assist_runtime.llm.parsing.structured import StructuredOutputParser
from assist_runtime.tools.executor import ToolExecutor
from assist_runtime.tools.registry import ToolRegistry
from IPython.display import display, Image


logger = logging.getLogger(__name__)


def build_graph(
    llm_client: UnifiedLLMClient,
    tool_executor: ToolExecutor,
    tool_registry: ToolRegistry,
    parser: StructuredOutputParser | None = None,
    max_iterations: int = 10,
) -> Any:
    """
    Construct and compile the full agent orchestration graph.

    Parameters
    ----------
    llm_client:
        The unified LLM client injected into all LLM-calling nodes.
    tool_executor:
        Wraps ``ToolRegistry`` — used by the tool-executor node.
    tool_registry:
        Provides tool metadata — used by planner and tool-router nodes.
    parser:
        Structured output parser for JSON extraction. Created automatically
        if not provided.
    max_iterations:
        Maximum number of tool-execution cycles before forced termination.

    Returns
    -------
    CompiledGraph
        A compiled LangGraph ``StateGraph`` ready for ``.invoke()`` or
        ``.ainvoke()`` calls.
    """
    if parser is None:
        parser = StructuredOutputParser()

    # =================================================================
    # 1. CREATE NODE FUNCTIONS via factories
    # =================================================================

    planner_fn = create_planner_node(
        llm_client=llm_client,
        parser=parser,
        tool_registry=tool_registry,
    )

    tool_router_fn = create_tool_router_node(
        tool_registry=tool_registry,
    )

    tool_executor_fn = create_tool_executor_node(
        tool_executor=tool_executor,
    )

    reflection_fn = create_reflection_node(
        llm_client=llm_client,
        parser=parser,
        max_iterations=max_iterations,
    )

    responder_fn = create_responder_node(
        llm_client=llm_client,
    )

    error_handler_fn = create_error_handler_node()

    # =================================================================
    # 2. BUILD THE STATE GRAPH
    # =================================================================

    graph = StateGraph(GraphState)

    # ---- Add nodes ----
    graph.add_node("planner", planner_fn)
    graph.add_node("tool_router", tool_router_fn)
    graph.add_node("tool_executor", tool_executor_fn)
    graph.add_node("reflection", reflection_fn)
    graph.add_node("responder", responder_fn)
    graph.add_node("error_handler", error_handler_fn)

    # ---- Add edges ----

    # START → planner
    graph.add_edge(START, "planner")

    # planner → conditional → {tool_router, responder, error_handler}
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "tool_router": "tool_router",
            "responder": "responder",
            "error_handler": "error_handler",
        },
    )

    # tool_router → tool_executor (always)
    graph.add_edge("tool_router", "tool_executor")

    # tool_executor → reflection (always)
    graph.add_edge("tool_executor", "reflection")

    # reflection → conditional → {planner, responder, error_handler}
    graph.add_conditional_edges(
        "reflection",
        route_after_reflection,
        {
            "planner": "planner",
            "responder": "responder",
            "error_handler": "error_handler",
        },
    )

    # responder → END
    graph.add_edge("responder", END)

    # error_handler → END
    graph.add_edge("error_handler", END)

    # =================================================================
    # 3. COMPILE AND RETURN
    # =================================================================

    checkpointer = InMemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)
    display(Image(compiled.get_graph().draw_mermaid_png()))

    logger.info(
        "Agent orchestration graph compiled successfully "
        "(6 nodes, max_iterations=%d)",
        max_iterations,
    )

    return compiled
