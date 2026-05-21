from assist_runtime.llm.providers.groq import GroqClient
from assist_runtime.llm.retry import retry_async
from assist_runtime.llm.timeout import with_timeout


class UnifiedLLMClient:

    def __init__(self):

        self.provider = GroqClient()

    async def generate(
        self,
        prompt: str,
        timeout: int = 60,
        retries: int = 3
    ):

        async def call():

            return await self.provider.generate(
                prompt=prompt
            )

        return await retry_async(
            lambda: with_timeout(
                call(),
                timeout
            ),
            retries=retries
        )