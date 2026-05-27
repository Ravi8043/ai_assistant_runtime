# assist_runtime/memory/schemas/retrieved_chunk.py

from typing import Any, Dict
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """
    Represents a retrieved chunk returned
    from semantic search.
    """

    text: str = Field(
        ...,
        description="Retrieved chunk content",
    )

    score: float = Field(
        ...,
        description="Similarity score",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Associated metadata",
    )