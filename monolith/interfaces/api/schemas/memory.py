import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MemoryOrigin(BaseModel):
    turn_id: uuid.UUID
    thread_id: uuid.UUID
    event: str
    user_message: str
    assistant_message: str
    sources: list[dict] = Field(
        description="Sources do RAG vistas no turno que gerou a memória"
    )
    recalled_memory_ids: list[str] = Field(
        description="Memórias injetadas no prompt do turno que gerou esta"
    )
    recorded_at: datetime


class MemoryTraceResponse(BaseModel):
    id: str = Field(description="Id da memória no motor")
    content: str
    engine_metadata: dict = Field(
        description="Tudo o que o MOTOR expõe sobre a memória, sem tratamento"
    )
    engine_history: list[dict] = Field(
        description="Histórico da memória segundo o próprio motor"
    )
    origins: list[MemoryOrigin] = Field(
        description="De onde a memória veio segundo o LEDGER — o que o motor "
        "deveria conseguir responder sozinho"
    )


class UserMemoriesResponse(BaseModel):
    engine: str
    memories: list[MemoryTraceResponse]
