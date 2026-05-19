import asyncio


async def retry_async(
    fn,
    retries: int = 3,
    backoff: float = 0.5
):

    last_error = None

    for attempt in range(retries):

        try:
            return await fn()

        except Exception as e:
            last_error = e
            await asyncio.sleep(backoff * (2 ** attempt))

    raise last_error