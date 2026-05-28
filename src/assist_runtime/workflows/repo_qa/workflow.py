from assist_runtime.workflows.base import GraphWorkflow
from assist_runtime.workflows.repo_qa.graph import build_repo_qa_graph

class RepoQAWorkflow(GraphWorkflow):
    name = "repo_qa"
    description = "Answers questions about a repository using retrieval."

    def __init__(self):
        super().__init__(compiled_graph=build_repo_qa_graph())

    def validate_inputs(self, state):
        if not state.goal:
            raise ValueError("goal (question) is required for Repo QA")
        if "llm_client" not in state.metadata:
            raise ValueError("llm_client is required in state metadata")
