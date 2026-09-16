"""Niveau 2 de validation : le juge.

Ne tranche que ce que le code ne peut pas trancher : exactitude factuelle et
adequation au public. Un seul appel pour tout le lot, en Haiku, verdict
binaire par item plus motif.
"""

import json

from app.config import reglages
from app.gabarits import remplir_gabarit
from app.modele import SortieIllisible, appeler, extraire_json
from app.schemas import Primitive
from app.validation import MotifRejet, Resultat

GABARIT_JUGE = """Tu controles la qualite d'items destines a un jeu d'animation.
Theme annonce : {theme}. Public vise : {public}.

Tu ne juges que deux choses, le reste a deja ete verifie par ailleurs :
1. exactitude factuelle : toute affirmation ou reponse fausse est rejetee ;
2. adequation au public : niveau de difficulte, vocabulaire, et contenu approprie a ce public.

Tu ne juges ni la mise en forme, ni la longueur, ni la presence des champs.
En cas de doute serieux sur un fait, rejette.

Items a controler :
{items}

Reponds uniquement par un tableau JSON d'objets {index, verdict, motif} :
- index est le numero de l'item tel qu'il apparait ci-dessus ;
- verdict vaut exactement "accepte" ou "rejete" ;
- motif est vide si accepte, sinon une phrase courte disant ce qui ne va pas.
Un objet par item, aucun texte autour, aucune balise de code."""


def _items_en_texte(items: list) -> str:
    """Serialise les items en JSON numerote, lisible par le juge."""
    numerotes = [
        {"index": index, **item.model_dump()} for index, item in enumerate(items)
    ]
    return json.dumps(numerotes, ensure_ascii=False, indent=2)


def juger(
    items: list,
    *,
    primitive: Primitive,
    theme: str,
    public: str,
) -> Resultat:
    """Soumet les items au juge et repartit entre retenus et rejetes.

    Un juge injoignable ou illisible ne doit pas faire passer du contenu non
    controle : dans ce cas tout le lot est rejete, et la tentative suivante
    reprendra depuis la generation.
    """
    if not items:
        return Resultat()

    # remplir_gabarit et non str.format : le gabarit contient des accolades
    # JSON d'exemple, que format() prendrait pour des placeholders.
    prompt = remplir_gabarit(
        GABARIT_JUGE, theme=theme, public=public, items=_items_en_texte(items)
    )

    try:
        brut = appeler(prompt, modele=reglages().modele_juge)
        verdicts = extraire_json(brut)
    except SortieIllisible as erreur:
        return Resultat(
            rejets=[MotifRejet(f"juge illisible : {erreur}", index) for index in range(len(items))]
        )

    # Verdict par index, pour ne pas dependre de l'ordre de la reponse.
    par_index: dict[int, dict] = {}
    for entree in verdicts:
        if isinstance(entree, dict) and isinstance(entree.get("index"), int):
            par_index[entree["index"]] = entree

    resultat = Resultat()
    for index, item in enumerate(items):
        entree = par_index.get(index)
        if entree is None:
            resultat.rejets.append(MotifRejet("juge sans verdict pour cet item", index))
            continue

        if str(entree.get("verdict", "")).strip().lower() == "accepte":
            resultat.items.append(item)
        else:
            motif = str(entree.get("motif") or "rejete par le juge sans motif").strip()
            resultat.rejets.append(MotifRejet(motif, index))

    return resultat
