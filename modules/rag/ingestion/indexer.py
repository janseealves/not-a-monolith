import logging

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from modules.rag.ingestion.base import BaseIndexer, Chunk

logger = logging.getLogger(__name__)


class OpenAIIndexer(BaseIndexer):
    def __init__(self):
        self._embedding = OpenAIEmbeddings()
        self._vector_store = InMemoryVectorStore(embedding=self._embedding)

    def index(self, chunks: list[Chunk]) -> None:
        logger.info("Indexing %d chunks", len(chunks))

        texts = [chunk.content for chunk in chunks]
        metadata = [
            {"source": chunk.source, "number": chunk.number} for chunk in chunks
        ]

        self._vector_store.add_texts(texts=texts, metadatas=metadata)
        logger.debug("Indexed %d chunks successfully", len(chunks))
