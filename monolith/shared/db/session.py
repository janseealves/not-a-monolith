from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from monolith.shared.config import settings

engine = create_async_engine(settings.get_database_url, echo=True)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session
