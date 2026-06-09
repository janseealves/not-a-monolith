from abc import ABC, abstractmethod

from langchain_core.documents import Document


class BaseParser(ABC):
    @abstractmethod
    async def load(self, source: str) -> Document:
        """Carrega documentos a partir de uma fonte (URL, caminho, etc.)."""
        ...


class BaseChunker(ABC):
    @abstractmethod
    def split(self, document: Document) -> list[Document]:
        """Divide documentos em chunks menores."""
        ...


class BaseIndexer(ABC):
    @abstractmethod
    async def index(self, document: Document, chunks: list[Document]) -> None:
        """Indexa e armazena um documento e seus chunks."""
        ...
