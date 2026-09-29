"""Prepare the database before the API and the worker start: migrations, then the demo data."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import engine
from app.demo import seed_demo_listener
from app.synthetic import seed_if_missing

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

logger = logging.getLogger(__name__)


def alembic_config() -> Config:
    """Alembic configuration from backend/pyproject.toml."""
    return Config(toml_file=PYPROJECT)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    command.upgrade(alembic_config(), "head")
    with Session(engine) as session:
        user = seed_demo_listener(session, get_settings().data_dir)
        session.commit()
        logger.info("Demo listener ready (id %s)", user.id)
        created = seed_if_missing(session, datetime.now(UTC))
        session.commit()
        logger.info("Simulated listeners: %s created", created)


if __name__ == "__main__":
    main()
