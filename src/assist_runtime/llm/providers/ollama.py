import ollama
from assist_runtime.llm.core.base import BaseLLM


class OllamaClient(BaseLLM):

    def __init__(
        self,
        model: str = "qwen3:8b",
    ):
        self.model = model

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        **kwargs
    ) -> str:

        # Ollama SDK uses chat format
        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": temperature
            }
        )

        return response["message"]["content"]