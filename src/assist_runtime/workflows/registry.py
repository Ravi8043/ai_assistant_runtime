from assist_runtime.workflows.base import BaseWorkflow

class WorkflowRegistry:
    """Registry of available workflows."""

    def __init__(self):
        self._workflows: dict[str, BaseWorkflow] = {}

    def register(self, workflow: BaseWorkflow) -> None:
        if workflow.name in self._workflows:
            raise ValueError(f"Workflow '{workflow.name}' is already registered.")
        self._workflows[workflow.name] = workflow

    def get(self, name: str) -> BaseWorkflow | None:
        return self._workflows.get(name)

    def list_workflows(self) -> list[str]:
        return list(self._workflows.keys())

    def clear(self) -> None:
        self._workflows.clear()
