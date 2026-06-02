import logging

from langchain.chat_models import BaseChatModel, init_chat_model
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from modules.rag.ingestion.base import BaseChunker, BaseIndexer, BaseParser
from modules.rag.ingestion.chunker import RecursiveChunker
from modules.rag.ingestion.indexer import VectorStoreIndexer
from modules.rag.ingestion.parser import WebParser
from modules.rag.retrieval.base import BaseRetriever, RetrievedDocument
from modules.rag.retrieval.retriever import SemanticRetriever
from shared.config import Settings
from shared.config import settings as default_settings

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
    def with_defaults(cls, settings: Settings | None = None) -> "RAGService":
        settings = settings or default_settings
        embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDINGS_MODEL,
            api_key=settings.LLM_API_KEY.get_secret_value(),
        )
        vector_store = InMemoryVectorStore(embeddings)
        llm = init_chat_model(
            f"openai:{settings.LLM_MODEL}",
            api_key=settings.LLM_API_KEY.get_secret_value(),
        )

        # único lugar do módulo que conhece as classes concretas
        return cls(
            parser=WebParser(),
            chunker=RecursiveChunker(),
            indexer=VectorStoreIndexer(vector_store),
            retriever=SemanticRetriever(vector_store),
            llm=llm,
        )

    def ingest(self, source: str) -> None:
        document = self._parser.load(source)
        chunks = self._chunker.split(document)
        self._indexer.index(chunks)

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        return self._retriever.search(query, top_k)

    def ask(self, query: str, top_k: int = 5) -> str:
        chunks = self.search(query, top_k)

        if not chunks:
            logger.warning(f"No relevant chunks found for query: {query}")
            return "Desculpe, não encontrei informações relevantes para sua pergunta."

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
            response = self._llm.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error occurred while invoking LLM: {e}")
            return "Desculpe, ocorreu um erro ao processar sua pergunta."
