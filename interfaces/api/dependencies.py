from fastapi import Request

from modules.rag.service import RAGService


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service
