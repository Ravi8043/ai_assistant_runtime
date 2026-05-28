import os
import time
from assist_runtime.workflows.state import WorkflowState
from assist_runtime.workflows.artifacts import ArtifactWriter
from assist_runtime.memory.loaders.text_loader import TextLoader
from assist_runtime.memory.loaders.markdown_loader import MarkdownLoader
from assist_runtime.memory.chunkers.recursive_chunker import RecursiveChunker
from assist_runtime.runtime.prompt_builder import PromptBuilder
from assist_runtime.runtime.cache import RuntimeCache
from assist_runtime.runtime.tracer import WorkflowTracer

async def load_documents(state: WorkflowState) -> WorkflowState:
    file_paths = state.metadata.get("file_paths", [])
    if not file_paths:
        raise ValueError("No file_paths provided in state metadata")
        
    docs = []
    for fp in file_paths:
        if fp.endswith(".md"):
            loader = MarkdownLoader()
        else:
            loader = TextLoader()
            
        docs.extend(loader.load(fp))
        
    # Prevent state bloat by caching
    ref_id = RuntimeCache.save_pickle(docs, prefix="docs")
    state.metadata["loaded_docs_ref"] = ref_id
    return state

async def chunk_documents(state: WorkflowState) -> WorkflowState:
    docs_ref = state.metadata.get("loaded_docs_ref")
    docs = RuntimeCache.load_pickle(docs_ref) if docs_ref else []
    
    chunker = RecursiveChunker(chunk_size=2000, chunk_overlap=200)
    chunks = chunker.chunk(docs)
    
    # Prevent state bloat by caching
    ref_id = RuntimeCache.save_pickle(chunks, prefix="chunks")
    state.metadata["chunks_ref"] = ref_id
    return state

async def summarize_chunks(state: WorkflowState) -> WorkflowState:
    llm_client = state.metadata.get("llm_client")
    chunks_ref = state.metadata.get("chunks_ref")
    chunks = RuntimeCache.load_pickle(chunks_ref) if chunks_ref else []
    
    chunk_summaries = []
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    for i, chunk in enumerate(chunks):
        prompt = PromptBuilder.build_chunk_summary_prompt(chunk.text)
        
        start_time = time.time()
        summary = await llm_client.generate(prompt)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log manual trace for the LLM call
        WorkflowTracer.on_llm_call(state.workflow_id, duration_ms=duration_ms)
        
        chunk_summaries.append(f"### Section {i+1}\n{summary}\n")
        
    ref_id = RuntimeCache.save_json(chunk_summaries, prefix="chunk_summaries")
    state.metadata["chunk_summaries_ref"] = ref_id
    return state

async def synthesize_report(state: WorkflowState) -> WorkflowState:
    llm_client = state.metadata.get("llm_client")
    summaries_ref = state.metadata.get("chunk_summaries_ref")
    chunk_summaries = RuntimeCache.load_json(summaries_ref) if summaries_ref else []
    
    joined_summaries = "\n".join(chunk_summaries)
    prompt = PromptBuilder.build_synthesize_report_prompt(joined_summaries)
    
    start_time = time.time()
    final_report = await llm_client.generate(prompt)
    duration_ms = (time.time() - start_time) * 1000
    
    WorkflowTracer.on_llm_call(state.workflow_id, duration_ms=duration_ms)
    
    # Store just the final result string in step_outputs so the next node can write it
    state.step_outputs["final_report"] = final_report
    return state

async def write_artifact(state: WorkflowState) -> WorkflowState:
    report = state.step_outputs.get("final_report", "No report generated.")
    
    writer = ArtifactWriter()
    artifact = writer.write_markdown(
        name="document_summary",
        content=report,
        workflow_id=state.workflow_id
    )
    
    state.artifacts.append(artifact.path)
    return state
