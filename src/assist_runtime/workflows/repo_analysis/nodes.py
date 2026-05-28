from assist_runtime.workflows.state import WorkflowState
from assist_runtime.workflows.artifacts import ArtifactWriter
from assist_runtime.runtime.services.repository_service import RepositoryService
from assist_runtime.runtime.services.summarization_service import SummarizationService
from assist_runtime.runtime.tracer import WorkflowTracer
import time

async def scan_repository(state: WorkflowState) -> WorkflowState:
    repo_path = state.metadata.get("repo_path", ".")
    scan_ref_id = RepositoryService.scan_repository(repo_path)
    state.metadata["repo_scan_ref"] = scan_ref_id
    return state

async def summarize_repository(state: WorkflowState) -> WorkflowState:
    llm_client = state.metadata.get("llm_client")
    scan_ref_id = state.metadata.get("repo_scan_ref")
    
    if not llm_client:
        raise ValueError("llm_client not found in workflow metadata")
    if not scan_ref_id:
        raise ValueError("repo_scan_ref not found in workflow metadata")
        
    start_time = time.time()
    summary = await SummarizationService.summarize_repository_hierarchy(scan_ref_id, llm_client)
    duration_ms = (time.time() - start_time) * 1000
    
    # We record LLM call trace manually here since the service makes the call, 
    # but ideally the LLM client would log itself.
    WorkflowTracer.on_llm_call(state.workflow_id, duration_ms=duration_ms)
    
    state.step_outputs["summary_markdown"] = summary
    return state

async def write_artifact(state: WorkflowState) -> WorkflowState:
    summary_md = state.step_outputs.get("summary_markdown", "No summary generated.")
    
    writer = ArtifactWriter()
    artifact = writer.write_markdown(
        name="repo_analysis",
        content=summary_md,
        workflow_id=state.workflow_id
    )
    
    state.artifacts.append(artifact.path)
    return state
