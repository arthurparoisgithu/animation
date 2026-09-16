"""Fixtures partagees.

Les tests de l'API ont besoin d'un Postgres. S'il n'y en a pas, ils sont
ignores plutot que mis en echec : la suite de validation, elle, doit
pouvoir tourner n'importe ou sans rien installer.
"""

import json
import os

import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _base_joignable() -> bool:
    """Teste la connexion en passant par la meme normalisation que l'app.

    Sans passer par Reglages, une URL « postgres://… » — celle que
    fournissent les hebergeurs — echouerait ici et ferait silencieusement
    ignorer les quatorze tests de base.

    Si DATABASE_URL est definie mais que la base ne repond pas, on laisse
    l'erreur remonter : une variable renseignee qui ne marche pas est un
    probleme a signaler, pas a contourner. On n'ignore que le cas ou
    aucune base n'a ete configuree du tout.
    """
    if not DATABASE_URL:
        return False

    from sqlalchemy import create_engine, text

    from app.config import Reglages

    moteur = create_engine(Reglages(database_url=DATABASE_URL).database_url)
    with moteur.connect() as connexion:
        connexion.execute(text("select 1"))
    return True


base_requise = pytest.mark.skipif(
    not _base_joignable(),
    reason="DATABASE_URL non definie : tests de base ignores",
)


class ModeleSimule:
    """Remplace l'appel reseau par des reponses ecrites a l'avance.

    Permet de tester tout le chemin — API, generation, validation, base —
    sans cle d'API, sans reseau, et de facon deterministe.
    """

    def __init__(self, reponses: list[str]) -> None:
        self.reponses = list(reponses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str, *, modele: str, max_tokens: int = 4096) -> str:
        self.prompts.append(prompt)
        if not self.reponses:
            raise AssertionError("le modele simule a ete appele plus que prevu")
        return self.reponses.pop(0)


def sortie_questions(nb: int, depart: int = 0) -> str:
    """Un lot de questions valides, au format attendu du modele."""
    items = [
        {
            "question": f"Question numero {depart + i} ?",
            "propositions": [f"Reponse {depart + i}", "Autre A", "Autre B", "Autre C"],
            "bonne_reponse": f"Reponse {depart + i}",
            "anecdote": "Une anecdote courte.",
        }
        for i in range(nb)
    ]
    return json.dumps(items, ensure_ascii=False)


# Des solutions volontairement absentes de l'enonce et de l'indice : la
# validation de la primitive enigme refuse une enigme qui se donne.
_SOLUTIONS = ("Lanterne", "Boussole", "Sextant", "Ancre", "Cordage", "Fanal")


def sortie_enigmes(nb: int) -> str:
    """Un lot d'enigmes valides, au format attendu du modele."""
    items = [
        {
            "enonce": f"Etape {i} : ce que le gardien reclame avant d'ouvrir la serrure.",
            "solution": _SOLUTIONS[i % len(_SOLUTIONS)],
            "indice": "Un marin du siecle dernier en avait toujours un.",
        }
        for i in range(nb)
    ]
    return json.dumps(items, ensure_ascii=False)


def verdicts_juge(nb: int, accepte: bool = True) -> str:
    return json.dumps(
        [
            {
                "index": i,
                "verdict": "accepte" if accepte else "rejete",
                "motif": "" if accepte else "fait inexact",
            }
            for i in range(nb)
        ]
    )
