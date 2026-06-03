from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl

from modules.rag.service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return RAGService.with_defaults()


RAGServiceDeps = Annotated[RAGService, Depends(get_rag_service)]


class IngestRequest(BaseModel):
    source: HttpUrl = Field(..., description="URL do documento a ser ingerido")


class IngestResponse(BaseModel):
    message: str = Field(..., description="Mensagem de confirmação da ingestão")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Pergunta a ser respondida")
    top_k: int = Field(
        5, gt=0, le=20, description="Número de chunks relevantes a serem recuperados"
    )


class RetrievedChunk(BaseModel):
    content: str = Field(..., description="Conteúdo do chunk recuperado")
    score: float = Field(..., description="Pontuação de relevância do chunk")


class SearchResponse(BaseModel):
    results: list[RetrievedChunk] = Field(
        ..., description="Lista de chunks relevantes encontrados"
    )


class AskResponse(BaseModel):
    answer: str = Field(..., description="Resposta gerada para a pergunta")


@router.post("/ingest", status_code=201, response_model=IngestResponse)
async def ingest(service: RAGServiceDeps, request: IngestRequest):
    await service.ingest(request.source)
    return IngestResponse(message="Documento processado com sucesso.")


@router.post("/search", status_code=200, response_model=SearchResponse)
def search(service: RAGServiceDeps, request: QueryRequest):
    results = service.search(request.query, request.top_k)
    return SearchResponse(results=results)


@router.post("/ask", status_code=200, response_model=AskResponse)
def ask(service: RAGServiceDeps, request: QueryRequest):
    response = service.ask(request.query, request.top_k)
    return AskResponse(answer=response)
