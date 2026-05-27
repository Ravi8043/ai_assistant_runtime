# assist_runtime/memory/schemas/document.py

from typing import Any, Dict
from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    """
    Normalized raw document representation
    returned by ingestion loaders.
    """

    content: str = Field(
        ...,
        description="Raw document content",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata",
    )