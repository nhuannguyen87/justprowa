from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import settings

if settings.DATABASE_URL.startswith("sqlite:///"):
    from pathlib import Path
    Path(settings.DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)
    SQLModel.metadata.create_all(engine)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
