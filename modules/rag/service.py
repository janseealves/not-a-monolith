import logging
from collections.abc import AsyncIterator

from langchain.chat_models import BaseChatModel
from langchain_ollama import OllamaEmbeddings
from sqlalchemy.ext.asyncio import async_sessionmaker

from modules.rag.ingestion.base import BaseChunker, BaseIndexer, BaseParser, Source
from modules.rag.ingestion.chunker import RecursiveChunker
from modules.rag.ingestion.indexer import PostgresIndexer
from modules.rag.ingestion.parser import WebParser
from modules.rag.retrieval.base import BaseRetriever, RetrievedDocument
from modules.rag.retrieval.retriever import SemanticRetriever
from shared.config import Settings
from shared.config import settings as default_settings
from shared.db.session import SessionLocal
from shared.llm import build_chat_model

logger = logging.getLogger(__name__)


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
    ) -> AsyncIterator[str]:
        chunks = await self.search(query, collection_id, top_k)

        if not chunks:
            logger.warning(f"No relevant chunks found for query: {query}")
            yield "Desculpe, não encontrei informações relevantes para sua pergunta."
            return

        # TODO: extrair toda a lógica abaixo para um package 'generation' e usar um template engine para montar o prompt.
        context = "\n\n".join(
            f"[{idx + 1}] {chunk.document.page_content} (fonte: {chunk.document.metadata.get('source', 'desconhecida')})"
            for idx, chunk in enumerate(chunks)
        )

        prompt = f"""Você é um assistente de perguntas e respostas. Use SOMENTE as informações do contexto abaixo para responder à pergunta. Cite as fontes das informações usadas, indicando o número do chunk correspondente. Se o contexto não contiver informações suficientes para responder à pergunta, diga que não sabe. Não invente respostas.
        Contexto: {context}

        ---

        Pergunta: {query}

        Resposta:
        """
        try:
            async for chunk in self._llm.astream(prompt):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error occurred while invoking LLM: {e}")
            yield "Desculpe, ocorreu um erro ao processar sua pergunta."
