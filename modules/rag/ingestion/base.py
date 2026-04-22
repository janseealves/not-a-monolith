from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Document:
    metadata: dict
    content: str


@dataclass
class Chunk:
    source: dict
    number: tuple[int, int]
    content: str


class BaseParser(ABC):
    @abstractmethod
    def load(self, source: str) -> Document:
        """Carrega documentos a partir de uma fonte (URL, caminho, etc.)."""
        ...


class BaseChunker(ABC):
    @abstractmethod
    def split(self, document: Document) -> list[Chunk]:
        """Divide documentos em chunks menores."""
        ...


class BaseIndexer(ABC):
    @abstractmethod
    def index(self, source: str) -> list[Chunk]:
        """Indexa documentos a partir de uma fonte, realizando parsing e chunking."""
        ...
