"""
Graph registry — factory that initialises all dependencies and returns
a ready-to-invoke compiled graph.

Usage::

    from assist_runtime.graph.registry import get_compiled_graph

    graph = get_compiled_graph()
    result = await graph.ainvoke({
        "input_text": "List files in the current directory",
        "max_iterations": 10,
        ...
    })
"""

from __future__ import annotations

import logging
from typing import Any

from assist_runtime.graph.builder import build_graph
from assist_runtime.llm.client import UnifiedLLMClient
from assist_runtime.llm.parsing.structured import StructuredOutputParser
from assist_runtime.tools.bootstrap import load_tools
from assist_runtime.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)

# Module-level cache for the compiled graph singleton
_compiled_graph_cache: Any | None = None


def get_compiled_graph(
    max_iterations: int = 10,
    *,
    force_rebuild: bool = False,
) -> Any:
    """
    Initialise all dependencies and return a compiled LangGraph.

    The compiled graph is cached at module level so that repeated calls
    return the same instance (unless ``force_rebuild=True``).

    Parameters
    ----------
    max_iterations:
        Maximum number of tool-execution loops before forced termination.
    force_rebuild:
        If ``True``, discard the cached graph and build a fresh one.

    Returns
    -------
    CompiledGraph
        A compiled ``StateGraph`` ready for ``.invoke()`` / ``.ainvoke()``.
    """
    global _compiled_graph_cache

    if _compiled_graph_cache is not None and not force_rebuild:
        logger.debug("Returning cached compiled graph")
        return _compiled_graph_cache

    logger.info("Building agent orchestration graph...")

    # ---- 1. LLM Client ----
    llm_client = UnifiedLLMClient()

    # ---- 2. Tool Infrastructure ----
    tool_registry = load_tools()
    tool_executor = ToolExecutor(registry=tool_registry)

    # ---- 3. Structured Output Parser ----
    parser = StructuredOutputParser()

    # ---- 4. Build & compile the graph ----
    compiled = build_graph(
        llm_client=llm_client,
        tool_executor=tool_executor,
        tool_registry=tool_registry,
        parser=parser,
        max_iterations=max_iterations,
    )

    _compiled_graph_cache = compiled

    logger.info(
        "Agent orchestration graph ready (tools: %s)",
        list(tool_registry.get_all_tools().keys()),
    )

    return compiled
