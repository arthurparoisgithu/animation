"""Les trois manieres d'obtenir une reponse de modele.

C'est la couture du projet. Le generateur et le juge ne savent pas d'ou
vient la reponse : ils appellent modele.appeler(), qui delegue au
transport actif.

- TransportApi       : appelle vraiment l'API, et facture.
- TransportEnregistre : appelle vraiment, puis ecrit la reponse sur disque.
- TransportRejeu      : ne rappelle jamais, relit la reponse enregistree.

Interet : une seule campagne payante suffit. Les tests, la demo et le
developpement rejouent ensuite les memes reponses, gratuitement et de
facon deterministe. Et les fixtures obtenues sont de vraies sorties de
modele, defauts compris — c'est exactement ce que la validation doit
attraper.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

DOSSIER_FIXTURES = Path("fixtures")

# Longueur du condensat dans le nom de fichier : 8 caracteres hexadecimaux
# suffisent largement pour quelques centaines de fixtures.
_LONGUEUR_EMPREINTE = 8
_LONGUEUR_SLUG = 40


class FixtureIntrouvable(RuntimeError):
    """Aucun enregistrement ne correspond a ce prompt."""


class Transport(Protocol):
    """Ce que le reste du code attend : un prompt entre, du texte sort."""

    def __call__(self, prompt: str, *, modele: str, max_tokens: int = 4096) -> str: ...


def empreinte(prompt: str, modele: str) -> str:
    """Identifie un appel de facon reproductible.

    Le modele fait partie de l'empreinte : la meme question posee a Haiku
    et a Sonnet sont deux appels differents, et on ne veut pas rejouer
    l'un a la place de l'autre.
    """
    condensat = hashlib.sha256(f"{modele}\n{prompt}".encode("utf-8")).hexdigest()
    return condensat[:_LONGUEUR_EMPREINTE]


def _slug(texte: str) -> str:
    """Debut de prompt transforme en nom de fichier lisible.

    Sans ca les fixtures s'appellent « a1b2c3d4.json » et sont
    inspectables uniquement en les ouvrant une par une.
    """
    premiere_ligne = texte.strip().splitlines()[0] if texte.strip() else "vide"
    sans_accents = "".join(
        c for c in unicodedata.normalize("NFD", premiere_ligne)
        if unicodedata.category(c) != "Mn"
    )
    slug = re.sub(r"[^a-z0-9]+", "-", sans_accents.lower()).strip("-")
    return slug[:_LONGUEUR_SLUG] or "prompt"


def chemin_fixture(prompt: str, modele: str, dossier: Path = DOSSIER_FIXTURES) -> Path:
    return dossier / f"{_slug(prompt)}-{empreinte(prompt, modele)}.json"


class TransportApi:
    """Le vrai appel reseau. C'est le seul transport qui coute de l'argent."""

    def __call__(self, prompt: str, *, modele: str, max_tokens: int = 4096) -> str:
        from app.modele import client  # import tardif : evite un cycle

        reponse = client().messages.create(
            model=modele,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(bloc.text for bloc in reponse.content if bloc.type == "text")


class TransportEnregistre:
    """Decore un transport et conserve ce qu'il a repondu.

    On enregistre la reponse brute, avant toute validation : une sortie
    rejetee est aussi interessante qu'une sortie acceptee, et c'est meme
    elle qui prouve que la validation sert a quelque chose.
    """

    def __init__(self, interne: Transport, dossier: Path = DOSSIER_FIXTURES) -> None:
        self.interne = interne
        self.dossier = dossier
        self.enregistrees: list[Path] = []

    def __call__(self, prompt: str, *, modele: str, max_tokens: int = 4096) -> str:
        reponse = self.interne(prompt, modele=modele, max_tokens=max_tokens)

        self.dossier.mkdir(parents=True, exist_ok=True)
        chemin = chemin_fixture(prompt, modele, self.dossier)
        chemin.write_text(
            json.dumps(
                {
                    "modele": modele,
                    "empreinte": empreinte(prompt, modele),
                    "enregistre_le": datetime.now(timezone.utc).isoformat(),
                    "prompt": prompt,
                    "reponse": reponse,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.enregistrees.append(chemin)
        return reponse


class TransportRejeu:
    """Relit les reponses enregistrees. Ne touche jamais au reseau.

    Un prompt absent du dossier leve une erreur explicite plutot que de
    retomber sur un appel reel : sinon une demo publique se mettrait a
    facturer sans prevenir.
    """

    def __init__(self, dossier: Path = DOSSIER_FIXTURES) -> None:
        self.dossier = dossier

    def __call__(self, prompt: str, *, modele: str, max_tokens: int = 4096) -> str:
        chemin = chemin_fixture(prompt, modele, self.dossier)
        if not chemin.exists():
            raise FixtureIntrouvable(
                f"aucune fixture pour ce prompt ({empreinte(prompt, modele)}, {modele}). "
                f"Attendu : {chemin}. Lancer une campagne d'enregistrement d'abord."
            )
        return json.loads(chemin.read_text(encoding="utf-8"))["reponse"]


def construire(mode: str, dossier: Path = DOSSIER_FIXTURES) -> Transport:
    """Fabrique le transport correspondant au mode demande."""
    if mode == "api":
        return TransportApi()
    if mode == "enregistrement":
        return TransportEnregistre(TransportApi(), dossier)
    if mode == "rejeu":
        return TransportRejeu(dossier)
    raise ValueError(f"mode inconnu : {mode!r} (api, enregistrement ou rejeu)")
