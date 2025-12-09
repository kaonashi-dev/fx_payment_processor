from sqlmodel import create_engine, SQLModel
from src.config.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=5,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    from sqlmodel import Session

    with Session(engine) as session:
        yield session
