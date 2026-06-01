import logging
from re import search

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from modules.rag.ingestion.base import BaseChunker

logger = logging.getLogger(__name__)


class RecursiveChunker(BaseChunker):
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, document: Document) -> list[Document]:
        raw_chunks = self._splitter.split_text(document.page_content)
        logger.debug("Split document into chunks: %d", len(raw_chunks))

        return self._treat_chunks(raw_chunks, source=document.metadata["source"])

    def _treat_chunks(self, chunks: list[str], source: str) -> list[Document]:
        treated_chunks: list[Document] = []

        for idx, chunk in enumerate(chunks):
            if treated_chunks and not search(r"[.!]$", treated_chunks[-1].page_content):
                treated_chunks[-1].page_content += " " + chunk
            else:
                treated_chunks.append(
                    Document(
                        page_content=chunk,
                        metadata={"source": source, "number": (idx + 1, len(chunks))},
                    )
                )

        logger.debug("Treated chunks: %d", len(treated_chunks))
        return treated_chunks
