from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.documents import Document


@dataclass
class RetrievedDocument:
    document: Document
    score: float


class BaseRetriever(ABC):
    @abstractmethod
    async def asearch(
        self, query: str, collection_id: int, top_k: int = 5
    ) -> list[RetrievedDocument]:
        """Recupera documentos relevantes de uma collection para uma query."""
        ...
