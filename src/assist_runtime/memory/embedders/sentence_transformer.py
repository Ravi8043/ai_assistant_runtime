from typing import List
import logging

from sentence_transformers import SentenceTransformer

from assist_runtime.memory.embedders.base import BaseEmbedder
from assist_runtime.memory.exceptions import MemoryLoadError

logger = logging.getLogger(__name__)



class SentenceTransformerEmbedder(BaseEmbedder):

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        **kwargs
    ) -> None:
        logger.info(
            f"Loading SentenceTransformer model: {model_name}"
        )
        
        self.model = SentenceTransformer(
            model_name,
            **kwargs
        )

    def embed(
        self,
        text: str
    ) -> List[float]:

        try:
            logger.info(
                f"Embedding text: {text[:100]}..."
            )

            embedding = self.model.encode(text)

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Failed to embed text: {text[:100]}...", exc_info=True)
            raise MemoryLoadError(f"Failed to embed text: {text[:100]}...") from e

    def embed_many(
        self,
        texts: List[str],
    ) -> List[List[float]]:

        try:
            logger.info(
                f"Embedding {len(texts)} texts..."
            )

            embeddings = self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            return embeddings.tolist()

        except Exception as e:
            logger.error(
                f"Failed to embed {len(texts)} texts",
                exc_info=True,
            )

            raise MemoryLoadError(f"Failed to embed {len(texts)} texts") from e

    def get_model_dim(self) -> int:
        """
        Returns the embedding dimension of the loaded model.
        """
        return self.model.get_sentence_embedding_dimension()