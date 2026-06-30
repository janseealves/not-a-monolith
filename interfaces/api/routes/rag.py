from typing import Annotated

from fastapi import APIRouter, Depends, status

from interfaces.api.dependencies import get_rag_service
from interfaces.api.schemas.rag import (
    AskResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    RetrievedChunk,
    SearchResponse,
)
from modules.rag.service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


RAGServiceDeps = Annotated[RAGService, Depends(get_rag_service)]


@router.post(
    "/ingest", status_code=status.HTTP_201_CREATED, response_model=IngestResponse
)
async def ingest(service: RAGServiceDeps, request: IngestRequest):
    await service.ingest(request.to_source())
    return IngestResponse(message="Documento processado com sucesso.")


@router.post("/search", status_code=status.HTTP_200_OK, response_model=SearchResponse)
async def search(service: RAGServiceDeps, request: QueryRequest):
    r = await service.search(request.query, request.top_k)
    return SearchResponse(
        results=[
            RetrievedChunk(
                content=doc.document.page_content,
                score=doc.score,
            )
            for doc in r
        ]
    )


@router.post("/ask", status_code=status.HTTP_200_OK, response_model=AskResponse)
async def ask(service: RAGServiceDeps, request: QueryRequest):
    response = await service.ask(request.query, request.top_k)
    return AskResponse(answer=response)
