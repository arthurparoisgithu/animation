"""Schema initial : format_jeu, jeu, rejet.

Migration ecrite a la main plutot qu'autogeneree : elle est courte, et
l'ordre de creation des types ENUM par rapport aux tables merite d'etre
explicite.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

PRIMITIVE = postgresql.ENUM(
    "question", "enigme", "vrai_faux", name="primitive", create_type=False
)
PUBLIC = postgresql.ENUM(
    "mini", "junior", "ado", "adulte", "general", name="public", create_type=False
)
MOMENT = postgresql.ENUM(
    "cafe_apero", "veillee_enfants", "soiree_adultes", "grand_jeu",
    name="moment", create_type=False,
)
MATERIEL = postgresql.ENUM(
    "aucun", "videoprojecteur", "sono", "accessoires", name="materiel", create_type=False
)
NIVEAU_REJET = postgresql.ENUM(
    "deterministe", "juge", name="niveau_rejet", create_type=False
)

TYPES = (PRIMITIVE, PUBLIC, MOMENT, MATERIEL, NIVEAU_REJET)


def upgrade() -> None:
    connexion = op.get_bind()
    for type_enum in TYPES:
        type_enum.create(connexion, checkfirst=True)

    op.create_table(
        "format_jeu",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("nom", sa.Text(), nullable=False),
        sa.Column("primitive", PRIMITIVE, nullable=False),
        # Tableau Postgres : permet le filtrage par l'operateur @>.
        sa.Column("publics", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("moment", MOMENT, nullable=False),
        sa.Column("materiel", MATERIEL, nullable=False),
        sa.Column("regle_animateur", sa.Text(), nullable=False),
        sa.Column("gabarit_prompt", sa.Text(), nullable=False),
        sa.Column("nb_items_defaut", sa.Integer(), nullable=False),
    )
    # Index GIN : c'est celui qui rend l'operateur de contenance efficace.
    op.create_index(
        "ix_format_jeu_publics",
        "format_jeu",
        ["publics"],
        postgresql_using="gin",
    )

    op.create_table(
        "jeu",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "format_code",
            sa.Text(),
            sa.ForeignKey("format_jeu.code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("theme", sa.Text(), nullable=False),
        sa.Column("public", PUBLIC, nullable=False),
        sa.Column("contenu", postgresql.JSONB(), nullable=False),
        sa.Column("favori", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "cree_le",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_jeu_format_code", "jeu", ["format_code"])

    op.create_table(
        "rejet",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("format_code", sa.Text(), nullable=False),
        sa.Column("primitive", PRIMITIVE, nullable=False),
        sa.Column("motif", sa.Text(), nullable=False),
        sa.Column("niveau", NIVEAU_REJET, nullable=False),
        sa.Column(
            "cree_le",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_rejet_format_code", "rejet", ["format_code"])


def downgrade() -> None:
    op.drop_table("rejet")
    op.drop_table("jeu")
    op.drop_index("ix_format_jeu_publics", table_name="format_jeu")
    op.drop_table("format_jeu")

    connexion = op.get_bind()
    for type_enum in reversed(TYPES):
        type_enum.drop(connexion, checkfirst=True)
