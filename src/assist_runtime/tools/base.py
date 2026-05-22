from abc import ABC, abstractmethod

from typing import Any, Dict


class BaseTool(ABC):
    #every tool should have these attributes
    name: str
    description: str

    #this method must be implemented by child classes
    @abstractmethod
    def execute(
        self, 
        input_data: Dict[str, Any]
    ) -> dict:
        """
        All tools must implement this
        """
        pass