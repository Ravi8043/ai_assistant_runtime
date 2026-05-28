import os
from assist_runtime.workflows.state import WorkflowState
from assist_runtime.workflows.artifacts import ArtifactWriter
from assist_runtime.memory.loaders.text_loader import TextLoader
from assist_runtime.memory.loaders.markdown_loader import MarkdownLoader
from assist_runtime.memory.chunkers.recursive_chunker import RecursiveChunker
from assist_runtime.workflows.document_summary.prompts import CHUNK_SUMMARY_PROMPT, SYNTHESIZE_REPORT_PROMPT

async def load_documents(state: WorkflowState) -> WorkflowState:
    file_paths = state.metadata.get("file_paths", [])
    if not file_paths:
        raise ValueError("No file_paths provided in state metadata")
        
    docs = []
    for fp in file_paths:
        if fp.endswith(".md"):
            loader = MarkdownLoader()
        else:
            # Fallback to TextLoader
            loader = TextLoader()
            
        docs.extend(loader.load(fp))
        
    state.step_outputs["loaded_docs"] = docs
    return state

async def chunk_documents(state: WorkflowState) -> WorkflowState:
    docs = state.step_outputs.get("loaded_docs", [])
    chunker = RecursiveChunker(chunk_size=2000, chunk_overlap=200)
    chunks = chunker.chunk(docs)
    
    state.step_outputs["chunks"] = chunks
    return state

async def summarize_chunks(state: WorkflowState) -> WorkflowState:
    llm_client = state.metadata.get("llm_client")
    chunks = state.step_outputs.get("chunks", [])
    
    chunk_summaries = []
    # For a real system we'd use asyncio.gather to parallelize, but sequential is fine for this skeleton
    for i, chunk in enumerate(chunks):
        prompt = CHUNK_SUMMARY_PROMPT.format(chunk_text=chunk.text)
        summary = await llm_client.generate(prompt)
        chunk_summaries.append(f"### Section {i+1}\n{summary}\n")
        
    state.step_outputs["chunk_summaries"] = chunk_summaries
    return state

async def synthesize_report(state: WorkflowState) -> WorkflowState:
    llm_client = state.metadata.get("llm_client")
    chunk_summaries = state.step_outputs.get("chunk_summaries", [])
    
    joined_summaries = "\n".join(chunk_summaries)
    prompt = SYNTHESIZE_REPORT_PROMPT.format(summaries=joined_summaries)
    
    final_report = await llm_client.generate(prompt)
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
