# interfaces/api/main.py
import logging
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interfaces.api.routes.agent import router as agent_router
from interfaces.api.routes.collections import router as collections_router
from interfaces.api.routes.meta import router as meta_router
from interfaces.api.routes.rag import router as rag_router
from modules.agents.checkpointer import build_agent_checkpointer
from modules.agents.service import AgentService
from modules.rag.service import RAGService
from shared.config import settings, setup_logger

setup_logger(level=settings.LOGGING_LEVEL)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───
    logger.info("Initializing RAG service...")
    app.state.rag_service = RAGService.with_defaults()
    logger.info("RAG service ready.")

    # O checkpointer do agente pode deter uma conexão (Postgres); o ExitStack
    # garante que ela seja fechada no shutdown.
    async with AsyncExitStack() as stack:
        logger.info("Initializing Agent service...")
        checkpointer = await stack.enter_async_context(build_agent_checkpointer())
        app.state.agent_service = AgentService.with_defaults(
            rag=app.state.rag_service, checkpointer=checkpointer
        )
        logger.info("Agent service ready.")

        yield  # ◀── aqui a API roda

        # ─── Shutdown ───
        logger.info("Cleaning up...")
        # o ExitStack fecha o checkpointer aqui


app = FastAPI(title="not-a-monolith", lifespan=lifespan)

# CORS: libera o frontend local (mono-ui) a consumir a API de outra origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(meta_router)
app.include_router(collections_router, prefix="/v1")
app.include_router(rag_router, prefix="/v1")
app.include_router(agent_router, prefix="/v1")
