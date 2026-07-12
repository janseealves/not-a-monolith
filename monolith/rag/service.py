import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from langchain.chat_models import BaseChatModel
from langchain_ollama import OllamaEmbeddings
from sqlalchemy.ext.asyncio import async_sessionmaker

from monolith.rag.ingestion.base import BaseChunker, BaseIndexer, BaseParser, Source
from monolith.rag.ingestion.chunker import RecursiveChunker
from monolith.rag.ingestion.indexer import PostgresIndexer
from monolith.rag.ingestion.parser import WebParser
from monolith.rag.retrieval.base import BaseRetriever, RetrievedDocument
from monolith.rag.retrieval.retriever import SemanticRetriever
from monolith.shared.config import Settings
from monolith.shared.config import settings as default_settings
from monolith.shared.db.session import SessionLocal
from monolith.shared.llm import build_chat_model
from monolith.shared.prompts import render_prompt

logger = logging.getLogger(__name__)


@dataclass
class SourceInfo:
    source: str
    chunk_ids: list[str]


@dataclass
class AskResult:
    sources: list[SourceInfo]
    stream: AsyncIterator[str]


def build_sources(chunks: list[RetrievedDocument]) -> list[SourceInfo]:
    # agrupa por source: vários chunks costumam vir do mesmo documento.
    chunk_ids_by_source: dict[str, list[str]] = {}
    for chunk in chunks:
        source = chunk.document.metadata.get("source", "desconhecida")
        chunk_ids_by_source.setdefault(source, []).append(
            chunk.document.metadata["chunk_id"]
        )
    return [
        SourceInfo(source=source, chunk_ids=chunk_ids)
        for source, chunk_ids in chunk_ids_by_source.items()
    ]


class RAGService:
    def __init__(
        self,
        parser: BaseParser,
        chunker: BaseChunker,
        indexer: BaseIndexer,
        retriever: BaseRetriever,
        llm: BaseChatModel,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._indexer = indexer
        self._retriever = retriever
        self._llm = llm

    @classmethod
    def with_defaults(
        cls,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
        session_factory: async_sessionmaker | None = None,
    ) -> "RAGService":
        settings = settings or default_settings
        session_factory = session_factory or SessionLocal
        embeddings = OllamaEmbeddings(
            model=settings.EMBEDDINGS_MODEL,
            base_url=settings.EMBEDDINGS_BASE_URL,
        )

        # único lugar do módulo que conhece as classes concretas
        return cls(
            parser=WebParser(),
            chunker=RecursiveChunker(),
            indexer=PostgresIndexer(session_factory, embeddings),
            retriever=SemanticRetriever(session_factory, embeddings),
            llm=build_chat_model(settings),
        )

    async def ingest(self, source: Source, collection_id: int) -> None:
        document = await self._parser.load(source)
        chunks = self._chunker.split(document)
        await self._indexer.index(document, chunks, collection_id)

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
