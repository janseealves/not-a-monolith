import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from langchain_core.documents import Document
from pydantic import BaseModel


class LocalSource(BaseModel):
    path: Path


class WebSource(BaseModel):
    url: str


class ObjectStoreSource(BaseModel):
    bucket: str
    key: str
    endpoint: str | None = None


Source = LocalSource | WebSource | ObjectStoreSource


class BaseParser(ABC):
    @abstractmethod
    async def load(self, source: Source) -> Document:
        """Carrega documentos a partir de uma fonte tipada."""
        ...


class BaseChunker(ABC):
    @abstractmethod
    def split(self, document: Document) -> list[Document]:
        """Divide documentos em chunks menores."""
        ...


class BaseIndexer(ABC):
    @abstractmethod
    async def index(
        self, document: Document, chunks: list[Document], collection_id: int
    ) -> uuid.UUID:
        """Indexa um documento e seus chunks, associando-os à collection informada.

        Devolve o external_id do documento — é por ele que o cliente pede a
        referência depois, e ele pode ser de um documento que já existia.
        """
        ...
