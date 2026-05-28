from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4

class WorkflowState(BaseModel):
    """Structured execution state for any workflow."""

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_name: str = ""
    goal: str = ""

    # Step tracking
    current_step: str | None = None
    completed_steps: list[str] = []
    pending_steps: list[str] = []
    failed_steps: list[str] = []

    # Data flow
    step_outputs: dict[str, Any] = {}       # step_name -> output data
    artifacts: list[str] = []               # paths to generated artifacts

    # Metadata
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    status: str = "pending"                 # pending | running | completed | failed
    error: str | None = None
    metadata: dict[str, Any] = {}
