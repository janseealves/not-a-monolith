from fastapi import APIRouter, status

from interfaces.api.schemas.collection import (
    CollectionResponse,
    CreateCollectionRequest,
)
from modules.rag import crud
from modules.rag.models import Collection

router = APIRouter(prefix="/rag/collections", tags=["Collections"])


def _to_response(collection: Collection) -> CollectionResponse:
    return CollectionResponse(
        id=collection.external_id,
        name=collection.name,
        description=collection.description,
        created_at=collection.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CollectionResponse)
async def create(request: CreateCollectionRequest):
    collection = await crud.create_collection(request.name, request.description)
    return _to_response(collection)


@router.get("", status_code=status.HTTP_200_OK, response_model=list[CollectionResponse])
async def list_collections():
    collections = await crud.list_collections()
    return [_to_response(c) for c in collections]
