from abc import ABC, abstractmethod
from typing import List

from assist_runtime.memory.schemas.document import RawDocument
from assist_runtime.memory.schemas.chunk import DocumentChunk


class BaseChunker(ABC):
    """
    Base abstraction for all chunking strategies.

    Responsibilities:
    - split documents into semantic chunks
    - preserve metadata
    - return normalized chunk objects

    Chunkers should NOT:
    - generate embeddings
    - access vector databases
    - call LLMs
    """

    @abstractmethod
    def chunk(
        self,
        documents: List[RawDocument],
    ) -> List[DocumentChunk]:
        """
        Split documents into chunks.
        """
        pass