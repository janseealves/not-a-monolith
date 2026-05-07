import logging

from langchain_core.vectorstores import VectorStore
from modules.rag.ingestion.base import BaseIndexer, Chunk

logger = logging.getLogger(__name__)


class VectorStoreIndexer(BaseIndexer):
    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    def index(self, chunks: list[Chunk]) -> None:
        logger.info("Indexing %d chunks", len(chunks))

        texts = [chunk.content for chunk in chunks]
        metadata = [
            {"source": chunk.source, "number": chunk.number} for chunk in chunks
        ]

        self._vector_store.add_texts(texts=texts, metadatas=metadata)
        logger.debug("Indexed %d chunks successfully", len(chunks))
