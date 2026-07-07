from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseAgent(ABC):
    @abstractmethod
    def astream(
        self,
        message: str,
        thread_id: str,
        collection_id: int | None = None,
    ) -> AsyncIterator[str]:
        """Processa uma mensagem numa conversa (thread) e streama a resposta em tokens.

        thread_id identifica a conversa — é o que dá memória multi-turno ao agente.
        collection_id, quando presente, escopa a busca do agente numa collection.
        """
        ...
