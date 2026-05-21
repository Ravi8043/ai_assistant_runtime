from dataclasses import dataclass, field

from pathlib import Path


@dataclass
class ExecutionContext:
    """
    Execution context for the runtime
    """

    current_working_directory: Path = field(
        default_factory=Path.cwd
    )
    
    active_repo_path: Path | None = None
    active_file_path: Path | None = None