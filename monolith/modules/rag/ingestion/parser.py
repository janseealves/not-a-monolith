import asyncio
import logging

import fitz  # PyMuPDF
import pymupdf4llm
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from langchain_core.documents import Document

from monolith.modules.rag.ingestion.base import (
    BaseParser,
    LocalSource,
    Source,
    WebSource,
)

logger = logging.getLogger(__name__)


class WebParser(BaseParser):
    async def load(self, source: Source, options: dict | None = None) -> Document:
        if not isinstance(source, WebSource):
            raise TypeError(
                f"WebParser aceita apenas WebSource, recebeu {type(source).__name__}"
            )

        opts = options or {}
        is_dynamic = bool(opts.get("js_code") or opts.get("wait_for"))

        browser_config = BrowserConfig(
            headless=True,
            text_mode=not is_dynamic,
            light_mode=not is_dynamic,
        )
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=opts.get("js_code"),
            wait_for=opts.get("wait_for"),
            page_timeout=opts.get("page_timeout", 30000),
        )

        logger.info("Loading %s (dynamic=%s)", source.url, is_dynamic)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(source.url, config=run_config)

        if not result.success:
            raise ValueError(f"Failed to load {source.url}: {result.error_message}")

        markdown = result.markdown
        content = (
            markdown.raw_markdown
            if hasattr(markdown, "raw_markdown")
            else str(markdown)
        )

        if not content or len(content.strip()) < 50:
            logger.warning("No meaningful content found at %s", source.url)
            raise ValueError(f"No content found at {source.url}")

        return Document(
            page_content=content.strip(),
            metadata={"source": result.url, "status_code": result.status_code},
        )


class PDFParser(BaseParser):
    async def load(self, source: Source) -> Document:
        if not isinstance(source, LocalSource):
            raise TypeError(
                f"PDFParser aceita apenas LocalSource, recebeu {type(source).__name__}"
            )

        path = source.path
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        # len(doc) lê só a árvore de páginas, sem parsear conteúdo.
        with fitz.open(path) as doc:
            page_count = len(doc)
            title = (doc.metadata or {}).get("title", "").strip()

        logger.info("Loading PDF %s (%d páginas)", path.name, page_count)

        loop = asyncio.get_running_loop()
        content: str = await loop.run_in_executor(
            None, pymupdf4llm.to_markdown, str(path)
        )
        content = content.strip()

        # Markdown vazio = PDF sem camada de texto. A checagem antiga varria
        # todas as páginas antes disso só para descobrir o que a própria
        # extração já responde.
        if not content:
            raise ValueError(
                f"PDF sem texto selecionável: {path}. OCR não é suportado."
            )

        if len(content) < 50:
            logger.warning("Conteúdo insuficiente extraído de %s", path)
            raise ValueError(f"Nenhum conteúdo extraído de: {path}")

        return Document(
            page_content=content,
            metadata={
                "source": str(path),
                # O título entra no embedding de cada chunk (ver _DOC_PROMPT do
                # indexer) e é o que a citação mostra ao usuário — o nome do
                # arquivo é bem melhor que o "none" que ficava aqui antes.
                "title": title or path.stem,
                "page_count": page_count,
                "file_size": path.stat().st_size,
            },
        )


class ParserRouter(BaseParser):
    """Escolhe o parser pelo tipo do Source.

    Existe porque o RAGService recebe um único BaseParser: sem o dispatch, o
    serviço ficaria preso ao parser web e o PDFParser seria inalcançável.
    """

    def __init__(self, parsers: dict[type, BaseParser]) -> None:
        self._parsers = parsers

    async def load(self, source: Source) -> Document:
        parser = self._parsers.get(type(source))
        if parser is None:
            raise TypeError(f"Nenhum parser registrado para {type(source).__name__}")
        return await parser.load(source)
