from typing import Any
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime
from uuid import uuid4

class Artifact(BaseModel):
    """First-class workflow output."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str                       # e.g. "repo_analysis"
    type: str                       # "markdown", "json", "text"
    path: str                       # absolute path to file
    workflow_id: str                 # which workflow produced this
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = {}

class ArtifactWriter:
    """Writes artifacts to disk. Configurable output directory."""

    def __init__(self, output_dir: Path | str = "./artifacts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_markdown(
        self,
        name: str,
        content: str,
        workflow_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        """Write markdown content to disk, return Artifact."""
        filename = f"{name}.md"
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return Artifact(
            name=name,
            type="markdown",
            path=str(path.resolve()),
            workflow_id=workflow_id,
            metadata=metadata or {},
        )
