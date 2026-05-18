class ChatService:

    async def chat(
        self,
        message: str
    ) -> str:

        return f"Jarvis received: {message}"