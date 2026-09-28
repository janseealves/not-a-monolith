import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status

from monolith.interfaces.api.dependencies import get_memory_service
from monolith.interfaces.api.schemas.memory import (
    MemoryOrigin,
    MemoryTraceResponse,
    UserMemoriesResponse,
)
from monolith.modules.memory.service import MemoryService

router = APIRouter(prefix="/memory", tags=["Memory"])

MemoryServiceDeps = Annotated[MemoryService, Depends(get_memory_service)]


@router.get(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserMemoriesResponse,
)
async def inspect_user_memories(service: MemoryServiceDeps, user_id: uuid.UUID):
    traces = await service.inspect(user_id)
    return UserMemoriesResponse(
        engine=service.engine,
        memories=[
            MemoryTraceResponse(
                id=t.memory.id,
                content=t.memory.content,
                engine_metadata=t.memory.metadata,
                engine_history=t.engine_history,
                origins=[MemoryOrigin(**asdict(o)) for o in t.origins],
            )
            for t in traces
        ],
    )
