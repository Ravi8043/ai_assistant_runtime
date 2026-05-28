import os
from typing import Any
from assist_runtime.memory.retrieval.context_builder import WorkflowContextBuilder
from assist_runtime.workflows.artifacts import ArtifactWriter
from assist_runtime.workflows.repo_qa.prompts import REPO_QA_PROMPT

async def ingest_check(state: dict[str, Any]) -> dict[str, Any]:
    # In a real implementation, this would check if the repo is indexed in ChromaDB.
    # If not, it would trigger ingestion.
    # For now, we assume ingestion is done or skip it.
    return state

async def retrieve(state: dict[str, Any]) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    retriever = metadata.get("retriever")
    goal = state.get("goal", "")
    
    if retriever and goal:
        try:
            chunks = retriever.retrieve(goal, top_k=5)
            state.setdefault("step_outputs", {})["retrieved_chunks"] = chunks
        except Exception as e:
            state.setdefault("step_outputs", {})["retrieved_chunks"] = []
    else:
        state.setdefault("step_outputs", {})["retrieved_chunks"] = []
        
    return state

async def evaluate_results(state: dict[str, Any]) -> dict[str, Any]:
    # Determine if we have good results.
    chunks = state.get("step_outputs", {}).get("retrieved_chunks", [])
    
    # Simple check: do we have chunks?
    if chunks:
        # good results
        state.setdefault("metadata", {})["has_good_results"] = True
    else:
        # poor results
        state.setdefault("metadata", {})["has_good_results"] = False
        
    return state

async def fallback_scan(state: dict[str, Any]) -> dict[str, Any]:
    # In a real implementation, use grep/filesystem tools.
    # For now, we'll just leave chunks empty.
    return state

async def answer(state: dict[str, Any]) -> dict[str, Any]:
    llm_client = state.get("metadata", {}).get("llm_client")
    chunks = state.get("step_outputs", {}).get("retrieved_chunks", [])
    goal = state.get("goal", "")
    
    if not llm_client:
        raise ValueError("llm_client missing in state metadata")
        
    cb = WorkflowContextBuilder()
    cb.add_retrieved_chunks(chunks)
    context_str = cb.build()
    
    prompt = REPO_QA_PROMPT.format(context=context_str, question=goal)
    answer_text = await llm_client.generate(prompt)
    
    state.setdefault("step_outputs", {})["answer"] = answer_text
    return state

async def write_artifact(state: dict[str, Any]) -> dict[str, Any]:
    answer_text = state.get("step_outputs", {}).get("answer", "No answer generated.")
    workflow_id = state.get("workflow_id", "unknown")
    
    writer = ArtifactWriter()
    artifact = writer.write_markdown(
        name="repo_qa",
        content=answer_text,
        workflow_id=workflow_id
    )
    
    # We must construct a new list of artifacts or append to it if it exists.
    artifacts = state.get("artifacts", [])
    artifacts.append(artifact.path)
    state["artifacts"] = artifacts
    
    return state
