import logging
import uuid
from pathlib import Path

from langchain.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from mem0 import AsyncMemory

from monolith.modules.memory.base import BaseMemory, MemoryItem, MemoryWrite, Turn
from monolith.shared.config import Settings

logger = logging.getLogger(__name__)


class Mem0Memory(BaseMemory):
    """mem0 OSS: um LLM extrai fatos do turno e os grava como vetores no pgvector.

    O que ele NÃO guarda, e por isso fica a cargo do ledger: de qual turno veio
    cada memória. O histórico dele (SQLite) registra o evento, não a origem.
    """

    name = "mem0"

    def __init__(self, memory: AsyncMemory) -> None:
        self._memory = memory

    @classmethod
    def from_settings(
        cls, settings: Settings, llm: BaseChatModel, embeddings: Embeddings
    ) -> "Mem0Memory":
        Path(settings.MEM0_HISTORY_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        memory = AsyncMemory.from_config(
            {
                "vector_store": {
                    "provider": "pgvector",
                    "config": {
                        # Mesmo Postgres do app, em tabela própria (fora do Alembic,
                        # como o checkpointer): o mem0 cria e mantém o schema dela.
                        "connection_string": settings.get_checkpointer_url,
                        "collection_name": "mem0_memories",
                        "embedding_model_dims": 768,
                    },
                },
                # Provider "langchain": o mem0 usa as MESMAS instâncias do agente,
                # e as chamadas de extração ficam visíveis no LangSmith.
                "llm": {"provider": "langchain", "config": {"model": llm}},
                "embedder": {"provider": "langchain", "config": {"model": embeddings}},
                "history_db_path": settings.MEM0_HISTORY_DB_PATH,
            }
        )
        return cls(memory)

    async def asearch(
        self, query: str, user_id: uuid.UUID, top_k: int = 5
    ) -> list[MemoryItem]:
        result = await self._memory.search(
            query, filters={"user_id": str(user_id)}, top_k=top_k
        )
        return [_to_item(r) for r in result["results"]]

    async def aadd(self, turn: Turn, metadata: dict | None = None) -> list[MemoryWrite]:
        # Só user + assistant, como numa integração típica. O conteúdo das tools
        # (trechos do RAG) não entra — se chegar à memória, foi pela resposta.
        result = await self._memory.add(
            [
                {"role": "user", "content": turn.user_message},
                {"role": "assistant", "content": turn.assistant_message},
            ],
            user_id=str(turn.user_id),
            metadata=metadata,
        )
        return [
            MemoryWrite(memory_id=r["id"], content=r["memory"], event=r["event"])
            for r in result["results"]
        ]

    async def alist(self, user_id: uuid.UUID) -> list[MemoryItem]:
        result = await self._memory.get_all(
            filters={"user_id": str(user_id)}, top_k=100
        )
        return [_to_item(r) for r in result["results"]]

    async def ahistory(self, memory_id: str) -> list[dict]:
        return await self._memory.history(memory_id)


def _to_item(raw: dict) -> MemoryItem:
    # Tudo além de id/texto/score vai como metadata "crua": é o que o motor
    # expõe de si, e a comparação precisa ver exatamente isso.
    metadata = {k: v for k, v in raw.items() if k not in ("id", "memory", "score")}
    return MemoryItem(
        id=raw["id"], content=raw["memory"], score=raw.get("score"), metadata=metadata
    )
