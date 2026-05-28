from typing import Any
import time
from assist_runtime.memory.retrieval.context_builder import WorkflowContextBuilder
from assist_runtime.workflows.artifacts import ArtifactWriter
from assist_runtime.runtime.prompt_builder import PromptBuilder
from assist_runtime.runtime.tracer import WorkflowTracer
from assist_runtime.runtime.cache import RuntimeCache

async def retrieve(state: dict[str, Any]) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    retriever = metadata.get("retriever")
    goal = state.get("goal", "")
    workflow_id = state.get("workflow_id", "unknown")
    
    start_time = time.time()
    if retriever and goal:
        try:
            chunks = retriever.retrieve(goal, top_k=5)
            # Store in cache instead of state bloat
            ref_id = RuntimeCache.save_pickle(chunks, prefix="retrieved_chunks")
            state.setdefault("metadata", {})["retrieved_chunks_ref"] = ref_id
        except Exception as e:
            state.setdefault("metadata", {})["retrieved_chunks_ref"] = None
    else:
        state.setdefault("metadata", {})["retrieved_chunks_ref"] = None
        
    duration = (time.time() - start_time) * 1000
    WorkflowTracer.on_node_complete(workflow_id, "retrieve", duration)
    return state

async def answer(state: dict[str, Any]) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    llm_client = metadata.get("llm_client")
    chunks_ref = metadata.get("retrieved_chunks_ref")
    chunks = RuntimeCache.load_pickle(chunks_ref) if chunks_ref else []
    goal = state.get("goal", "")
    workflow_id = state.get("workflow_id", "unknown")
    
    if not llm_client:
        raise ValueError("llm_client missing in state metadata")
        
    cb = WorkflowContextBuilder()
    cb.add_retrieved_chunks(chunks)
    context_str = cb.build()
    
    prompt = PromptBuilder.build_repo_qa_prompt(context=context_str, question=goal)
    
    start_time = time.time()
    answer_text = await llm_client.generate(prompt)
    duration_ms = (time.time() - start_time) * 1000
    
    WorkflowTracer.on_llm_call(workflow_id, duration_ms=duration_ms)
    WorkflowTracer.on_node_complete(workflow_id, "answer", duration_ms)
    
    state.setdefault("step_outputs", {})["answer"] = answer_text
    return state

async def write_artifact(state: dict[str, Any]) -> dict[str, Any]:
    answer_text = state.get("step_outputs", {}).get("answer", "No answer generated.")
    workflow_id = state.get("workflow_id", "unknown")
    
    start_time = time.time()
    
    writer = ArtifactWriter()
    artifact = writer.write_markdown(
        name="repo_qa",
        content=answer_text,
        workflow_id=workflow_id
    )
    
    artifacts = state.get("artifacts", [])
    artifacts.append(artifact.path)
    state["artifacts"] = artifacts
    
    duration = (time.time() - start_time) * 1000
    WorkflowTracer.on_node_complete(workflow_id, "write_artifact", duration)
    return state
