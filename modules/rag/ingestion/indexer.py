import logging

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from modules.rag.ingestion.base import BaseIndexer

logger = logging.getLogger(__name__)


class VectorStoreIndexer(BaseIndexer):
    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    def index(self, chunks: list[Document]) -> None:
        logger.info("Indexing %d chunks", len(chunks))
        self._vector_store.add_documents(chunks)
        logger.debug("Indexed %d chunks successfully", len(chunks))
