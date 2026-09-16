"""Appel du modele et extraction du JSON de sa reponse.

Tout ce qui touche au reseau est isole ici : le reste du projet
(validation, juge, generateur) reste testable sans cle d'API.

appeler() delegue au transport actif (app/transport.py), ce qui permet
d'enregistrer les reponses reelles une fois puis de les rejouer sans
rien payer. Les appelants ne changent pas : ils appellent toujours
appeler().
"""

import json
import re

from anthropic import Anthropic

from app.config import reglages
from app.transport import Transport, construire


class SortieIllisible(RuntimeError):
    """Le modele a repondu autre chose qu'un tableau JSON exploitable."""


# Le modele encadre parfois sa reponse de ```json malgre la consigne.
_BLOC_CODE = re.compile(r"```(?:json)?", re.IGNORECASE)

_client: Anthropic | None = None


def client() -> Anthropic:
    """Client Anthropic partage, construit au premier appel."""
    global _client
    if _client is None:
        cle = reglages().anthropic_api_key
        if not cle:
            raise RuntimeError(
                "ANTHROPIC_API_KEY absente. Copier .env.example en .env et la renseigner."
            )
        _client = Anthropic(api_key=cle)
    return _client


def extraire_json(texte: str) -> list:
    """Recupere le tableau JSON d'une reponse de modele.

    Tolere les balises de code et le texte d'introduction : on cherche le
    premier crochet ouvrant et le dernier crochet fermant. Si le JSON entre
    les deux est invalide, on echoue explicitement plutot que de deviner.
    """
    nettoye = _BLOC_CODE.sub("", texte).strip()

    debut = nettoye.find("[")
    fin = nettoye.rfind("]")
    if debut == -1 or fin == -1 or fin < debut:
        raise SortieIllisible("aucun tableau JSON dans la reponse du modele")

    try:
        donnees = json.loads(nettoye[debut : fin + 1])
    except json.JSONDecodeError as erreur:
        raise SortieIllisible(f"JSON invalide : {erreur.msg}") from erreur

    if not isinstance(donnees, list):
        raise SortieIllisible("la reponse n'est pas un tableau")
    return donnees


_transport: Transport | None = None


def definir_transport(transport: Transport | None) -> None:
    """Choisit d'ou viennent les reponses. None remet le mode par defaut."""
    global _transport
    _transport = transport


def transport_actif() -> Transport:
    """Le transport courant, construit depuis la configuration au besoin."""
    global _transport
    if _transport is None:
        _transport = construire(reglages().mode_modele)
    return _transport


def appeler(prompt: str, *, modele: str, max_tokens: int = 4096) -> str:
    """Un appel, un prompt, le texte brut de la reponse."""
    return transport_actif()(prompt, modele=modele, max_tokens=max_tokens)
