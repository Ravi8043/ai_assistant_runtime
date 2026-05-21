from typing_extensions import TypedDict
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Any
from assist_runtime.runtime.context import ExecutionContext



class GraphState(TypedDict):
    """The state of the graph execution."""
    input_text: str
    context: ExecutionContext
    messages: Annotated[
        list[AnyMessage], add_messages
    ]
    current_plan: Annotated[
        dict[str, Any] | None, 
        "Structured planner output"
    ]
     # selected tool name
    selected_tool: Annotated[
        str | None,
        "Tool selected by planner"
    ]

    # tool execution input
    tool_input: Annotated[
        dict[str, Any] | None,
        "Input payload for tool"
    ]

    # raw tool execution output
    tool_output: Annotated[
        Any | None,
        "Output returned by tool execution"
    ]

    # final user-facing response
    final_response: Annotated[
        str | None,
        "Final response returned to user"
    ]

    # next node routing
    next_node: Annotated[
        str | None,
        "Next graph node to execute"
    ]

    # graph completion state
    is_complete: Annotated[
        bool,
        "Whether graph execution is finished"
    ]

    # iteration tracking
    current_iteration: Annotated[
        int,
        "Current graph iteration count"
    ]

    max_iterations: Annotated[
        int,
        "Maximum allowed graph iterations"
    ]

    # error handling
    error: Annotated[
        str | None,
        "Execution error if any"
    ]