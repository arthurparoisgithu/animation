"""Les requetes du projet, isolees des routes.

Le filtrage du catalogue est ecrit en SQL et non via l'ORM : la colonne
publics est un tableau Postgres, et l'operateur de contenance @> exprime
exactement ce qu'on cherche (« ce format s'adresse-t-il a ce public ? »)
en une clause, la ou l'ORM demanderait un detour.
"""

import uuid

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modeles import FormatJeu, Jeu, Rejet
from app.schemas import Materiel, Moment, Public

_SQL_FORMATS = """
SELECT code, nom, primitive, publics, moment, materiel,
       regle_animateur, nb_items_defaut
FROM format_jeu
-- Deux raisons a ces CAST. Sans type explicite, Postgres ne peut pas
-- deduire celui du parametre a partir du seul « IS NULL ». Et la syntaxe
-- courte « :public::text » est illisible pour SQLAlchemy, qui y voit un
-- nom de parametre et non un cast : CAST(... AS ...) leve l'ambiguite.
WHERE (CAST(:public AS text)   IS NULL OR publics @> ARRAY[CAST(:public AS text)])
  AND (CAST(:moment AS text)   IS NULL OR CAST(moment AS text)   = CAST(:moment AS text))
  AND (CAST(:materiel AS text) IS NULL OR CAST(materiel AS text) = CAST(:materiel AS text))
ORDER BY nom
"""


def lister_formats(
    session: Session,
    *,
    public: Public | None = None,
    moment: Moment | None = None,
    materiel: Materiel | None = None,
) -> list[dict]:
    """Le catalogue, filtre par public, moment et materiel."""
    lignes = session.execute(
        text(_SQL_FORMATS),
        {
            "public": public.value if public else None,
            "moment": moment.value if moment else None,
            "materiel": materiel.value if materiel else None,
        },
    ).mappings()
    return [dict(ligne) for ligne in lignes]


def obtenir_format(session: Session, code: str) -> FormatJeu | None:
    return session.get(FormatJeu, code)


def jeu_existant(
    session: Session, *, format_code: str, theme: str, public: Public
) -> Jeu | None:
    """Meme format, meme theme, meme public deja en base : on ressert.

    Levier de cout du cahier des charges : regenerer ce qu'on possede deja
    revient a payer deux fois la meme chose. La comparaison du theme est
    insensible a la casse et aux espaces de bordure.
    """
    requete = (
        select(Jeu)
        .where(
            Jeu.format_code == format_code,
            func.lower(func.trim(Jeu.theme)) == theme.strip().lower(),
            Jeu.public == public,
        )
        .order_by(Jeu.cree_le.desc())
        .limit(1)
    )
    return session.execute(requete).scalars().first()


def lister_jeux(session: Session, *, favoris_seulement: bool = False, limite: int = 50) -> list[Jeu]:
    requete = select(Jeu).order_by(Jeu.cree_le.desc()).limit(limite)
    if favoris_seulement:
        requete = requete.where(Jeu.favori.is_(True))
    return list(session.execute(requete).scalars())


def obtenir_jeu(session: Session, identifiant: uuid.UUID) -> Jeu | None:
    return session.get(Jeu, identifiant)


_SQL_TAUX_REJET = """
SELECT f.code,
       f.nom,
       f.primitive,
       COALESCE(r.deterministe, 0) AS rejets_deterministe,
       COALESCE(r.juge, 0)         AS rejets_juge,
       COALESCE(j.items_retenus, 0) AS items_retenus
FROM format_jeu f
LEFT JOIN (
    SELECT format_code,
           COUNT(*) FILTER (WHERE niveau = 'deterministe') AS deterministe,
           COUNT(*) FILTER (WHERE niveau = 'juge')         AS juge
    FROM rejet
    GROUP BY format_code
) r ON r.format_code = f.code
LEFT JOIN (
    SELECT format_code, SUM(jsonb_array_length(contenu)) AS items_retenus
    FROM jeu
    GROUP BY format_code
) j ON j.format_code = f.code
ORDER BY f.nom
"""


def taux_de_rejet(session: Session) -> list[dict]:
    """Rejets et items retenus par format, avec le taux calcule.

    C'est la metrique qui prouve que la validation sert a quelque chose, et
    celle qui declenche l'escalade vers Sonnet au-dela de 20 pour cent.
    """
    resultats = []
    for ligne in session.execute(text(_SQL_TAUX_REJET)).mappings():
        donnees = dict(ligne)
        rejets = donnees["rejets_deterministe"] + donnees["rejets_juge"]
        produits = rejets + donnees["items_retenus"]
        donnees["rejets_total"] = rejets
        donnees["items_produits"] = produits
        donnees["taux"] = rejets / produits if produits else 0.0
        # Seuil d'escalade du cahier des charges.
        donnees["escalade_conseillee"] = produits > 0 and donnees["taux"] > 0.20
        resultats.append(donnees)
    return resultats


def enregistrer_rejets(session: Session, *, format_code: str, primitive, rejets) -> None:
    """Chaque rejet est enregistre avec son motif et son niveau."""
    session.add_all(
        Rejet(
            format_code=format_code,
            primitive=primitive,
            motif=rejet.motif[:500],
            niveau=rejet.niveau,
        )
        for rejet in rejets
    )
