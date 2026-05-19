import asyncio


async def with_timeout(
    coro,
    timeout: int
):

    return await asyncio.wait_for(
        coro,
        timeout=timeout
    )