from abc import ABC, abstractmethod
from typing import Any, Dict
from assist_runtime.memory.schemas.document import RawDocument

class BaseLoader(ABC):

    @abstractmethod
    def load(
        self, 
        file_path: str
    ) -> list[RawDocument]:
        """
        All loaders must implement this
        """
        pass