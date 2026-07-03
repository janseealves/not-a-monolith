import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from modules.rag.models import Collection
from shared.db.session import SessionLocal


class CollectionService:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    @classmethod
    def with_defaults(
        cls, session_factory: async_sessionmaker | None = None
    ) -> "CollectionService":
        return cls(session_factory or SessionLocal)

    async def create(self, name: str, description: str | None = None) -> Collection:
        collection = Collection(
            name=name, description=description, created_at=datetime.now(UTC)
        )
        async with self._session_factory() as session, session.begin():
            session.add(collection)
            await session.flush()  # garante id/external_id preenchidos
        return collection

    async def list(self) -> list[Collection]:
        async with self._session_factory() as session:
            result = await session.scalars(select(Collection))
            return list(result.all())

    async def get_by_external_id(self, external_id: uuid.UUID) -> Collection | None:
        async with self._session_factory() as session:
            return await session.scalar(
                select(Collection).where(Collection.external_id == external_id)
            )

    # TODO: update() e delete(). No delete, decidir o que fazer com documentos que
    # ficam sem nenhuma collection (apagar em cascata ou manter órfãos p/ reaproveitar).
