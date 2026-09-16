"""Configuration Alembic.

L'URL de connexion vient de DATABASE_URL (via app.config), jamais du
fichier alembic.ini : une chaine de connexion n'a pas a etre commitee.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import reglages
from app.modeles import Base

config = context.config

# L'URL n'est deliberement pas ecrite dans la config Alembic : celle-ci
# passe par configparser, qui interprete « % » comme une interpolation.
# Un mot de passe genere contenant un « % » — ce que font les hebergeurs —
# ferait echouer la migration avant meme la connexion. On construit donc
# le moteur directement.
def url_base() -> str:
    return reglages().database_url


if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Permet a `alembic revision --autogenerate` de comparer les modeles au schema.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=url_base(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(url_base(), poolclass=pool.NullPool)
    with connectable.connect() as connexion:
        context.configure(connection=connexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
