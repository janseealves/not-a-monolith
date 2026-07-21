from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from monolith.interfaces.api.dependencies import get_chat_service
from monolith.interfaces.api.schemas.agent import ChatRequest
from monolith.modules.agents.chat.service import ChatService
from monolith.modules.rag import crud as rag_crud
from monolith.shared.streaming import sse_stream

router = APIRouter(prefix="/agent", tags=["Agent"])

ChatServiceDeps = Annotated[ChatService, Depends(get_chat_service)]


@router.post("/chat", status_code=status.HTTP_200_OK)
async def chat(service: ChatServiceDeps, request: ChatRequest):
    # A collection é opcional; quando vem, resolvemos o UUID externo → id interno
    # antes de entrar no domínio (a tool só conhece o id interno).
    collection_pk: int | None = None
    if request.collection_id is not None:
        collection = await rag_crud.get_collection_by_external_id(request.collection_id)
        if collection is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection não encontrada.")
        collection_pk = collection.id

    stream = service.astream(request.message, str(request.thread_id), collection_pk)
    return StreamingResponse(sse_stream(stream), media_type="text/event-stream")
