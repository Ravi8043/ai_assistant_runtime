from dataclasses import dataclass

from pathlib import Path

from uuid import uuid4

from datetime import datetime


@dataclass
class ExecutionContext:
    """
    Execution context for the runtime
    """
    #instance attributes
    session_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    started_at: datetime = field(
        default_factory=datetime.utcnow
    )

    current_working_directory: Path = field(
        default_factory=Path.cwd
    )
    
    active_repo_path: Path | None = None
    active_file_path: Path | None = None
    
    environment: dict[str, str] = field(
        default_factory=dict
    )

    metadata: dict = field(
        default_factory = dict
    )