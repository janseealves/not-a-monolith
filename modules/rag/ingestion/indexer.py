import hashlib
import logging
from datetime import UTC, datetime

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from modules.rag.ingestion.base import BaseIndexer
from modules.rag.models import Chunk, collection_documents
from modules.rag.models import Document as DocumentModel

logger = logging.getLogger(__name__)

# Prompt de documento do EmbeddingGemma. O título entra no embedding, não é só metadado.
_DOC_PROMPT = "title: {title} | text: {content}"


class PostgresIndexer(BaseIndexer):
    def __init__(
        self, session_factory: async_sessionmaker, embeddings: Embeddings
    ) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def index(
        self, document: Document, chunks: list[Document], collection_id: int
    ) -> None:
        if not chunks:
            logger.warning(
                "No chunks to index for source %s", document.metadata.get("source")
            )
            return

        title = document.metadata.get("title") or "none"
        source = document.metadata.get("source", "")
        content_hash = hashlib.sha256(document.page_content.encode("utf-8")).hexdigest()

        # Reaproveita: se o conteúdo já foi processado (em qualquer collection),
        # não reembeda — só garante o vínculo com esta collection.
        # Leitura numa sessão à parte: a sessão de escrita abaixo precisa começar
        # "limpa" pra poder abrir sua própria transação com session.begin().
        async with self._session_factory() as session:
            existing_id = await session.scalar(
                select(DocumentModel.id).where(
                    DocumentModel.content_hash == content_hash
                )
            )
            already_linked = (
                await session.scalar(
                    select(collection_documents.c.document_id).where(
                        collection_documents.c.document_id == existing_id,
                        collection_documents.c.collection_id == collection_id,
                    )
                )
                if existing_id is not None
                else None
            )

        if existing_id is not None:
            if already_linked is None:
                async with self._session_factory() as session, session.begin():
                    await session.execute(
                        insert(collection_documents).values(
                            document_id=existing_id, collection_id=collection_id
                        )
                    )
                logger.info(
                    "Document already indexed elsewhere, linked to collection %d: %s",
                    collection_id,
                    source,
                )
            else:
                logger.info("Document already indexed and linked, skipping: %s", source)
            return

        # 1. Embeddings PRIMEIRO, fora da transação — é uma chamada de rede ao Ollama.
        prompts = [
            _DOC_PROMPT.format(title=title, content=chunk.page_content)
            for chunk in chunks
        ]
        vectors = await self._embeddings.aembed_documents(prompts)

        # 2. Transação curta: grava o documento e seus chunks.
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            doc_model = DocumentModel(
                title=title,
                source=source,
                content_hash=content_hash,
                created_at=now,
            )
            session.add(doc_model)
            await session.flush()  # garante doc_model.id antes dos chunks

            session.add_all(
                [
                    Chunk(
                        document_id=doc_model.id,
                        chunk_index=idx,
                        content=chunk.page_content,
                        embedding=vector,
                        created_at=now,
                    )
                    for idx, (chunk, vector) in enumerate(
                        zip(chunks, vectors, strict=True)
                    )
                ]
            )
            await session.execute(
                insert(collection_documents).values(
                    document_id=doc_model.id, collection_id=collection_id
                )
            )

        logger.info("Indexed %d chunks for document %s", len(chunks), source)
