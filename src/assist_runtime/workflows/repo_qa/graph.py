from typing import Any
from langgraph.graph import StateGraph, START, END

from assist_runtime.workflows.repo_qa.nodes import (
    retrieve,
    answer,
    write_artifact
)

def build_repo_qa_graph() -> Any:
    graph = StateGraph(dict)
    
    graph.add_node("retrieve", retrieve)
    graph.add_node("answer", answer)
    graph.add_node("write_artifact", write_artifact)
    
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", "write_artifact")
    graph.add_edge("write_artifact", END)
    
    return graph.compile()
