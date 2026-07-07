import uuid

from fastapi import HTTPException, Request, status

from modules.agents.service import AgentService
from modules.rag import crud
from modules.rag.models import Collection
from modules.rag.service import RAGService


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_agent_service(request: Request) -> AgentService:
    return request.app.state.agent_service


async def get_collection(collection_id: uuid.UUID) -> Collection:
    collection = await crud.get_collection_by_external_id(collection_id)
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection não encontrada.")
    return collection
