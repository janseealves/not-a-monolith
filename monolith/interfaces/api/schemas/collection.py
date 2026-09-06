import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., description="Nome único da collection")
    description: str | None = Field(None, description="Descrição da collection")


class CollectionResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Identificador público da collection")
    name: str = Field(..., description="Nome único da collection")
    description: str | None = Field(None, description="Descrição da collection")
    created_at: datetime = Field(..., description="Data de criação da collection")
