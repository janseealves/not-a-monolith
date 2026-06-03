import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.documents import Document


@dataclass
class RetrievedDocument:
    document: Document
    score: float


class BaseRetriever(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        """Recupera documentos relevantes para uma query."""
        ...

    async def asearch(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        """Recupera documentos relevantes para uma query de forma assíncrona."""
        return await asyncio.to_thread(self.search, query, top_k)
