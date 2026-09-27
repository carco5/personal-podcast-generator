import logging

from alembic import context
from sqlalchemy import Connection, create_engine, pool

from app.config import get_settings
from app.models import Base

logging.basicConfig(format="%(levelname)s [%(name)s] %(message)s")
logging.getLogger("alembic").setLevel(logging.INFO)

target_metadata = Base.metadata


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
# Tests pass their own connection (Alembic cookbook: sharing a connection).
elif (connection := context.config.attributes.get("connection")) is not None:
    run_migrations(connection)
else:
    engine = create_engine(get_settings().database_url.get_secret_value(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        run_migrations(connection)
