import logging

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from langchain_core.documents import Document

from modules.rag.ingestion.base import BaseParser

logger = logging.getLogger(__name__)


class WebParser(BaseParser):
    async def load(self, source: str, options: dict | None = None) -> Document:
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

        logger.info("Loading %s (dynamic=%s)", source, is_dynamic)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(source, config=run_config)

        if not result.success:
            raise ValueError(f"Failed to load {source}: {result.error_message}")

        markdown = result.markdown
        content = markdown.raw_markdown if hasattr(markdown, "raw_markdown") else str(markdown)

        if not content or len(content.strip()) < 50:
            logger.warning("No meaningful content found at %s", source)
            raise ValueError(f"No content found at {source}")

        return Document(
            page_content=content.strip(),
            metadata={"source": result.url, "status_code": result.status_code},
        )


# TODO: Adicionar PDF Parser — ver recomendação de PyMuPDF4LLM (langchain-pymupdf4llm).
# Para PDFs image-only (sem texto selecionável), detectar via page.get_text("blocks")
# e lançar erro explícito — OCR é escopo separado.
class PDFParser(BaseParser):
    async def load(self, source: str, options: dict | None = None) -> Document:
        raise NotImplementedError("PDFParser is not implemented yet")
