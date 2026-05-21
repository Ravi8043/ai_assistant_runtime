from uuid import uuid4

from langchain_core.messages import HumanMessage

from assist_runtime.graph.registry import get_compiled_graph
from assist_runtime.graph.state import GraphState
from assist_runtime.runtime.context import ExecutionContext


class ChatService:

    def __init__(self):

        self.thread_id = str(uuid4())

        self.graph = get_compiled_graph()

    async def chat(
        self,
        message: str
    ) -> str:

        state: GraphState = {

            "input_text": message,

            "context": ExecutionContext(),

            "messages": [
                HumanMessage(content=message)
            ],

            "current_plan": None,

            "current_step_index": 0,

            "selected_tool": None,

            "tool_input": None,

            "tool_output": None,

            "current_iteration": 0,

            "max_iterations": 10,

            "is_complete": False,

            "next_node": None,

            "error": None,

            "final_response": None
        }

        config = {
            "configurable": {
                "thread_id": self.thread_id
            }
        }

        result = await self.graph.ainvoke(
            state,
            config=config
        )

        return result.get(
            "final_response",
            "No response generated."
        )