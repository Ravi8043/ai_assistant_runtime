"""
LangGraph-based agent orchestration graph.

This package contains the full agentic workflow:
    START → planner → tool_router → tool_executor → reflection → (loop or) responder → END
"""

from assist_runtime.graph.registry import get_compiled_graph

__all__ = ["get_compiled_graph"]
