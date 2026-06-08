import logging

from langchain_core.vectorstores import VectorStore

from modules.rag.retrieval.base import BaseRetriever, RetrievedDocument

logger = logging.getLogger(__name__)


class SemanticRetriever(BaseRetriever):
    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        logger.info("Retrieving top %d chunks for query: '%s'", top_k, query)
        result = self._vector_store.similarity_search_with_score(query, k=top_k)

        if not result:
            logger.warning("No chunks retrieved.")
            return []

        logger.debug(
            "Retrieved chunks: %d | Preview: %s",
            len(result),
            result[0][0].page_content[:50],
        )
        return [
            RetrievedDocument(document=document, score=score)
            for document, score in result
        ]


class HybridRetriever(BaseRetriever):
    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        pass


# TODO: implementar um retriever que decomponha a query em subqueries e faça múltiplas buscas, combinando os resultados (ex: usando um modelo para gerar reformulações da query original)
class MultiQueryRetriever(BaseRetriever):
    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    async def asearch(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        pass
