import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MemoryItem:
    """Uma memória como o MOTOR a devolve — id e metadata são os dele."""

    id: str
    content: str
    score: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryWrite:
    """Um evento de escrita que o motor reportou ao processar um turno."""

    memory_id: str
    content: str
    event: str  # ADD / UPDATE / DELETE, no vocabulário do motor


@dataclass
class Turn:
    """Um turno completo da conversa: a unidade que o hook entrega ao motor.

    Carrega o que o ledger precisa para reconstruir a proveniência por fora do
    motor — inclusive as sources do RAG, que o motor nunca vê: ele só recebe o
    texto da resposta, onde um trecho de PDF pode ter chegado sem etiqueta.
    """

    user_id: uuid.UUID
    thread_id: uuid.UUID
    user_message: str
    assistant_message: str
    collection_id: int | None = None
    sources: list[dict] = field(default_factory=list)
    recalled: list[MemoryItem] = field(default_factory=list)
    id: uuid.UUID = field(default_factory=uuid.uuid4)


class BaseMemory(ABC):
    """Contrato comum aos motores de memória. Cada adapter expõe só o que o motor
    oferece de fato: o que faltar aqui é, em si, um dado da comparação."""

    name: str

    @abstractmethod
    async def asearch(
        self, query: str, user_id: uuid.UUID, top_k: int = 5
    ) -> list[MemoryItem]:
        """Memórias do usuário relevantes para a query."""
        ...

    @abstractmethod
    async def aadd(self, turn: Turn, metadata: dict | None = None) -> list[MemoryWrite]:
        """Entrega o turno ao motor e devolve os eventos de escrita que ele reportou.

        metadata, quando vem, é repassada ao motor como está — se ela sobrevive
        até a leitura é justamente o que se quer medir.
        """
        ...

    @abstractmethod
    async def alist(self, user_id: uuid.UUID) -> list[MemoryItem]:
        """Todas as memórias do usuário, como o motor as guarda."""
        ...

    @abstractmethod
    async def ahistory(self, memory_id: str) -> list[dict]:
        """Histórico de uma memória segundo o próprio motor (vazio se ele não tem)."""
        ...
