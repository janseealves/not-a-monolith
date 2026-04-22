import logging
from re import search

from langchain_text_splitters import RecursiveCharacterTextSplitter

from modules.rag.ingestion.base import BaseChunker, Chunk, Document

logger = logging.getLogger(__name__)


class RecursiveChunker(BaseChunker):
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, document: Document) -> list[Chunk]:
        raw_chunks = self._splitter.split_text(document.content)
        logger.debug("Split document into chunks: %d", len(raw_chunks))

        return self._treat_chunks(raw_chunks, source=document.metadata["source"])

    def _treat_chunks(self, chunks: list[str], source: dict) -> list[Chunk]:
        treated_chunks = []

        for idx, chunk in enumerate(chunks):
            if treated_chunks and not search(r"[.!]$", treated_chunks[-1].content):
                treated_chunks[-1].content += " " + chunk
            else:
                treated_chunks.append(
                    Chunk(source=source, number=(idx + 1, len(chunks)), content=chunk)
                )

        logger.debug("Treated chunks: %d", len(treated_chunks))
        return treated_chunks
