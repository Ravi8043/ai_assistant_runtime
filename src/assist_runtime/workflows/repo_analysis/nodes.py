import os
import json
from assist_runtime.workflows.state import WorkflowState
from assist_runtime.workflows.artifacts import ArtifactWriter
from assist_runtime.llm.client import UnifiedLLMClient
from assist_runtime.workflows.repo_analysis.prompts import REPO_ANALYSIS_PROMPT

async def scan_repository(state: WorkflowState) -> WorkflowState:
    repo_path = state.metadata.get("repo_path", ".")
    ignore_dirs = {".git", "__pycache__", "node_modules", "env", "venv"}
    
    file_list = []
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_path)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            file_list.append({
                "path": rel_path,
                "size": size,
                "ext": os.path.splitext(f)[1]
            })
            
    state.step_outputs["scanned_files"] = file_list
    return state

async def detect_languages(state: WorkflowState) -> WorkflowState:
    file_list = state.step_outputs.get("scanned_files", [])
    
    ext_counts = {}
    for f in file_list:
        ext = f["ext"]
        if ext:
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
            
    state.step_outputs["language_counts"] = ext_counts
    return state

async def map_modules(state: WorkflowState) -> WorkflowState:
    # Just group files by top-level directory for simplicity
    file_list = state.step_outputs.get("scanned_files", [])
    modules = {}
    
    for f in file_list:
        path_parts = f["path"].split(os.sep)
        module_name = path_parts[0] if len(path_parts) > 1 else "root"
        modules.setdefault(module_name, []).append(f["path"])
        
    state.step_outputs["modules"] = modules
    return state

async def generate_summary(state: WorkflowState) -> WorkflowState:
    llm_client = state.metadata.get("llm_client")
    if not llm_client:
        raise ValueError("llm_client not found in workflow metadata")
        
    # Prepare data dump for prompt
    data_dump = json.dumps({
        "languages": state.step_outputs.get("language_counts", {}),
        "modules": {k: len(v) for k, v in state.step_outputs.get("modules", {}).items()},
        "total_files": len(state.step_outputs.get("scanned_files", []))
    }, indent=2)
    
    prompt = REPO_ANALYSIS_PROMPT.format(scanned_data=data_dump)
    
    summary = await llm_client.generate(prompt)
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
