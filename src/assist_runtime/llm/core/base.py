from abc import ABC, abstractmethod

from typing import Any

class BaseLLM(ABC):

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        All LLM providers must implement this method
        """
        pass