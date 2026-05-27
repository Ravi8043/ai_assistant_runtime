import logging
import uuid
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import ValidationError

from assist_runtime.memory.chunkers.base import BaseChunker
from assist_runtime.memory.schemas.document import RawDocument
from assist_runtime.memory.schemas.chunk import DocumentChunk
from assist_runtime.memory.exceptions import MemoryLoadError

logger = logging.getLogger(__name__)

class RecursiveChunker(BaseChunker):
    """
    Production-ready semantic text chunker engineered to process batches
    directly from upstream ingestion pipelines securely and defensively.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self._splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " "],
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        logger.info(
            f"RecursiveChunker initialized with chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}"
        )

    def _normalize_metadata(self, doc: RawDocument) -> Dict[str, Any]:
        """
        Defensively normalizes upstream metadata to guarantee a valid dictionary structure.
        """
        if not hasattr(doc, 'metadata') or doc.metadata is None:
            return {}
        
        if isinstance(doc.metadata, dict):
            return doc.metadata.copy()
            
        # Upstream fallback: if metadata is an unexpected type, cast it securely
        try:
            return dict(doc.metadata)
        except (TypeError, ValueError):
            logger.warning(f"Upstream metadata was unparseable type ({type(doc.metadata)}). Defaulting to empty dict.")
            return {}

    def chunk(self, documents: List[RawDocument]) -> List[DocumentChunk]:
        """
        Splits a batch of RawDocuments into a flat list of normalized DocumentChunks.
        
        Args:
            documents (List[RawDocument]): Input structures from upstream ingestion.
            
        Returns:
            List[DocumentChunk]: Validated chunks with unique tracking IDs.
            
        Raises:
            MemoryLoadError: If incoming batch structure is unreadable.
        """
        # Guard Clause 1: High-level payload validation
        if documents is None:
            logger.error("Received NoneType instead of a list of RawDocuments from upstream pipeline.")
            raise MemoryLoadError("Upstream ingestion pipeline passed a null document payload.")
            
        if not documents:
            logger.warning("Upstream payload batch is empty. Skipping chunking lifecycle execution.")
            return []

        processed_chunks: List[DocumentChunk] = []
        logger.info(f"Ingestion Sync: Processing batch of {len(documents)} documents.")

        try:
            for doc_idx, doc in enumerate(documents):
                # Guard Clause 2: Check for corrupt/empty documents
                if not doc or not hasattr(doc, 'content') or doc.content is None:
                    logger.warning(f"Skipping corrupt or structural null document at batch index {doc_idx}.")
                    continue
                
                clean_content = str(doc.content).strip()
                if not clean_content:
                    logger.debug(f"Skipping document at index {doc_idx}; content is empty string.")
                    continue

                # Defensive clean room extraction of upstream metadata
                safe_metadata = self._normalize_metadata(doc)

                # Execute splitting algorithm
                raw_text_chunks = self._splitter.split_text(clean_content)
                
                for chunk_text in raw_text_chunks:
                    processed_chunks.append(
                        DocumentChunk(
                            id=f"chk_{uuid.uuid4().hex[:12]}",  # Collision-free unique chunk signature
                            text=chunk_text,
                            metadata=safe_metadata.copy(),      # Complete dictionary isolation
                        )
                    )
            
            logger.info(f"Ingestion Sync Complete: Generated {len(processed_chunks)} validated chunks.")
            return processed_chunks

        except ValidationError as ve:
            logger.error("Chunk schema validation failed against internal DocumentChunk contract.", exc_info=True)
            raise MemoryLoadError("Downstream data integrity violation: parsed chunk schemas are invalid.") from ve
        except Exception as e:
            logger.error("Critical failure during chunk processing loop architecture.", exc_info=True)
            raise MemoryLoadError("Failed to safely process upstream data batch.") from e