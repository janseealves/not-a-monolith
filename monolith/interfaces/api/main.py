# monolith/interfaces/api/main.py
import logging
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from monolith.agents.checkpointer import build_agent_checkpointer
from monolith.agents.service import AgentService
from monolith.interfaces.api.routes.agent import router as agent_router
from monolith.interfaces.api.routes.collections import router as collections_router
from monolith.interfaces.api.routes.meta import router as meta_router
from monolith.interfaces.api.routes.rag import router as rag_router
from monolith.rag.service import RAGService
from monolith.shared.config import settings, setup_logger

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


app.include_router(meta_router)
app.include_router(collections_router, prefix="/v1")
app.include_router(rag_router, prefix="/v1")
app.include_router(agent_router, prefix="/v1")
