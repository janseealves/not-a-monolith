import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensagem do usuário para o agente")
    thread_id: uuid.UUID = Field(
        ..., description="Id da conversa; mantém a memória multi-turno do agente"
    )
    collection_id: uuid.UUID | None = Field(
        None,
        description="Collection que escopa a busca do agente. Sem ela, o agente "
        "conversa sem acesso à base de conhecimento.",
    )
