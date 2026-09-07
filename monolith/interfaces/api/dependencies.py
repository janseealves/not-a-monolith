import uuid

from fastapi import HTTPException, Request, status

from monolith.modules.agents.chat.service import ChatService
from monolith.modules.rag import crud
from monolith.modules.rag.models import Collection
from monolith.modules.rag.service import RAGService
from monolith.shared.storage import ObjectStore


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_object_store(request: Request) -> ObjectStore:
    return request.app.state.object_store


async def get_collection(collection_id: uuid.UUID) -> Collection:
    collection = await crud.get_collection_by_external_id(collection_id)
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection não encontrada.")
    return collection
