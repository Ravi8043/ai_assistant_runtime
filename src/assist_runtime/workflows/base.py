from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Coroutine
from langgraph.graph import StateGraph, START, END

from assist_runtime.workflows.state import WorkflowState

@dataclass
class WorkflowResult:
    """Standard return from any workflow."""
    success: bool
    artifacts: list[str]            # file paths produced
    state: WorkflowState            # final state snapshot
    error: str | None = None

class BaseWorkflow(ABC):
    """Base class for all workflows."""

    name: str = "base_workflow"
    description: str = "Base workflow"

    @abstractmethod
    async def run(self, state: WorkflowState) -> WorkflowResult:
        """Execute the workflow. Subclasses implement this."""
        ...

    def validate_inputs(self, state: WorkflowState) -> None:
        """Optional input validation. Override if needed."""
        pass

class SequentialWorkflow(BaseWorkflow):
    """Executes a list of steps sequentially."""

    def __init__(self, steps: list[Callable[[WorkflowState], Coroutine[Any, Any, WorkflowState]]]):
        self.steps = steps

    async def run(self, state: WorkflowState) -> WorkflowResult:
        self.validate_inputs(state)
        state.status = "running"
        
        try:
            for step_func in self.steps:
                step_name = step_func.__name__
                state.current_step = step_name
                state.pending_steps.remove(step_name) if step_name in state.pending_steps else None
                
                # Execute step
                state = await step_func(state)
                
                state.completed_steps.append(step_name)
                
            state.status = "completed"
            state.current_step = None
            return WorkflowResult(
                success=True,
                artifacts=state.artifacts,
                state=state
            )
            
        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            if state.current_step:
                state.failed_steps.append(state.current_step)
            return WorkflowResult(
                success=False,
                artifacts=state.artifacts,
                state=state,
                error=str(e)
            )

class GraphWorkflow(BaseWorkflow):
    """Executes a LangGraph StateGraph."""
    
    def __init__(self, compiled_graph: Any):
        self.graph = compiled_graph
        
    async def run(self, state: WorkflowState) -> WorkflowResult:
        self.validate_inputs(state)
        state.status = "running"
        
        try:
            # LangGraph expects a dict for StateGraph, so we dump and load
            initial_state_dict = state.model_dump()
            final_state_dict = await self.graph.ainvoke(initial_state_dict)
            
            # Update state with results
            final_state = WorkflowState(**final_state_dict)
            final_state.status = "completed"
            
            return WorkflowResult(
                success=True,
                artifacts=final_state.artifacts,
                state=final_state
            )
            
        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            return WorkflowResult(
                success=False,
                artifacts=state.artifacts,
                state=state,
                error=str(e)
            )
