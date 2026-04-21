from abc import ABC, abstractmethod

from langchain_core.documents import Document


class BaseParser(ABC):
    @abstractmethod
    def load(self, source: str) -> list[Document]:
        """Carrega documentos a partir de uma fonte (URL, caminho, etc.)."""
        ...


class BaseChunker(ABC):
    @abstractmethod
    def split(self, documents: list[Document]) -> list[Document]:
        """Divide documentos em chunks menores."""
        ...
