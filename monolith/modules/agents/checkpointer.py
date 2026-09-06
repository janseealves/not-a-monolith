import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from monolith.shared.config import Settings
from monolith.shared.config import settings as default_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def build_agent_checkpointer(
    settings: Settings | None = None,
) -> AsyncIterator[BaseCheckpointSaver]:
    """Context manager com o checkpointer certo conforme AGENT_CHECKPOINTER.

    É async context manager porque o saver Postgres detém uma conexão que precisa
    ser aberta/fechada junto do ciclo de vida da app (usar no lifespan).
    O saver Postgres cria/mantém suas próprias tabelas (fora do Alembic) via setup().
    """
    settings = settings or default_settings

    if settings.AGENT_CHECKPOINTER == "postgres":
        logger.info("Agent checkpointer: Postgres")
        async with AsyncPostgresSaver.from_conn_string(
            settings.get_checkpointer_url
        ) as checkpointer:
            await checkpointer.setup()
            yield checkpointer
    else:
        logger.info("Agent checkpointer: in-memory (não persiste no restart)")
        yield InMemorySaver()
