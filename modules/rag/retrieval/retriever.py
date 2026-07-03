import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from modules.rag.models import Chunk, collection_documents
from modules.rag.models import Document as DocumentModel
from modules.rag.retrieval.base import BaseRetriever, RetrievedDocument

logger = logging.getLogger(__name__)

# Prompt de query do EmbeddingGemma (assimétrico em relação ao de documento).
_QUERY_PROMPT = "task: search result | query: {query}"


class SemanticRetriever(BaseRetriever):
    """Busca densa por similaridade de vetores no pgvector (índice HNSW)."""

    def __init__(
        self, session_factory: async_sessionmaker, embeddings: Embeddings
    ) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def asearch(
        self, query: str, collection_id: int, top_k: int = 5
    ) -> list[RetrievedDocument]:
        logger.info(
            "Retrieving top %d chunks for query: '%s' (collection=%d)",
            top_k,
            query,
            collection_id,
        )
        query_vector = await self._embeddings.aembed_query(
            _QUERY_PROMPT.format(query=query)
        )

        # cosine_distance casa com o índice HNSW vector_cosine_ops. Menor = mais próximo.
        distance = Chunk.embedding.cosine_distance(query_vector).label("distance")
        stmt = (
            select(
                Chunk.content,
                Chunk.chunk_index,
                DocumentModel.source,
                DocumentModel.title,
                distance,
            )
            .join(DocumentModel, Chunk.document_id == DocumentModel.id)
            .join(
                collection_documents,
                collection_documents.c.document_id == DocumentModel.id,
            )
            .where(collection_documents.c.collection_id == collection_id)
            .order_by(distance)
            .limit(top_k)
        )

        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).all()

        if not rows:
            logger.warning("No chunks retrieved.")
            return []

        logger.debug(
            "Retrieved chunks: %d | Preview: %s", len(rows), rows[0].content[:50]
        )
        return [
            RetrievedDocument(
                document=Document(
                    page_content=row.content,
                    metadata={
                        "source": row.source,
                        "title": row.title,
                        "chunk_index": row.chunk_index,
                    },
                ),
                # distância -> similaridade (1 = idêntico), p/ manter "maior = melhor".
                score=1 - row.distance,
            )
            for row in rows
        ]


class HybridRetriever(BaseRetriever):
    def __init__(self, session_factory, embeddings):
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def asearch(
        self, query: str, collection_id: int, top_k: int = 5
    ) -> list[RetrievedDocument]:
        pass


# TODO: implementar um retriever que decomponha a query em subqueries e faça múltiplas buscas, combinando os resultados (ex: usando um modelo para gerar reformulações da query original)
class MultiQueryRetriever(BaseRetriever):
    def __init__(self, session_factory, embeddings):
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def asearch(
        self, query: str, collection_id: int, top_k: int = 5
    ) -> list[RetrievedDocument]:
        pass
