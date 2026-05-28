from assist_runtime.workflows.base import SequentialWorkflow
from assist_runtime.workflows.document_summary.nodes import (
    load_documents,
    chunk_documents,
    summarize_chunks,
    synthesize_report,
    write_artifact
)

class DocumentSummaryWorkflow(SequentialWorkflow):
    name = "document_summary"
    description = "Summarizes multiple documents sequentially."

    def __init__(self):
        super().__init__(steps=[
            load_documents,
            chunk_documents,
            summarize_chunks,
            synthesize_report,
            write_artifact
        ])

    def validate_inputs(self, state):
        if "file_paths" not in state.metadata:
            raise ValueError("file_paths is required in state metadata")
        if "llm_client" not in state.metadata:
            raise ValueError("llm_client is required in state metadata")
