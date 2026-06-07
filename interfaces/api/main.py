# interfaces/api/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# CORS: libera o frontend local (mono-ui) a consumir a API de outra origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(meta_router)
app.include_router(rag_router, prefix="/v1")
