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

from anthropic import (
    Anthropic,
    AnthropicError,
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from app.config import reglages
from app.transport import Transport, construire


class SortieIllisible(RuntimeError):
    """Le modele a repondu autre chose qu'un tableau JSON exploitable."""


class AppelModeleEchoue(RuntimeError):
    """L'appel n'a pas abouti, pour une raison exterieure au contenu genere.

    Distincte de SortieIllisible et de GenerationEchouee : ici le modele n'a
    rien repondu du tout. La cause est une cle refusee, un credit epuise, une
    surcharge ou le reseau — et l'animateur doit pouvoir la lire a l'ecran
    plutot que de recevoir une erreur 500 sans explication.
    """


# Le modele encadre parfois sa reponse de ```json malgre la consigne.
_BLOC_CODE = re.compile(r"```(?:json)?", re.IGNORECASE)

_client: Anthropic | None = None


def client() -> Anthropic:
    """Client Anthropic partage, construit au premier appel."""
    global _client
    if _client is None:
        cle = reglages().anthropic_api_key
        if not cle:
            raise AppelModeleEchoue(
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


# Le message que renvoie l'API quand le compte n'a plus de credit. Il arrive
# sous forme de 400, indistinguable d'une requete malformee sans le lire.
_MOTIF_CREDIT = "credit balance"


def motif_lisible(erreur: AnthropicError, modele: str) -> str:
    """Traduit une erreur du SDK en une phrase que l'animateur peut agir.

    Une chaine du plus precis au plus general, comme le recommande le SDK :
    un « except APIStatusError » unique perdrait la difference entre une cle
    refusee (a corriger) et une surcharge passagere (a reessayer).
    """
    if isinstance(erreur, AuthenticationError):
        return (
            "Clé d'API refusée par Anthropic. Vérifie la ligne ANTHROPIC_API_KEY "
            "du fichier .env, puis redémarre l'application."
        )
    if isinstance(erreur, PermissionDeniedError):
        return (
            "Clé d'API valide mais sans les droits nécessaires. Vérifie les "
            "permissions de la clé dans la console Anthropic."
        )
    if isinstance(erreur, NotFoundError):
        return (
            f"Modèle introuvable : {modele}. Vérifie l'identifiant du modèle "
            "dans la configuration."
        )
    if isinstance(erreur, RateLimitError):
        return "Trop d'appels d'un coup. Attends une minute et relance la génération."
    if isinstance(erreur, BadRequestError) and _MOTIF_CREDIT in str(erreur).lower():
        return (
            "Crédit insuffisant sur le compte Anthropic. Ajoute du crédit dans "
            "la console, rubrique Billing. Un jeu coûte environ un demi-centime."
        )
    if isinstance(erreur, APIStatusError):
        if erreur.status_code >= 500:
            return (
                f"Le service du modèle est momentanément indisponible "
                f"(code {erreur.status_code}). Réessaie dans quelques minutes."
            )
        return f"Appel refusé par l'API (code {erreur.status_code}) : {erreur}"
    if isinstance(erreur, APIConnectionError):
        return (
            "Impossible de joindre l'API Anthropic. Vérifie la connexion "
            "internet de la machine."
        )
    return f"Appel au modèle impossible : {erreur}"


def appeler(prompt: str, *, modele: str, max_tokens: int = 4096) -> str:
    """Un appel, un prompt, le texte brut de la reponse.

    Les erreurs du SDK sont traduites ici, au seul endroit du projet qui
    connait Anthropic. Le reste du code ne voit qu'AppelModeleEchoue, avec
    un motif redigee pour etre affichee telle quelle.
    """
    try:
        return transport_actif()(prompt, modele=modele, max_tokens=max_tokens)
    except AnthropicError as erreur:
        raise AppelModeleEchoue(motif_lisible(erreur, modele)) from erreur
