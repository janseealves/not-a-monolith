import json
from collections.abc import AsyncIterator


async def sse_stream(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
    """Envelopa um stream de texto no formato Server-Sent Events."""
    async for chunk in chunks:
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"
