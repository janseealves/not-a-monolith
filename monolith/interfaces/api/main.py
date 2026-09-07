# monolith/interfaces/api/main.py
import logging
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from monolith.interfaces.api.routes.agent import router as agent_router
from monolith.interfaces.api.routes.collections import router as collections_router
from monolith.interfaces.api.routes.meta import router as meta_router
from monolith.interfaces.api.routes.rag import documents_router
from monolith.interfaces.api.routes.rag import router as rag_router
from monolith.modules.agents.chat.service import ChatService
from monolith.modules.agents.checkpointer import build_agent_checkpointer
from monolith.modules.rag.service import RAGService
from monolith.shared.config import settings, setup_logger
from monolith.shared.storage import ObjectStore

setup_logger(level=settings.LOGGING_LEVEL)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───
    logger.info("Initializing RAG service...")
    # Um único store: o serviço grava por ele e as rotas assinam por ele.
    app.state.object_store = ObjectStore(settings)
    app.state.rag_service = RAGService.with_defaults(store=app.state.object_store)
    logger.info("RAG service ready.")

    # O checkpointer do agente pode deter uma conexão (Postgres); o ExitStack
    # garante que ela seja fechada no shutdown.
    async with AsyncExitStack() as stack:
        logger.info("Initializing Agent service...")
        checkpointer = await stack.enter_async_context(build_agent_checkpointer())
        app.state.chat_service = ChatService.with_defaults(
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
app.include_router(documents_router, prefix="/v1")
app.include_router(agent_router, prefix="/v1")
