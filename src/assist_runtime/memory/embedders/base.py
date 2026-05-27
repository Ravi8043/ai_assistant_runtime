from abc import ABC, abstractmethod
from typing import List


class BaseEmbedder(ABC):
    """
    Base abstraction for embedding providers.

    Responsibilities:
    - generate vector embeddings
    - support single + batch embedding

    Embedders should NOT:
    - interact with vector DBs
    - perform retrieval
    - manage chunking
    """

    @abstractmethod
    def embed(
        self,
        text: str,
    ) -> List[float]:
        """
        prompt embedding

        Generate embedding for a single text input.
        """
        pass

    @abstractmethod
    def embed_many(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        knowledge base embeddings

        Generate embeddings for multiple texts.
        """
        pass