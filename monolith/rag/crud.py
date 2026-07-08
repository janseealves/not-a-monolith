import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from monolith.rag.models import Collection
from monolith.shared.db.session import SessionLocal


async def create_collection(
    name: str,
    description: str | None = None,
    session_factory: async_sessionmaker = SessionLocal,
) -> Collection:
    collection = Collection(
        name=name, description=description, created_at=datetime.now(UTC)
    )
    async with session_factory() as session, session.begin():
        session.add(collection)
        await session.flush()  # garante id/external_id preenchidos
    return collection


async def list_collections(
    session_factory: async_sessionmaker = SessionLocal,
) -> list[Collection]:
    async with session_factory() as session:
        result = await session.scalars(select(Collection))
        return list(result.all())


async def get_collection_by_external_id(
    external_id: uuid.UUID,
    session_factory: async_sessionmaker = SessionLocal,
) -> Collection | None:
    async with session_factory() as session:
        return await session.scalar(
            select(Collection).where(Collection.external_id == external_id)
        )


# TODO: update/delete de collection. No delete, decidir o que fazer com documentos que
# ficam sem nenhuma collection (apagar em cascata ou manter órfãos p/ reaproveitar).
