"""Ajoute l'emoji du format au catalogue.

C'est de la donnee de catalogue au meme titre que le nom : quelque chose
qu'un humain saisit et que l'animateur voit a l'ecran. Elle a donc sa place
en base, et ajouter un format continue de se faire en une ligne.

La colonne arrive avec une valeur par defaut pour que la migration passe
sur une base deja peuplee ; le seed remplace ensuite chaque valeur.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Une valeur neutre plutot que NULL : la colonne est affichee a chaque
# carte, et un format sans emoji casserait la grille au lieu de degrader.
DEFAUT = "🎲"


def upgrade() -> None:
    op.add_column(
        "format_jeu",
        sa.Column("emoji", sa.Text(), nullable=False, server_default=DEFAUT),
    )


def downgrade() -> None:
    op.drop_column("format_jeu", "emoji")
