from assist_runtime.workflows.base import SequentialWorkflow
from assist_runtime.workflows.repo_analysis.nodes import (
    scan_repository,
    summarize_repository,
    write_artifact
)

class RepoAnalysisWorkflow(SequentialWorkflow):
    name = "repo_analysis"
    description = "Scans a repository and generates an architectural summary."

    def __init__(self):
        super().__init__(steps=[
            scan_repository,
            summarize_repository,
            write_artifact
        ])

    def validate_inputs(self, state):
        if "repo_path" not in state.metadata:
            raise ValueError("repo_path is required in state metadata")
        if "llm_client" not in state.metadata:
            raise ValueError("llm_client is required in state metadata")
