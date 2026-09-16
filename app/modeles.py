"""Les trois tables du projet, en SQLAlchemy 2.0.

format_jeu est le catalogue, saisi a la main et jamais genere.
jeu contient les instances generees.
rejet est la metrique de validation : c'est elle qui prouve que les deux
niveaux servent a quelque chose.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as EnumSQL,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.schemas import Materiel, Moment, NiveauRejet, Primitive, Public


class Base(DeclarativeBase):
    pass


def _enum(enumeration, nom: str) -> EnumSQL:
    """Type ENUM Postgres construit sur une enumeration Python.

    values_callable force SQLAlchemy a stocker la valeur du membre
    ("quiz_express") et non son nom Python, qui se trouve etre identique
    ici mais n'a aucune raison de l'etre toujours.
    """
    return EnumSQL(
        enumeration,
        name=nom,
        values_callable=lambda membres: [membre.value for membre in membres],
    )


class FormatJeu(Base):
    """Le catalogue. Ajouter un format se fait ici, sans ligne de Python."""

    __tablename__ = "format_jeu"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    nom: Mapped[str] = mapped_column(Text, nullable=False)
    primitive: Mapped[Primitive] = mapped_column(_enum(Primitive, "primitive"), nullable=False)

    # Tableau Postgres et non table de liaison : ca permet d'ecrire le
    # filtrage par public avec l'operateur de contenance @> plutot que
    # de passer par une jointure.
    publics: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)

    moment: Mapped[Moment] = mapped_column(_enum(Moment, "moment"), nullable=False)
    materiel: Mapped[Materiel] = mapped_column(_enum(Materiel, "materiel"), nullable=False)
    regle_animateur: Mapped[str] = mapped_column(Text, nullable=False)
    gabarit_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    nb_items_defaut: Mapped[int] = mapped_column(Integer, nullable=False)

    jeux: Mapped[list["Jeu"]] = relationship(back_populates="format")


class Jeu(Base):
    """Une instance generee : un format, un theme, un public, des items."""

    __tablename__ = "jeu"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    format_code: Mapped[str] = mapped_column(
        Text, ForeignKey("format_jeu.code", ondelete="RESTRICT"), nullable=False, index=True
    )
    theme: Mapped[str] = mapped_column(Text, nullable=False)
    public: Mapped[Public] = mapped_column(_enum(Public, "public"), nullable=False)

    # jsonb et non json : Postgres le stocke sous forme decomposee, ce qui
    # permet de l'indexer et de l'interroger. La structure du contenu depend
    # de la primitive du format.
    contenu: Mapped[list] = mapped_column(JSONB, nullable=False)

    favori: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    format: Mapped[FormatJeu] = relationship(back_populates="jeux")


class Rejet(Base):
    """Un item refuse. Le taux de rejet par format est une metrique affichee."""

    __tablename__ = "rejet"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    format_code: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    primitive: Mapped[Primitive] = mapped_column(_enum(Primitive, "primitive"), nullable=False)
    motif: Mapped[str] = mapped_column(Text, nullable=False)
    niveau: Mapped[NiveauRejet] = mapped_column(_enum(NiveauRejet, "niveau_rejet"), nullable=False)
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
