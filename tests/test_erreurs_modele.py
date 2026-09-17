"""Ce que voit l'animateur quand l'appel au modele echoue.

Un 500 sans explication est le pire resultat possible pour ce projet : la
these est qu'une erreur explicite vaut mieux qu'un contenu plausible, et
elle ne tient que si l'erreur est effectivement lisible. Ces tests sont
purs — aucune cle, aucun reseau, aucune base.
"""

import anthropic
import httpx2 as httpx
import pytest

from app.modele import AppelModeleEchoue, appeler, motif_lisible

MODELE = "claude-haiku-4-5-20251001"


def _reponse(code: int) -> httpx.Response:
    requete = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx.Response(code, request=requete)


def _erreur(classe, code: int, message: str = "Error code"):
    return classe(message, response=_reponse(code), body=None)


@pytest.mark.parametrize(
    "erreur, attendu",
    [
        (_erreur(anthropic.AuthenticationError, 401), "ANTHROPIC_API_KEY"),
        (_erreur(anthropic.PermissionDeniedError, 403), "droits nécessaires"),
        (_erreur(anthropic.NotFoundError, 404), MODELE),
        (_erreur(anthropic.RateLimitError, 429), "Attends une minute"),
        (_erreur(anthropic.APIStatusError, 529), "indisponible"),
        (_erreur(anthropic.APIStatusError, 500), "indisponible"),
    ],
)
def test_chaque_cause_a_son_message(erreur, attendu):
    assert attendu in motif_lisible(erreur, MODELE)


def test_le_credit_epuise_est_distingue_d_une_requete_invalide():
    """Les deux arrivent en 400 : seul le texte les separe.

    C'est la panne la plus probable pour quelqu'un qui vient de creer sa
    cle, et « requete invalide » ne lui dirait pas quoi faire.
    """
    epuise = _erreur(
        anthropic.BadRequestError,
        400,
        "Your credit balance is too low to access the API",
    )
    assert "Crédit insuffisant" in motif_lisible(epuise, MODELE)

    autre = _erreur(anthropic.BadRequestError, 400, "max_tokens is too large")
    motif = motif_lisible(autre, MODELE)
    assert "Crédit insuffisant" not in motif
    assert "400" in motif


def test_une_panne_reseau_ne_parle_pas_de_cle():
    motif = motif_lisible(
        anthropic.APIConnectionError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        ),
        MODELE,
    )
    assert "connexion" in motif.lower()
    assert "cle" not in motif.lower()


def test_appeler_traduit_l_erreur_du_sdk(monkeypatch):
    """La frontiere : au-dela d'appeler(), plus personne ne connait Anthropic."""

    def transport_qui_echoue(prompt, *, modele, max_tokens=4096):
        raise _erreur(anthropic.AuthenticationError, 401)

    monkeypatch.setattr("app.modele.transport_actif", lambda: transport_qui_echoue)

    with pytest.raises(AppelModeleEchoue) as capture:
        appeler("peu importe", modele=MODELE)

    assert "ANTHROPIC_API_KEY" in str(capture.value)
    # La cause d'origine reste attachee : le journal du serveur garde la
    # trace technique, l'ecran n'affiche que la phrase lisible.
    assert isinstance(capture.value.__cause__, anthropic.AuthenticationError)


def test_une_erreur_de_fixture_n_est_pas_traduite(monkeypatch):
    """Le mode rejeu a deja son propre message et son propre code HTTP.

    Sans cette garantie, un theme inedit en demonstration passerait de 503
    a 502 avec un motif faux.
    """
    from app.transport import FixtureIntrouvable

    def transport_sans_fixture(prompt, *, modele, max_tokens=4096):
        raise FixtureIntrouvable("aucune fixture")

    monkeypatch.setattr("app.modele.transport_actif", lambda: transport_sans_fixture)

    with pytest.raises(FixtureIntrouvable):
        appeler("peu importe", modele=MODELE)


def test_les_motifs_affiches_sont_en_francais_accentue():
    """Meme regle que pour le catalogue et les gabarits.

    Ces phrases s'affichent en rouge sous le formulaire de generation.
    Un « Cle d'API refusee » sans accents trahit du texte ecrit a la
    va-vite, et ca se voit a l'ecran.
    """
    accentues = set("àâäéèêëîïôöùûüç")

    motifs = [
        motif_lisible(_erreur(classe, code), MODELE)
        for classe, code in [
            (anthropic.AuthenticationError, 401),
            (anthropic.PermissionDeniedError, 403),
            (anthropic.NotFoundError, 404),
            (anthropic.RateLimitError, 429),
            (anthropic.APIStatusError, 529),
        ]
    ]
    motifs.append(
        motif_lisible(
            _erreur(anthropic.BadRequestError, 400, "Your credit balance is too low"),
            MODELE,
        )
    )

    for motif in motifs:
        assert accentues & set(motif.lower()), f"motif sans aucun accent : {motif}"
