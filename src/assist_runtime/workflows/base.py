from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Coroutine
import time
from langgraph.graph import StateGraph, START, END

from assist_runtime.workflows.state import WorkflowState
from assist_runtime.runtime.tracer import WorkflowTracer

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
    """Executes a list of steps sequentially using LangGraph."""

    def __init__(self, steps: list[Callable[[WorkflowState], Coroutine[Any, Any, WorkflowState]]]):
        self.steps = steps
        
        graph = StateGraph(dict)
        
        for step in steps:
            graph.add_node(step.__name__, self._make_node(step))
            
        if steps:
            graph.add_edge(START, steps[0].__name__)
            for i in range(len(steps) - 1):
                graph.add_edge(steps[i].__name__, steps[i+1].__name__)
            graph.add_edge(steps[-1].__name__, END)
        else:
            graph.add_edge(START, END)
            
        self.graph = graph.compile()

    def _make_node(self, step_func):
        async def node_func(state_dict: dict):
            state_obj = WorkflowState(**state_dict)
            
            start_time = time.time()
            WorkflowTracer.on_node_start(state_obj.workflow_id, step_func.__name__)
            
            result_state = await step_func(state_obj)
            
            duration = (time.time() - start_time) * 1000
            WorkflowTracer.on_node_complete(result_state.workflow_id, step_func.__name__, duration)
            
            return result_state.model_dump()
        return node_func

    async def run(self, state: WorkflowState) -> WorkflowResult:
        self.validate_inputs(state)
        state.status = "running"
        
        WorkflowTracer.on_workflow_start(self.name, state.workflow_id, state.metadata)
        
        try:
            initial_state_dict = state.model_dump()
            final_state_dict = await self.graph.ainvoke(initial_state_dict)
            
            final_state = WorkflowState(**final_state_dict)
            final_state.status = "completed"
            
            WorkflowTracer.on_workflow_complete(final_state.workflow_id, success=True)
            
            return WorkflowResult(
                success=True,
                artifacts=final_state.artifacts,
                state=final_state
            )
            
        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            WorkflowTracer.on_workflow_complete(state.workflow_id, success=False, error=str(e))
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
        
        WorkflowTracer.on_workflow_start(self.name, state.workflow_id, state.metadata)
        
        try:
            # LangGraph expects a dict for StateGraph, so we dump and load
            initial_state_dict = state.model_dump()
            final_state_dict = await self.graph.ainvoke(initial_state_dict)
            
            # Update state with results
            final_state = WorkflowState(**final_state_dict)
            final_state.status = "completed"
            
            WorkflowTracer.on_workflow_complete(final_state.workflow_id, success=True)
            
            return WorkflowResult(
                success=True,
                artifacts=final_state.artifacts,
                state=final_state
            )
            
        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            WorkflowTracer.on_workflow_complete(state.workflow_id, success=False, error=str(e))
            return WorkflowResult(
                success=False,
                artifacts=state.artifacts,
                state=state,
                error=str(e)
            )
