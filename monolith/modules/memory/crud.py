from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from monolith.modules.memory.base import MemoryWrite, Turn
from monolith.modules.memory.models import LedgerTurn, LedgerWrite
from monolith.shared.db.session import SessionLocal


async def record_turn(
    turn: Turn,
    engine: str,
    writes: list[MemoryWrite],
    error: str | None = None,
    session_factory: async_sessionmaker = SessionLocal,
) -> LedgerTurn:
    now = datetime.now(UTC)
    record = LedgerTurn(
        external_id=turn.id,
        engine=engine,
        user_id=turn.user_id,
        thread_id=turn.thread_id,
        collection_id=turn.collection_id,
        user_message=turn.user_message,
        assistant_message=turn.assistant_message,
        sources=turn.sources,
        recalled_memory_ids=[m.id for m in turn.recalled],
        error=error,
        created_at=now,
        writes=[LedgerWrite(**asdict(w), created_at=now) for w in writes],
    )
    async with session_factory() as session, session.begin():
        session.add(record)
    return record


async def get_writes_by_memory_ids(
    memory_ids: list[str],
    session_factory: async_sessionmaker = SessionLocal,
) -> list[LedgerWrite]:
    """Escritas do ledger para esses ids do motor, já com o turno de origem."""
    async with session_factory() as session:
        result = await session.scalars(
            select(LedgerWrite)
            .where(LedgerWrite.memory_id.in_(memory_ids))
            .options(selectinload(LedgerWrite.turn))
            .order_by(LedgerWrite.created_at)
        )
        return list(result.all())
