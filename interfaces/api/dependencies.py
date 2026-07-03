import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from modules.rag.collection_service import CollectionService
from modules.rag.models import Collection
from modules.rag.service import RAGService


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_collection_service(request: Request) -> CollectionService:
    return request.app.state.collection_service


async def get_collection(
    collection_id: uuid.UUID,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> Collection:
    collection = await service.get_by_external_id(collection_id)
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection não encontrada.")
    return collection
