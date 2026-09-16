"""Configuration Alembic.

L'URL de connexion vient de DATABASE_URL (via app.config), jamais du
fichier alembic.ini : une chaine de connexion n'a pas a etre commitee.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import reglages
from app.modeles import Base

config = context.config
config.set_main_option("sqlalchemy.url", reglages().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Permet a `alembic revision --autogenerate` de comparer les modeles au schema.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connexion:
        context.configure(connection=connexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
