import logging
import re

from langchain_community.document_loaders import WebBaseLoader

from modules.rag.ingestion.base import BaseParser, Document

logger = logging.getLogger(__name__)


class WebParser(BaseParser):
    def load(self, source: str, options: dict | None = None) -> Document:
        loader = WebBaseLoader(source, **(options or {}))
        logger.info("Loading document from %s", source)
        doc = loader.load()

        if not doc:
            logger.warning("No content found at %s", source)
            raise ValueError(f"No content found at {source}")

        logger.debug("Document loaded with metadata: %s", doc[0].metadata)
        return Document(
            metadata=doc[0].metadata, content=self._clean(doc[0].page_content)
        )

    def _clean(self, raw_content: str) -> str:
        # Remove multiple spaces and newlines
        content = re.sub(r" {2,}", " ", raw_content)

        # Replace multiple newlines with a maximum of two
        content = re.sub(r"\n{3,}", "\n\n", raw_content)

        return content.strip()
