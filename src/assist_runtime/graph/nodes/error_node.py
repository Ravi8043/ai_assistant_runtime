"""
Error handler node — catch-all for graceful failure responses.

This node is the terminal error sink for the entire graph. Any node that
encounters an unrecoverable exception should set ``state["error"]`` and
route here via ``next_node = "error_handler"``.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from langchain_core.messages import AIMessage

from assist_runtime.graph.state import GraphState

logger = logging.getLogger(__name__)


def create_error_handler_node() -> Any:
    """
    Factory that returns the error-handler node function.

    No external dependencies are required — the node only reads ``state["error"]``
    and produces a user-friendly ``final_response``.
    """

    async def error_handler_node(state: GraphState) -> dict[str, Any]:
        """
        Formats whatever is stored in ``state["error"]`` into a graceful,
        user-facing message and terminates the workflow.
        """
        raw_error = state.get("error") or "An unknown error occurred."
        logger.error("Graph terminated via error_handler: %s", raw_error)

        # Build a polished, user-facing message
        user_message = (
            "I'm sorry, but I ran into a problem while processing your request.\n\n"
            f"**Error details:** {raw_error}\n\n"
            "Please try rephrasing your request or check that the required "
            "resources are accessible."
        )

        return {
            "final_response": user_message,
            "is_complete": True,
            "error": None,  # Clear so downstream consumers don't re-trigger
            "messages": [
                AIMessage(content=f"[ERROR] {raw_error}")
            ],
        }

    return error_handler_node
