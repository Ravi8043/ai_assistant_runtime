import os
import json
import time
from typing import Any

LOGS_DIR = ".runtime/logs"
TRACE_FILE = os.path.join(LOGS_DIR, "workflow_traces.jsonl")

class WorkflowTracer:
    """Lightweight execution tracing to track workflow runs, node timings, and LLM calls."""
    
    @staticmethod
    def _ensure_dir():
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR, exist_ok=True)
            
    @staticmethod
    def _log_event(event_type: str, payload: dict[str, Any]):
        WorkflowTracer._ensure_dir()
        event = {
            "timestamp": time.time(),
            "type": event_type,
            **payload
        }
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
            
    @staticmethod
    def on_workflow_start(workflow_name: str, workflow_id: str, metadata: dict[str, Any] = None):
        WorkflowTracer._log_event("workflow_start", {
            "workflow_name": workflow_name,
            "workflow_id": workflow_id,
            "metadata": metadata or {}
        })
        
    @staticmethod
    def on_workflow_complete(workflow_id: str, success: bool, error: str = None):
        WorkflowTracer._log_event("workflow_complete", {
            "workflow_id": workflow_id,
            "success": success,
            "error": error
        })
        
    @staticmethod
    def on_node_start(workflow_id: str, node_name: str):
        WorkflowTracer._log_event("node_start", {
            "workflow_id": workflow_id,
            "node_name": node_name
        })
        
    @staticmethod
    def on_node_complete(workflow_id: str, node_name: str, duration_ms: float):
        WorkflowTracer._log_event("node_complete", {
            "workflow_id": workflow_id,
            "node_name": node_name,
            "duration_ms": duration_ms
        })
        
    @staticmethod
    def on_llm_call(workflow_id: str, prompt_tokens: int = 0, completion_tokens: int = 0, duration_ms: float = 0.0):
        WorkflowTracer._log_event("llm_call", {
            "workflow_id": workflow_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_ms": duration_ms
        })
