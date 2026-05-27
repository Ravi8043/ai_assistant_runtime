import logging
import os
from typing import List

import chromadb
from chromadb.config import Settings

from assist_runtime.memory.vector_store.base import BaseVectorStore
from assist_runtime.memory.schemas.chunk import DocumentChunk
from assist_runtime.memory.schemas.retrieved_chunk import RetrievedChunk
from assist_runtime.memory.exceptions import MemoryLoadError

logger = logging.getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """
    Production-grade, persistent ChromaDB vector store implementation.
    Handles data ingestion protection and safe similarity queries.
    """

    def __init__(
        self,
        collection_name: str = "assist_memory",
        persist_directory: str = "./chroma_db",
    ) -> None:
        """
        Initializes persistent local infrastructure for vector indexing.
        """
        logger.info(f"Initializing persistent Chroma Vector Store: collection='{collection_name}'")
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        try:
            # Secure directories natively prior to initializing the persistent engine
            os.makedirs(self.persist_directory, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                ),
            )

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Production RAG runtime collection",
                    "engine": "chromadb"
                }
            )
            
            logger.info(f"Chroma connection secured. Active records in collection: {self.collection.count()}")

        except Exception as e:
            logger.error(f"Critical operational crash during Chroma database initialization framework.", exc_info=True)
            raise MemoryLoadError("Failed to safely prepare persistent vector storage systems.") from e

    def add(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> None:
        """
        Stores structured chunks and their vectorized matrices inside the collection context.

        Args:
            chunks (List[DocumentChunk]): Flat collection of internal data structures.
            embeddings (List[List[float]]): Corresponding multi-dimensional matrix values.
        """
        if not chunks:
            logger.warning("Empty records collection payload passed for database indexing assignment. Execution skipped.")
            return

        if len(chunks) != len(embeddings):
            error_msg = f"Data shape mismatch error: Record balance variation detected ({len(chunks)} chunks vs {len(embeddings)} embeddings)."
            logger.error(error_msg)
            raise MemoryLoadError(error_msg)

        logger.info(f"Committing {len(chunks)} elements into vector collection context: '{self.collection_name}'")

        try:
            # Unpack attributes sequentially into flat primitives for the low-level database boundary
            ids: List[str] = [chunk.id for chunk in chunks]
            documents: List[str] = [chunk.text for chunk in chunks]
            metadatas: List[dict] = [chunk.metadata if chunk.metadata is not None else {} for chunk in chunks]

            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info(f"Ingestion successful. Updated database density total: {self.collection.count()}")

        except Exception as e:
            logger.error(f"Failed to append data sequence execution cleanly into database collection context.", exc_info=True)
            raise MemoryLoadError("Ingestion matrix execution crash occurred inside the local storage core.") from e

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[RetrievedChunk]:
        """
        Executes semantic similarity search query routines targeting local embeddings data.

        Args:
            query_embedding (List[float]): Transformed mathematical expression vector of the query statement.
            top_k (int): Limit calculation total.

        Returns:
            List[RetrievedChunk]: Structured retrieval information collection.
        """
        logger.info(f"Executing semantic search matching process; parameter limit boundary top_k={top_k}")

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )

            # Defensive null-coalescing strategy down to extraction grids
            # Chroma nested arrays can evaluate to None types if nothing matches
            documents_list = results.get("documents") or [[]]
            metadatas_list = results.get("metadatas") or [[]]
            distances_list = results.get("distances") or [[]]

            # Intercept empty search outcomes safely
            if not documents_list or not documents_list[0]:
                logger.info("Vector space query complete. Search sequence matching yielded zero connections.")
                return []

            # Extract the raw internal index matrices accurately 
            documents = documents_list[0]
            metadatas = metadatas_list[0]
            distances = distances_list[0]

            retrieved_chunks: List[RetrievedChunk] = []

            for i in range(len(documents)):
                distance_val = distances[i] if i < len(distances) else 1.0
                
                # Production scoring formula variation: Map distance directly to confidence scores
                # Assuming L2 distance metrics; Adjust matching formulas if your database context shifts to Cosine Space
                similarity_score = float(1.0 / (1.0 + distance_val))

                retrieved_chunks.append(
                    RetrievedChunk(
                        text=str(documents[i]),
                        score=similarity_score,
                        metadata=metadatas[i] if (i < len(metadatas) and metadatas[i] is not None) else {},
                    )
                )

            logger.info(f"Search successfully resolved. Returned {len(retrieved_chunks)} valid reference matches.")
            return retrieved_chunks

        except Exception as e:
            logger.error("System failure encountered during query operations inside storage layer.", exc_info=True)
            # In production, returning an empty list during reading failures prevents the entire user agent UI from locking down completely
            return []