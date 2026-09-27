"""Prepare the database before the API and the worker start: migrations, then the demo user."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.db import engine
from app.demo import ensure_demo_user

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

logger = logging.getLogger(__name__)


def alembic_config() -> Config:
    """Alembic configuration from backend/pyproject.toml."""
    return Config(toml_file=PYPROJECT)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    command.upgrade(alembic_config(), "head")
    with Session(engine) as session:
        user = ensure_demo_user(session)
        session.commit()
        logger.info("Demo user ready (id %s)", user.id)


if __name__ == "__main__":
    main()
