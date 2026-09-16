"""Etape 3 du cahier des charges : le generateur seul, lance a la main.

Ni base, ni API, ni interface. On appelle le modele, on valide, on affiche.
C'est ici qu'on voit ce que le modele produit vraiment et ce que la
validation attrape.

    python -m scripts.generer --format quiz_express --theme "le cinema" --public ado

L'option --sans-juge evite l'appel au juge pendant la mise au point des
gabarits : on ne paie alors que la generation.
"""

import argparse
import sys

from app.gabarits import COMPLEMENT_DINGBATS, GABARIT_PAR_PRIMITIVE
from app.catalogue import CATALOGUE
from app.generateur import GenerationEchouee, generer
from app.schemas import Primitive


def afficher_question(index: int, item) -> None:
    print(f"\n{index}. {item.question}")
    for lettre, proposition in zip("ABCD", item.propositions):
        marque = ">" if proposition == item.bonne_reponse else " "
        print(f"   {marque} {lettre}. {proposition}")
    print(f"   anecdote : {item.anecdote}")


def afficher_enigme(index: int, item) -> None:
    print(f"\n{index}. {item.enonce}")
    print(f"   indice   : {item.indice}")
    print(f"   solution : {item.solution}")


def afficher_vrai_faux(index: int, item) -> None:
    print(f"\n{index}. {item.affirmation}")
    print(f"   verdict     : {item.verdict}")
    print(f"   explication : {item.explication}")


AFFICHAGE = {
    Primitive.question: afficher_question,
    Primitive.enigme: afficher_enigme,
    Primitive.vrai_faux: afficher_vrai_faux,
}


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--format", required=True, help="code du format, ex. quiz_express")
    analyseur.add_argument("--theme", required=True)
    analyseur.add_argument("--public", required=True)
    analyseur.add_argument("--nb-items", type=int, default=None)
    analyseur.add_argument("--sans-juge", action="store_true")
    arguments = analyseur.parse_args()

    formats = {format_jeu["code"]: format_jeu for format_jeu in CATALOGUE}
    if arguments.format not in formats:
        print(f"Format inconnu. Disponibles : {', '.join(sorted(formats))}", file=sys.stderr)
        return 1

    format_jeu = formats[arguments.format]
    primitive = Primitive(format_jeu["primitive"])
    gabarit = GABARIT_PAR_PRIMITIVE[primitive]
    if format_jeu["code"] == "dingbats":
        gabarit += COMPLEMENT_DINGBATS

    nb_items = arguments.nb_items or format_jeu["nb_items_defaut"]

    print(f"Format    : {format_jeu['nom']} ({primitive.value})")
    print(f"Theme     : {arguments.theme}")
    print(f"Public    : {arguments.public}")
    print(f"Items     : {nb_items}")
    print(f"Juge      : {'non' if arguments.sans_juge else 'oui'}")

    try:
        resultat = generer(
            primitive=primitive,
            gabarit=gabarit,
            nom_format=format_jeu["nom"],
            theme=arguments.theme,
            public=arguments.public,
            nb_items=nb_items,
            avec_juge=not arguments.sans_juge,
        )
    except GenerationEchouee as erreur:
        print(f"\nÉchec : {erreur}", file=sys.stderr)
        for rejet in erreur.rejets:
            print(f"  [{rejet.niveau.value}] {rejet.motif}", file=sys.stderr)
        return 1

    afficher = AFFICHAGE[primitive]
    for index, item in enumerate(resultat.items, start=1):
        afficher(index, item)

    print(f"\n--- {len(resultat.items)} items retenus, {len(resultat.rejets)} rejets "
          f"en {resultat.tentatives} tentative(s), taux de rejet {resultat.taux_rejet:.0%}")
    for rejet in resultat.rejets:
        print(f"  [{rejet.niveau.value}] {rejet.motif}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
