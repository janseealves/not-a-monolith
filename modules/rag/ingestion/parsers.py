import logging
from dataclasses import dataclass

from langchain_community.document_loaders import WebBaseLoader

from modules.rag.ingestion.base import BaseParser

logger = logging.getLogger(__name__)


@dataclass
class Document:
    metadata: dict
    content: str


class WebParser(BaseParser):
    def load(self, source: str, options: dict | None = None) -> Document:
        loader = WebBaseLoader(source, **(options or {}))
        logger.info("Loading document from %s", source)
        doc = loader.load()

        if not doc:
            logger.warning("No content found at %s", source)
            raise ValueError(f"No content found at {source}")

        logger.debug("Document loaded with metadata: %s", doc[0].metadata)
        return Document(metadata=doc[0].metadata, content=doc[0].page_content)
