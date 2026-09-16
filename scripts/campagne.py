"""Genere un jeu par format, pour constituer les fixtures et la demo.

Trois usages, tous avec la meme commande a un argument pres :

    python -m scripts.campagne --enregistrer
        Appelle vraiment le modele et sauvegarde chaque reponse brute
        dans fixtures/. C'est la seule passe qui coute de l'argent.
        Compter environ un centime par format.

    python -m scripts.campagne --rejouer
        Rejoue les fixtures, sans reseau ni cout. Remplit la base de
        demonstration avec exactement les memes jeux.

    python -m scripts.campagne --rejouer --sans-base
        Verifie que les fixtures se rejouent, sans toucher a la base.

Le --enregistrer se lance une fois, chez toi, avec ta cle. Ensuite tout
le monde — la CI, la demo en ligne, un recruteur qui clone le depot —
rejoue les memes reponses gratuitement.
"""

import argparse
import sys

from app import modele
from app.catalogue import CATALOGUE
from app.generateur import GenerationEchouee
from app.schemas import Public
from app.transport import DOSSIER_FIXTURES, FixtureIntrouvable, construire

# Un theme par format, choisi pour rester lisible et sans ambiguite.
# Le public retenu est le premier de la liste du format.
THEMES = {
    "quiz_express": "le cinéma des années 90",
    "quiz_minis": "les animaux de la ferme",
    "quiz_thematique": "les capitales du monde",
    "speed_quiz": "le sport",
    "dingbats": "les expressions françaises",
    "personnage_mystere": "les explorateurs",
    "devinettes": "la nature",
    "anagrammes": "les instruments de musique",
    "le_scoop": "les records du vivant",
    "incroyable_vrai": "l'histoire des inventions",
}

# Lots volontairement courts : la campagne sert a constituer des fixtures
# representatives, pas a remplir la base.
NB_ITEMS = 6


def lancer(*, enregistrer: bool, avec_base: bool) -> int:
    mode = "enregistrement" if enregistrer else "rejeu"

    # Un dossier de fixtures vide n'est pas une erreur : c'est l'etat du
    # projet tant qu'aucune campagne n'a tourne. On sort proprement pour
    # que la mise en ligne reussisse quand meme — une demo vide vaut mieux
    # qu'un deploiement qui echoue. Des fixtures presentes mais cassees,
    # en revanche, font echouer la commande.
    if not enregistrer and not list(DOSSIER_FIXTURES.glob("*.json")):
        print(
            f"Aucune fixture dans {DOSSIER_FIXTURES}/ : rien a rejouer.\n"
            "Lancer « python -m scripts.campagne --enregistrer » pour en produire."
        )
        return 0

    modele.definir_transport(construire(mode))
    print(f"Mode : {mode}\n")

    session = None
    if avec_base:
        from app.db import FabriqueSession

        session = FabriqueSession()

    from app.service import generer_et_enregistrer

    succes, echecs = 0, 0
    try:
        for format_jeu in CATALOGUE:
            code = format_jeu["code"]
            theme = THEMES[code]
            public = Public(format_jeu["publics"][0])

            print(f"  {code:20} {theme!r} ({public.value}) … ", end="", flush=True)

            if not avec_base:
                # Sans base, on rejoue seulement le generateur pour verifier
                # que les fixtures repondent.
                from app.catalogue import gabarit_du_format
                from app.generateur import generer

                try:
                    resultat = generer(
                        primitive=format_jeu["primitive"],
                        gabarit=gabarit_du_format(code, format_jeu["primitive"]),
                        nom_format=format_jeu["nom"],
                        theme=theme,
                        public=public.value,
                        nb_items=NB_ITEMS,
                    )
                except (GenerationEchouee, FixtureIntrouvable) as erreur:
                    print(f"echec : {erreur}")
                    echecs += 1
                    continue
                print(f"{len(resultat.items)} items, {len(resultat.rejets)} rejets")
                succes += 1
                continue

            try:
                jeu, resservi = generer_et_enregistrer(
                    session,
                    format_code=code,
                    theme=theme,
                    public=public,
                    nb_items=NB_ITEMS,
                    # En enregistrement on veut vraiment appeler le modele,
                    # pas ressortir un jeu deja en base.
                    reutiliser=not enregistrer,
                )
            except (GenerationEchouee, FixtureIntrouvable) as erreur:
                print(f"echec : {erreur}")
                echecs += 1
                continue

            etat = "resservi" if resservi else "genere"
            print(f"{len(jeu.contenu)} items ({etat})")
            succes += 1
    finally:
        if session is not None:
            session.close()

    print(f"\n{succes} formats traites, {echecs} echecs.")
    if enregistrer:
        print("Fixtures ecrites dans fixtures/. Pense a les committer.")
    return 0 if echecs == 0 else 1


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    groupe = analyseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument(
        "--enregistrer",
        action="store_true",
        help="appelle vraiment le modele et sauvegarde les reponses (payant)",
    )
    groupe.add_argument(
        "--rejouer", action="store_true", help="rejoue les fixtures (gratuit)"
    )
    analyseur.add_argument(
        "--sans-base", action="store_true", help="ne rien ecrire en base"
    )
    arguments = analyseur.parse_args()

    return lancer(
        enregistrer=arguments.enregistrer, avec_base=not arguments.sans_base
    )


if __name__ == "__main__":
    raise SystemExit(main())
