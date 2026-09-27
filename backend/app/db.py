from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_settings

engine = create_engine(get_settings().database_url.get_secret_value(), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Yield one database session per request."""
    with Session(engine) as session:
        yield session
