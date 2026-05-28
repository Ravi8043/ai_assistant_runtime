from typing import Any, Literal
from langgraph.graph import StateGraph, START, END

from assist_runtime.workflows.repo_qa.nodes import (
    ingest_check,
    retrieve,
    evaluate_results,
    fallback_scan,
    answer,
    write_artifact
)

def route_after_evaluation(state: dict[str, Any]) -> Literal["answer", "fallback_scan"]:
    if state.get("metadata", {}).get("has_good_results"):
        return "answer"
    return "fallback_scan"

def build_repo_qa_graph() -> Any:
    # State is just a generic dict, conforming to WorkflowState fields
    graph = StateGraph(dict)
    
    # Add nodes
    graph.add_node("ingest_check", ingest_check)
    graph.add_node("retrieve", retrieve)
    graph.add_node("evaluate_results", evaluate_results)
    graph.add_node("fallback_scan", fallback_scan)
    graph.add_node("answer", answer)
    graph.add_node("write_artifact", write_artifact)
    
    # Add edges
    graph.add_edge(START, "ingest_check")
    graph.add_edge("ingest_check", "retrieve")
    graph.add_edge("retrieve", "evaluate_results")
    
    # Conditional edge
    graph.add_conditional_edges(
        "evaluate_results",
        route_after_evaluation,
        {
            "answer": "answer",
            "fallback_scan": "fallback_scan"
        }
    )
    
    graph.add_edge("fallback_scan", "answer")
    graph.add_edge("answer", "write_artifact")
    graph.add_edge("write_artifact", END)
    
    return graph.compile()
