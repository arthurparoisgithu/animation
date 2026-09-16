"""Connexion a la base et fabrique de sessions SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import reglages

# pool_pre_ping : SQLAlchemy teste la connexion avant de la reutiliser.
# Sans ca, une connexion coupee par Postgres pendant une periode d'inactivite
# fait echouer la premiere requete suivante.
moteur = create_engine(reglages().database_url, pool_pre_ping=True, future=True)

FabriqueSession = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)


def obtenir_session() -> Iterator[Session]:
    """Dependance FastAPI : une session par requete, fermee a la fin."""
    session = FabriqueSession()
    try:
        yield session
    finally:
        session.close()
