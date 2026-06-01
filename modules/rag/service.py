from langchain_core.vectorstores import VectorStore

from modules.rag.retrieval.base import RetrievedDocument


class RAGService:
    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    def ingest(self, source: str) -> None:
        pass

    def retrieve(self, query: str) -> list[RetrievedDocument]:
        pass
