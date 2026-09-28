from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from monolith.shared.streaming import SourcesChunk


class BaseAgent(ABC):
    @abstractmethod
    def astream(
        self,
        message: str,
        thread_id: str,
        collection_id: int | None = None,
        memories: list[str] | None = None,
    ) -> AsyncIterator[str | SourcesChunk]:
        """Processa uma mensagem numa conversa (thread) e streama a resposta em tokens.

        thread_id identifica a conversa — é o que dá memória multi-turno ao agente.
        collection_id, quando presente, escopa a busca do agente numa collection.
        memories são as memórias de longo prazo já recuperadas para este turno;
        o agente só as usa, quem busca e grava é o ChatService.
        """
        ...
