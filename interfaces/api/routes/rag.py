from functools import lru_cache
from fastapi import APIRouter
from fastapi import Depends, Body, Query
from modules.rag.service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])

@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return RAGService.with_defaults()

@router.post("/ingest")
async def ingest(service: RAGService = Depends(get_rag_service), source: str = Body(..., embed=True)):
    await service.ingest(source)

@router.get("/search")
async def search(service: RAGService = Depends(get_rag_service), query: str = Body(...), top_k: int = Query(5)):
    return await service.search(query, top_k)

@router.get("/ask")
async def ask(service: RAGService = Depends(get_rag_service), query: str = Body(...), top_k: int = Query(5)):
    return await service.ask(query, top_k)
