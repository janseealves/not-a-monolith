import json
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class SourcesChunk:
    """Marca, no meio de um stream de texto, um lote de sources a emitir como evento SSE à parte."""

    sources: list


async def sse_stream(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
    """Envelopa um stream de texto no formato Server-Sent Events."""
    async for chunk in chunks:
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"


async def sse_stream_with_sources(
    sources: list, chunks: AsyncIterator[str]
) -> AsyncIterator[str]:
    """Envelopa um stream de texto em SSE, com um evento 'sources' antes dos chunks."""
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
    async for event in sse_stream(chunks):
        yield event


async def sse_stream_mixed(
    chunks: AsyncIterator[str | SourcesChunk],
) -> AsyncIterator[str]:
    """Envelopa um stream em SSE onde tokens de texto e eventos 'sources' podem
    se intercalar em qualquer ordem (caso de agentes, que decidem em tempo de
    execução quando chamar uma tool de busca)."""
    async for chunk in chunks:
        if isinstance(chunk, SourcesChunk):
            yield f"event: sources\ndata: {json.dumps(chunk.sources)}\n\n"
        else:
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"
