from langchain_core.vectorstores import VectorStore

from modules.rag.ingestion.base import BaseChunker, BaseIndexer, BaseParser
from modules.rag.ingestion.chunker import RecursiveChunker
from modules.rag.ingestion.indexer import VectorStoreIndexer
from modules.rag.ingestion.parser import WebParser
from modules.rag.retrieval.base import BaseRetriever, RetrievedDocument
from modules.rag.retrieval.retriever import SemanticRetriever


class RAGService:
    def __init__(self, parser: BaseParser, chunker: BaseChunker,
                 indexer: BaseIndexer, retriever: BaseRetriever) -> None:
        self._parser = parser
        self._chunker = chunker
        self._indexer = indexer
        self._retriever = retriever

    @classmethod
    def with_defaults(cls, vector_store: VectorStore) -> "RAGService":
        # único lugar do módulo que conhece as classes concretas
        return cls(
            parser=WebParser(),
            chunker=RecursiveChunker(),
            indexer=VectorStoreIndexer(vector_store),
            retriever=SemanticRetriever(vector_store),
        )

    def ingest(self, source: str) -> None:
        document = self._parser.load(source)
        chunks = self._chunker.split(document)
        self._indexer.index(chunks)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        return self._retriever.retrieve(query, top_k)
