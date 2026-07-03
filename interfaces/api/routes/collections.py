from typing import Annotated

from fastapi import APIRouter, Depends, status

from interfaces.api.dependencies import get_collection_service
from interfaces.api.schemas.collection import (
    CollectionResponse,
    CreateCollectionRequest,
)
from modules.rag.collection_service import CollectionService
from modules.rag.models import Collection

router = APIRouter(prefix="/rag/collections", tags=["Collections"])


CollectionServiceDeps = Annotated[CollectionService, Depends(get_collection_service)]


def _to_response(collection: Collection) -> CollectionResponse:
    return CollectionResponse(
        id=collection.external_id,
        name=collection.name,
        description=collection.description,
        created_at=collection.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CollectionResponse)
async def create(service: CollectionServiceDeps, request: CreateCollectionRequest):
    collection = await service.create(request.name, request.description)
    return _to_response(collection)


@router.get("", status_code=status.HTTP_200_OK, response_model=list[CollectionResponse])
async def list_collections(service: CollectionServiceDeps):
    collections = await service.list()
    return [_to_response(c) for c in collections]
