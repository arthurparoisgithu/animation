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
    if not DATABASE_URL:
        return False
    try:
        from sqlalchemy import create_engine, text

        moteur = create_engine(DATABASE_URL)
        with moteur.connect() as connexion:
            connexion.execute(text("select 1"))
        return True
    except Exception:
        return False


base_requise = pytest.mark.skipif(
    not _base_joignable(), reason="aucune base Postgres joignable via DATABASE_URL"
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
