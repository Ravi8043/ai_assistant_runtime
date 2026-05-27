from typing import List
import logging

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from assist_runtime.memory.loaders.base import BaseLoader
from assist_runtime.memory.schemas.document import RawDocument
from assist_runtime.memory.loaders.validators import validate_file_path
from assist_runtime.memory.exceptions import MemoryLoadError

logger = logging.getLogger(__name__)

class MarkdownLoader(BaseLoader):

    def load(self, file_path: str) -> list[RawDocument]:
        """
        Loads a markdown file.
        """

        validate_file_path(file_path)

        try:
            logger.info(f"Loading markdown file: {file_path}")
            
            loader = UnstructuredMarkdownLoader(file_path)
            docs = loader.load()

            return [RawDocument(
                content=doc.page_content,
                metadata=doc.metadata,
            ) for doc in docs]
            
        except Exception as e:
            logger.error(f"Execution failed while parsing markdown file: {file_path}", exc_info=True)
            raise MemoryLoadError(f"Failed to process markdown file: {file_path}") from e