import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from monolith.modules.memory import crud
from monolith.modules.memory.base import BaseMemory, MemoryItem, MemoryWrite, Turn
from monolith.shared.config import Settings
from monolith.shared.config import settings as default_settings
from monolith.shared.llm import build_chat_model, build_embeddings

logger = logging.getLogger(__name__)


@dataclass
class Origin:
    """De onde uma memória veio, segundo o ledger (não segundo o motor)."""

    turn_id: uuid.UUID
    thread_id: uuid.UUID
    event: str
    user_message: str
    assistant_message: str
    sources: list[dict]
    # Memórias injetadas no prompt do turno de origem: é o que liga uma memória
    # derivada à memória (talvez contaminada) que a induziu.
    recalled_memory_ids: list[str]
    recorded_at: datetime


@dataclass
class MemoryTrace:
    """Uma memória lado a lado: o que o motor diz dela e o que o ledger sabe."""

    memory: MemoryItem
    engine_history: list[dict]
    origins: list[Origin]


class MemoryService:
    """Ponto único entre o agente e o motor de memória — e, por isso, onde o
    ledger é gravado: todo turno passa por aqui, seja qual for o motor."""

    def __init__(self, memory: BaseMemory, settings: Settings | None = None) -> None:
        self._memory = memory
        self._settings = settings or default_settings

    @property
    def engine(self) -> str:
        return self._memory.name

    @classmethod
    def with_defaults(cls, settings: Settings | None = None) -> "MemoryService":
        settings = settings or default_settings

        # único lugar do módulo que conhece as classes concretas. Import local:
        # cada motor puxa dependências pesadas, e só o escolhido deve carregar.
        match settings.AGENT_MEMORY:
            case "mem0":
                from monolith.modules.memory.mem0.engine import Mem0Memory

                memory = Mem0Memory.from_settings(
                    settings, build_chat_model(settings), build_embeddings(settings)
                )
            case other:
                raise ValueError(f"Motor de memória desconhecido: {other}")

        return cls(memory, settings)

    async def recall(self, query: str, user_id: uuid.UUID) -> list[MemoryItem]:
        return await self._memory.asearch(
            query, user_id, top_k=self._settings.MEMORY_TOP_K
        )

    async def record(self, turn: Turn) -> list[MemoryWrite]:
        """Entrega o turno ao motor e grava no ledger o que ele reportou."""
        metadata = None
        if self._settings.MEMORY_PROPAGATE_PROVENANCE:
            metadata = {"turn_id": str(turn.id), "thread_id": str(turn.thread_id)}

        writes: list[MemoryWrite] = []
        error = None
        try:
            writes = await self._memory.aadd(turn, metadata)
        except Exception as e:
            # A conversa não pode cair porque a memória falhou; mas a falha fica
            # no ledger — memória que some sem rastro é o que se está medindo.
            logger.exception("Memory engine %s failed to add turn", self.engine)
            error = repr(e)

        await crud.record_turn(turn, self.engine, writes, error)
        logger.info(
            "Memory turn %s recorded (engine=%s, writes=%d)",
            turn.id,
            self.engine,
            len(writes),
        )
        return writes

    async def inspect(self, user_id: uuid.UUID) -> list[MemoryTrace]:
        memories = await self._memory.alist(user_id)
        writes = await crud.get_writes_by_memory_ids([m.id for m in memories])

        origins: dict[str, list[Origin]] = {}
        for w in writes:
            origins.setdefault(w.memory_id, []).append(
                Origin(
                    turn_id=w.turn.external_id,
                    thread_id=w.turn.thread_id,
                    event=w.event,
                    user_message=w.turn.user_message,
                    assistant_message=w.turn.assistant_message,
                    sources=w.turn.sources,
                    recalled_memory_ids=w.turn.recalled_memory_ids,
                    recorded_at=w.created_at,
                )
            )

        return [
            MemoryTrace(
                memory=m,
                engine_history=await self._memory.ahistory(m.id),
                origins=origins.get(m.id, []),
            )
            for m in memories
        ]
