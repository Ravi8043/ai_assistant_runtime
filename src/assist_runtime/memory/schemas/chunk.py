from typing import Any, Dict
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """
    Normalized chunk representation used throughout
    the retrieval pipeline.

    This becomes the core unit stored inside:
    - vector databases
    - retrieval systems
    - context builders
    """

    id: str = Field(
        ...,
        description="Unique identifier for the chunk",
    )

    text: str = Field(
        ...,
        description="Chunk content",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Associated chunk metadata",
    )