# interfaces/api/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from interfaces.api.routes.meta import router as meta_router
from interfaces.api.routes.rag import router as rag_router
from modules.rag.service import RAGService
from shared.config import setup_logger

setup_logger(level="INFO")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───
    logger.info("Initializing RAG service...")
    app.state.rag_service = RAGService.with_defaults()
    logger.info("RAG service ready.")

    yield  # ◀── aqui a API roda

    # ─── Shutdown ───
    logger.info("Cleaning up...")
    # fechar conexões, salvar estado, etc.


app = FastAPI(title="not-a-monolith", lifespan=lifespan)


app.include_router(meta_router)
app.include_router(rag_router, prefix="/v1")
