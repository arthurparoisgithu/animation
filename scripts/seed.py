"""Insere le catalogue de depart en base.

Relançable sans risque : un format deja present est mis a jour, pas
duplique. C'est ce qui permet de corriger un gabarit de prompt et de
rejouer le seed sans repartir d'une base vide.

    python -m scripts.seed
"""

from sqlalchemy.dialects.postgresql import insert

from app.catalogue import CATALOGUE, gabarit_du_format
from app.db import FabriqueSession
from app.modeles import FormatJeu


def lignes() -> list[dict]:
    return [
        {
            "code": format_jeu["code"],
            "nom": format_jeu["nom"],
            "emoji": format_jeu["emoji"],
            "primitive": format_jeu["primitive"].value,
            "publics": format_jeu["publics"],
            "moment": format_jeu["moment"].value,
            "materiel": format_jeu["materiel"].value,
            "regle_animateur": format_jeu["regle_animateur"],
            "gabarit_prompt": gabarit_du_format(
                format_jeu["code"], format_jeu["primitive"]
            ),
            "nb_items_defaut": format_jeu["nb_items_defaut"],
        }
        for format_jeu in CATALOGUE
    ]


def main() -> int:
    donnees = lignes()

    with FabriqueSession() as session:
        # ON CONFLICT DO UPDATE : le seed est idempotent.
        requete = insert(FormatJeu).values(donnees)
        requete = requete.on_conflict_do_update(
            index_elements=["code"],
            set_={
                colonne: requete.excluded[colonne]
                for colonne in (
                    "nom", "emoji", "primitive", "publics", "moment", "materiel",
                    "regle_animateur", "gabarit_prompt", "nb_items_defaut",
                )
            },
        )
        session.execute(requete)
        session.commit()

    print(f"{len(donnees)} formats inseres ou mis a jour.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
