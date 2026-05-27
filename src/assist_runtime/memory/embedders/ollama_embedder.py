from typing import List
import logging

from langchain_ollama import OllamaEmbeddings

from assist_runtime.memory.embedders.base import BaseEmbedder

logger = logging.getLogger(__name__)


class OllamaEmbedder(BaseEmbedder):

    def __init__(
        self,
        model: str = "nomic-embed-text",
    ) -> None:

        logger.info(
            f"Initializing Ollama embeddings: {model}"
        )

        self.embedder = OllamaEmbeddings(
            model=model,
        )

    def embed(
        self,
        text: str,
    ) -> List[float]:

        return self.embedder.embed_query(text)

    def embed_many(
        self,
        texts: List[str],
    ) -> List[List[float]]:

        return self.embedder.embed_documents(texts)