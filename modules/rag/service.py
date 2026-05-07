from langchain_core.vectorstores import VectorStore

class RAGService:
    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    def ingest(self, source: str) -> None:
        pass

    def retriever(selff, query: str) -> list[str]: 
        pass