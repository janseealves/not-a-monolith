from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from monolith.interfaces.api.dependencies import get_collection, get_rag_service
from monolith.interfaces.api.schemas.rag import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    RetrievedChunk,
    SearchResponse,
)
from monolith.modules.rag.models import Collection
from monolith.modules.rag.service import RAGService
from monolith.shared.streaming import sse_stream

router = APIRouter(prefix="/rag/collections/{collection_id}", tags=["RAG"])


RAGServiceDeps = Annotated[RAGService, Depends(get_rag_service)]
CollectionDeps = Annotated[Collection, Depends(get_collection)]


@router.post(
    "/ingest", status_code=status.HTTP_201_CREATED, response_model=IngestResponse
)
async def ingest(
    service: RAGServiceDeps, collection: CollectionDeps, request: IngestRequest
):
    await service.ingest(request.to_source(), collection.id)
    return IngestResponse(message="Documento processado com sucesso.")


@router.post("/search", status_code=status.HTTP_200_OK, response_model=SearchResponse)
async def search(
    service: RAGServiceDeps, collection: CollectionDeps, request: QueryRequest
):
    r = await service.search(request.query, collection.id, request.top_k)
    return SearchResponse(
        results=[
            RetrievedChunk(
                content=doc.document.page_content,
                score=doc.score,
            )
            for doc in r
        ]
    )


@router.post("/ask", status_code=status.HTTP_200_OK)
async def ask(
    service: RAGServiceDeps, collection: CollectionDeps, request: QueryRequest
):
    chunks = service.astream_ask(request.query, collection.id, request.top_k)
    return StreamingResponse(sse_stream(chunks), media_type="text/event-stream")
