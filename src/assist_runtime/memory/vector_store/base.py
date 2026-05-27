# assist_runtime/memory/vectordb/base.py

from abc import ABC, abstractmethod
from typing import List

from assist_runtime.memory.schemas.chunk import DocumentChunk
from assist_runtime.memory.schemas.retrieved_chunk import RetrievedChunk


class BaseVectorStore(ABC):
    """
    Base abstraction for vector database implementations.

    Responsibilities:
    - persist embeddings
    - perform similarity search
    - return normalized retrieval objects

    Vector stores should NOT:
    - generate embeddings
    - chunk documents
    - call LLMs
    """

    @abstractmethod
    def add(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> None:
        """
        Store chunks and embeddings.
        """
        ...

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[RetrievedChunk]:
        """
        Perform semantic similarity search.
        """
        ...