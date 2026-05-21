from dotenv import load_dotenv
from langchain_groq import ChatGroq

from assist_runtime.llm.core.base import BaseLLM


load_dotenv()


class GroqClient(BaseLLM):

    def __init__(
        self,
        model: str = "qwen/qwen3-32b"
    ):

        self.client = ChatGroq(
            model=model
        )

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        **kwargs
    ) -> str:

        response = await self.client.ainvoke(
            prompt,
            temperature=temperature
        )

        content = response.content

        if isinstance(content, str):
            return content

        return str(content)