import logging
import tempfile
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from langchain.chat_models import BaseChatModel
from langchain_ollama import OllamaEmbeddings
from sqlalchemy.ext.asyncio import async_sessionmaker

from monolith.modules.rag.ingestion.base import (
    BaseChunker,
    BaseIndexer,
    BaseParser,
    LocalSource,
    Source,
    WebSource,
)
from monolith.modules.rag.ingestion.chunker import RecursiveChunker
from monolith.modules.rag.ingestion.indexer import PostgresIndexer
from monolith.modules.rag.ingestion.parser import ParserRouter, PDFParser, WebParser
from monolith.modules.rag.retrieval.base import BaseRetriever, RetrievedDocument
from monolith.modules.rag.retrieval.retriever import SemanticRetriever
from monolith.shared.config import Settings
from monolith.shared.config import settings as default_settings
from monolith.shared.db.session import SessionLocal
from monolith.shared.llm import build_chat_model
from monolith.shared.prompts import render_prompt
from monolith.shared.storage import ObjectStore

logger = logging.getLogger(__name__)


@dataclass
class SourceInfo:
    source: str
    title: str
    chunk_ids: list[str]


@dataclass
class AskResult:
    sources: list[SourceInfo]
    stream: AsyncIterator[str]


def build_sources(chunks: list[RetrievedDocument]) -> list[SourceInfo]:
    # agrupa por source: vários chunks costumam vir do mesmo documento.
    # O título vai junto porque o source de um PDF é uma URI s3:// com um uuid
    # no nome — ilegível para quem lê a citação.
    grouped: dict[str, SourceInfo] = {}
    for chunk in chunks:
        source = chunk.document.metadata.get("source", "desconhecida")
        info = grouped.setdefault(
            source,
            SourceInfo(
                source=source,
                title=chunk.document.metadata.get("title") or source,
                chunk_ids=[],
            ),
        )
        info.chunk_ids.append(chunk.document.metadata["chunk_id"])
    return list(grouped.values())


class RAGService:
    def __init__(
        self,
        parser: BaseParser,
        chunker: BaseChunker,
        indexer: BaseIndexer,
        retriever: BaseRetriever,
        llm: BaseChatModel,
        store: ObjectStore,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._indexer = indexer
        self._retriever = retriever
        self._llm = llm
        self._store = store

    @classmethod
    def with_defaults(
        cls,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
        session_factory: async_sessionmaker | None = None,
        store: ObjectStore | None = None,
    ) -> "RAGService":
        settings = settings or default_settings
        session_factory = session_factory or SessionLocal
        embeddings = OllamaEmbeddings(
            model=settings.EMBEDDINGS_MODEL,
            base_url=settings.EMBEDDINGS_BASE_URL,
        )

        # único lugar do módulo que conhece as classes concretas
        return cls(
            # Um parser por tipo de fonte: URL vai pro crawler, arquivo vai pro PDF.
            parser=ParserRouter({WebSource: WebParser(), LocalSource: PDFParser()}),
            chunker=RecursiveChunker(),
            indexer=PostgresIndexer(session_factory, embeddings),
            retriever=SemanticRetriever(session_factory, embeddings),
            llm=build_chat_model(settings),
            store=store or ObjectStore(settings),
        )

    async def ingest(
        self, source: Source, collection_id: int, metadata: dict | None = None
    ) -> uuid.UUID:
        """Indexa a fonte. `metadata` sobrescreve o que o parser inferiu.

        Num upload o parser só enxerga o arquivo temporário: quem sabe a fonte
        durável e o nome real do arquivo é quem recebeu o request.
        """
        document = await self._parser.load(source)
        if metadata:
            document.metadata.update(metadata)
        chunks = self._chunker.split(document)
        return await self._indexer.index(document, chunks, collection_id)

    async def ingest_upload(
        self, filename: str, data: bytes, content_type: str, collection_id: int
    ) -> uuid.UUID:
        """Guarda o binário no object store e indexa o conteúdo dele."""
        suffix = Path(filename).suffix.lower()
        # O nome vem do cliente: só o sufixo é aproveitado, o resto é um uuid.
        key = f"{uuid.uuid4()}{suffix}"

        # Grava ANTES de indexar. Falhando aqui, nada foi para o banco; na ordem
        # inversa sobraria um documento indexado apontando para um objeto que
        # não existe, e a rota de referência devolveria 404 para sempre.
        uri = await self._store.put(key, data, content_type)

        # O PDFParser lê de um path em disco; o temporário só precisa durar a
        # ingestão, já que a cópia durável é a do object store.
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(data)
            tmp.flush()
            return await self.ingest(
                LocalSource(path=Path(tmp.name)),
                collection_id,
                metadata={"source": uri, "title": Path(filename).stem},
            )

    async def search(
        self, query: str, collection_id: int, top_k: int = 5
    ) -> list[RetrievedDocument]:
        return await self._retriever.asearch(query, collection_id, top_k)

    async def astream_ask(
        self, query: str, collection_id: int, top_k: int = 5
    ) -> AskResult:
        chunks = await self.search(query, collection_id, top_k)
        return AskResult(
            sources=build_sources(chunks),
            stream=self._stream_answer(query, chunks),
        )

    async def _stream_answer(
        self, query: str, chunks: list[RetrievedDocument]
    ) -> AsyncIterator[str]:
        if not chunks:
            logger.warning(f"No relevant chunks found for query: {query}")
            yield "Desculpe, não encontrei informações relevantes para sua pergunta."
            return

        context = "\n\n".join(
            f"[{idx + 1}] {chunk.document.page_content} (fonte: {chunk.document.metadata.get('source', 'desconhecida')})"
            for idx, chunk in enumerate(chunks)
        )

        persona = render_prompt("persona", project_name=default_settings.PROJECT_NAME)
        task = render_prompt("rag_answer", context=context, query=query)
        prompt = f"{persona}\n\n{task}"
        try:
            async for chunk in self._llm.astream(prompt):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error occurred while invoking LLM: {e}")
            yield "Desculpe, ocorreu um erro ao processar sua pergunta."
