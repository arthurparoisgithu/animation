"""Ce qui relie le generateur a la base.

Deux responsabilites, et rien d'autre : ne pas regenerer ce qu'on possede
deja, et n'ecrire en base que ce qui a passe les deux niveaux de validation.
"""

from sqlalchemy.orm import Session

from app.catalogue import gabarit_du_format
from app.generateur import GenerationEchouee, generer
from app.modeles import FormatJeu, Jeu
from app.requetes import enregistrer_rejets, jeu_existant
from app.schemas import Primitive, Public


class FormatInconnu(LookupError):
    pass


def generer_et_enregistrer(
    session: Session,
    *,
    format_code: str,
    theme: str,
    public: Public,
    nb_items: int | None = None,
    reutiliser: bool = True,
    avec_juge: bool = True,
) -> tuple[Jeu, bool]:
    """Retourne le jeu et un booleen disant s'il a ete resservi depuis la base.

    Les rejets sont enregistres meme quand la generation echoue : ce sont
    eux qui alimentent la metrique, et un echec est precisement le cas ou
    l'information vaut le plus.
    """
    format_jeu = session.get(FormatJeu, format_code)
    if format_jeu is None:
        raise FormatInconnu(format_code)

    theme = theme.strip()

    # Levier de cout : meme format, meme theme, meme public deja en base.
    if reutiliser:
        deja_la = jeu_existant(
            session, format_code=format_code, theme=theme, public=public
        )
        if deja_la is not None:
            return deja_la, True

    primitive = Primitive(format_jeu.primitive)
    gabarit = format_jeu.gabarit_prompt or gabarit_du_format(format_jeu.code, primitive)

    try:
        resultat = generer(
            primitive=primitive,
            gabarit=gabarit,
            nom_format=format_jeu.nom,
            theme=theme,
            public=public.value,
            nb_items=nb_items or format_jeu.nb_items_defaut,
            avec_juge=avec_juge,
        )
    except GenerationEchouee as erreur:
        enregistrer_rejets(
            session,
            format_code=format_code,
            primitive=primitive,
            rejets=erreur.rejets,
        )
        session.commit()
        raise

    enregistrer_rejets(
        session, format_code=format_code, primitive=primitive, rejets=resultat.rejets
    )

    jeu = Jeu(
        format_code=format_code,
        theme=theme,
        public=public,
        contenu=[item.model_dump() for item in resultat.items],
    )
    session.add(jeu)
    session.commit()
    session.refresh(jeu)
    return jeu, False
