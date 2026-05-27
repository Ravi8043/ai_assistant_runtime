from pathlib import Path
from typing import Dict, List
import logging

from assist_runtime.memory.loaders.base import BaseLoader
from assist_runtime.memory.loaders.markdown_loader import MarkdownLoader
from assist_runtime.memory.loaders.python_loader import PythonLoader
from assist_runtime.memory.loaders.text_loader import TextLoader
from assist_runtime.memory.loaders.validators import validate_directory_path
from assist_runtime.memory.schemas.document import RawDocument
from assist_runtime.memory.exceptions import MemoryLoadError

logger = logging.getLogger(__name__)


class DirectoryLoader:
    """
    Recursively loads supported files from a directory.

    Responsibilities:
    - traverse directories
    - ignore noisy/unwanted folders
    - delegate files to appropriate loaders
    - aggregate normalized RawDocument objects
    """

    IGNORE_DIRS = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".mypy_cache",
        ".pytest_cache",
    }

    SUPPORTED_LOADERS: Dict[str, BaseLoader] = {
        ".py": PythonLoader(),
        ".md": MarkdownLoader(),
        ".txt": TextLoader(),
    }

    def load(self, directory_path: str) -> List[RawDocument]:
        """
        Load all supported documents from a directory recursively.
        """

        validate_directory_path(directory_path)

        try:
            logger.info(
                f"Loading directory recursively: {directory_path}"
            )

            root_path = Path(directory_path)

            documents: List[RawDocument] = []

            for file_path in root_path.rglob("*"):

                if file_path.is_dir():
                    continue

                if self._should_ignore(file_path):
                    continue

                loader = self._get_loader(file_path)

                if loader is None:
                    continue

                logger.info(f"Loading file: {file_path}")

                docs = loader.load(str(file_path))

                documents.extend(docs)

            logger.info(
                f"Successfully loaded {len(documents)} documents "
                f"from directory: {directory_path}"
            )

            return documents

        except Exception as e:
            logger.error(
                f"Execution failed while loading directory: "
                f"{directory_path}",
                exc_info=True,
            )

            raise MemoryLoadError(
                f"Failed to load directory: {directory_path}"
            ) from e

    def _get_loader(self, file_path: Path) -> BaseLoader | None:
        """
        Resolve loader based on file extension.
        """

        return self.SUPPORTED_LOADERS.get(file_path.suffix)

    def _should_ignore(self, file_path: Path) -> bool:
        """
        Check whether file belongs to ignored directories.
        """

        return any(
            part in self.IGNORE_DIRS
            for part in file_path.parts
        )