from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.documents import Document


@dataclass
class RetrievedDocument:
    document: Document
    score: float


class BaseRetriever(ABC):
    @abstractmethod
    async def asearch(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        """Recupera documentos relevantes para uma query de forma assíncrona."""
        ...
