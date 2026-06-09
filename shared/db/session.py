from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.config import settings

database_url = settings.get_database_url

engine = create_engine(database_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
