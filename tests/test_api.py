"""Le chemin complet : requete HTTP, generation, validation, base, reponse.

L'appel au modele est simule, donc ces tests sont deterministes et gratuits.
Ils ont en revanche besoin d'un vrai Postgres : les tableaux, le jsonb et
l'operateur de contenance ne s'emulent pas en SQLite.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import generateur, juge as module_juge
from tests.conftest import (
    ModeleSimule,
    base_requise,
    sortie_enigmes,
    sortie_questions,
    verdicts_juge,
)

pytestmark = base_requise


def configurer(monkeypatch, *, mode: str, code: str | None = None) -> None:
    """Regle le mode du modele et vide le cache de configuration.

    reglages() est mis en cache par lru_cache : sans ce vidage, une
    variable changee apres le premier appel resterait sans effet, et le
    test verrait la configuration d'un autre.
    """
    from app.config import reglages

    monkeypatch.setenv("MODE_MODELE", mode)
    if code is None:
        monkeypatch.delenv("CODE_GENERATION", raising=False)
    else:
        monkeypatch.setenv("CODE_GENERATION", code)
    reglages.cache_clear()


@pytest.fixture
def client(monkeypatch):
    from app.config import reglages
    from app.db import FabriqueSession, moteur
    from app.main import app
    from scripts.seed import lignes
    from sqlalchemy.dialects.postgresql import insert
    from app.modeles import FormatJeu

    # Base remise a plat puis reseedee : chaque test part du meme etat.
    with moteur.begin() as connexion:
        connexion.execute(text("TRUNCATE jeu, rejet"))

    with FabriqueSession() as session:
        requete = insert(FormatJeu).values(lignes())
        session.execute(requete.on_conflict_do_nothing(index_elements=["code"]))
        session.commit()

    # Le modele est simule dans ces tests : aucun appel n'est emis et rien
    # n'est facture. On configure donc l'application comme une instance
    # sans cout, ou aucun code n'est exige. Les tests qui verifient la
    # protection rebasculent en mode « api » eux-memes.
    configurer(monkeypatch, mode="rejeu")

    yield TestClient(app)

    reglages.cache_clear()


@pytest.fixture
def simuler(monkeypatch):
    def brancher(reponses_generation, reponses_juge=()):
        monkeypatch.setattr(generateur, "appeler", ModeleSimule(reponses_generation))
        monkeypatch.setattr(module_juge, "appeler", ModeleSimule(list(reponses_juge)))

    return brancher


def test_la_route_de_vie_repond(client):
    assert client.get("/sante").json() == {"statut": "ok"}


def test_le_catalogue_contient_les_onze_formats(client):
    formats = client.get("/api/formats").json()
    assert len(formats) == 11


def test_le_catalogue_se_filtre_par_public(client):
    # C'est la requete qui utilise l'operateur de contenance @>.
    codes = {f["code"] for f in client.get("/api/formats?public=mini").json()}
    assert codes == {"quiz_minis", "devinettes"}


def test_le_catalogue_se_filtre_par_materiel_et_moment(client):
    formats = client.get("/api/formats?moment=cafe_apero&materiel=aucun").json()
    codes = {f["code"] for f in formats}
    assert codes == {"quiz_express", "incroyable_vrai"}


def test_un_filtre_sans_resultat_renvoie_une_liste_vide(client):
    assert client.get("/api/formats?public=mini&moment=soiree_adultes").json() == []


def test_generer_un_jeu_l_enregistre_et_le_renvoie(client, simuler):
    simuler([sortie_questions(3)], [verdicts_juge(3)])

    reponse = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "le cinema", "public": "ado", "nb_items": 3},
    )

    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["nb_items"] == 3
    assert corps["resservi"] is False
    assert len(corps["contenu"]) == 3

    # Le jeu est bien en base et relisible.
    relu = client.get(f"/api/jeux/{corps['id']}").json()
    assert relu["theme"] == "le cinema"


def test_un_jeu_deja_en_base_est_resservi_sans_nouvel_appel(client, simuler):
    simuler([sortie_questions(2)], [verdicts_juge(2)])
    premier = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "le sport", "public": "ado", "nb_items": 2},
    ).json()

    # Aucune reponse de modele fournie : si le code rappelait le modele,
    # le simulateur leverait une erreur. C'est le levier de cout du projet.
    simuler([], [])
    second = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "  LE SPORT ", "public": "ado"},
    ).json()

    assert second["id"] == premier["id"]
    assert second["resservi"] is True


def test_une_generation_qui_echoue_renvoie_422_et_les_motifs(client, simuler):
    illisible = "Desole, je ne peux pas."
    simuler([illisible] * 3, [])

    reponse = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "le cinema", "public": "ado", "nb_items": 3},
    )

    # 422 et non 500 : ce n'est pas un bug, c'est la validation qui refuse
    # de livrer du contenu non verifie.
    assert reponse.status_code == 422
    detail = reponse.json()["detail"]
    assert detail["rejets"]
    assert all(r["niveau"] == "deterministe" for r in detail["rejets"])


def test_les_rejets_alimentent_la_metrique(client, simuler):
    lot = sortie_questions(4).replace('"Autre C"', '"Autre B"')  # doublon : 4 items rejetes
    simuler([lot, sortie_questions(2, depart=50)], [verdicts_juge(2)])

    client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "les doublons", "public": "ado", "nb_items": 2},
    )

    metriques = client.get("/api/metriques/rejets").json()
    ligne = next(m for m in metriques if m["code"] == "quiz_express")
    assert ligne["rejets_deterministe"] == 4
    assert ligne["items_retenus"] == 2
    assert ligne["taux"] == pytest.approx(4 / 6)
    assert ligne["escalade_conseillee"] is True  # au-dela de 20 %


def test_un_format_inconnu_renvoie_404(client, simuler):
    simuler([], [])
    reponse = client.post(
        "/api/jeux",
        json={"format_code": "jeu_inexistant", "theme": "le cinema", "public": "ado"},
    )
    assert reponse.status_code == 404


def test_le_favori_se_bascule(client, simuler):
    simuler([sortie_questions(2)], [verdicts_juge(2)])
    jeu = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "les favoris", "public": "ado", "nb_items": 2},
    ).json()

    assert client.patch(f"/api/jeux/{jeu['id']}/favori").json()["favori"] is True
    assert client.patch(f"/api/jeux/{jeu['id']}/favori").json()["favori"] is False


def test_les_pages_html_repondent(client, simuler):
    simuler([sortie_questions(2)], [verdicts_juge(2)])
    jeu = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "les pages", "public": "ado", "nb_items": 2},
    ).json()

    for chemin in ("/", "/metriques", f"/jeu/{jeu['id']}", f"/projection/{jeu['id']}"):
        reponse = client.get(chemin)
        assert reponse.status_code == 200, chemin
        assert "text/html" in reponse.headers["content-type"]


def test_l_escape_game_traverse_tout_le_chemin_sans_code_dedie(client, simuler):
    """Le onzieme format doit marcher de bout en bout sans ligne de Python.

    C'est l'argument central du projet mis a l'epreuve : escape_game n'est
    qu'une entree de catalogue et un complement de gabarit, et pourtant il
    se filtre, se genere, se valide et s'enregistre comme les autres.
    """
    # Il est le seul a se jouer en grand jeu avec des accessoires : ces deux
    # valeurs d'enumeration n'etaient portees par aucun format avant lui.
    formats = client.get("/api/formats?moment=grand_jeu&materiel=accessoires").json()
    assert {f["code"] for f in formats} == {"escape_game"}

    simuler([sortie_enigmes(3)], [verdicts_juge(3)])
    reponse = client.post(
        "/api/jeux",
        json={
            "format_code": "escape_game",
            "theme": "le phare abandonne",
            "public": "ado",
            "nb_items": 3,
        },
    )

    assert reponse.status_code == 201
    corps = reponse.json()
    assert len(corps["contenu"]) == 3
    # La primitive enigme, telle quelle : ni champ en plus, ni champ en moins.
    assert set(corps["contenu"][0]) == {"enonce", "solution", "indice"}


def test_un_appel_de_modele_qui_echoue_renvoie_du_json_lisible(client, monkeypatch):
    """Le cas vecu : cle refusee, et l'ecran affichait « Unexpected token I ».

    L'application repondait 500 « Internal Server Error » en texte brut, que
    la page tentait de lire comme du JSON. Deux defauts d'un coup : la cause
    etait perdue cote serveur, et illisible cote navigateur.
    """
    import anthropic
    import httpx2 as httpx

    from app import modele as module_modele

    def cle_refusee(prompt, *, modele, max_tokens=4096):
        requete = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        raise anthropic.AuthenticationError(
            "Error code: 401", response=httpx.Response(401, request=requete), body=None
        )

    # On remplace le transport, pas appeler() : c'est appeler() qui porte la
    # traduction, et le but du test est justement de la traverser. Patcher
    # generateur.appeler court-circuiterait ce qu'on veut verifier.
    monkeypatch.setattr(module_modele, "transport_actif", lambda: cle_refusee)

    reponse = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "la cle", "public": "ado", "nb_items": 2},
    )

    # 502 : le service en amont a echoue, l'application n'est pas cassee.
    assert reponse.status_code == 502
    assert "application/json" in reponse.headers["content-type"]
    assert "ANTHROPIC_API_KEY" in reponse.json()["detail"]


def test_la_page_d_un_jeu_porte_la_fiche_imprimable(client, simuler):
    """La feuille que l'animateur emporte quand le videoprojecteur lache."""
    simuler([sortie_questions(2)], [verdicts_juge(2)])
    jeu = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "la fiche", "public": "ado", "nb_items": 2},
    ).json()

    page = client.get(f"/jeu/{jeu['id']}").text

    assert 'id="imprimer"' in page
    assert "/static/fiche.js" in page
    # L'avertissement ne s'affiche qu'a l'impression, mais il doit etre
    # dans le document : c'est la feuille de style qui le revele.
    assert "ne pas la laisser aux équipes" in page
    # La regle du format est sur la fiche : sans elle, la feuille ne sert
    # qu'a lire les reponses, pas a animer. Fragment sans apostrophe :
    # Jinja echappe « L'animateur » en « L&#39;animateur ».
    assert "Les équipes annoncent leur lettre" in page


def test_le_json_de_projection_est_echappe(client, simuler):
    # Un item contenant </script> ne doit pas pouvoir fermer le bloc.
    piege = sortie_questions(2).replace("Une anecdote courte.", "</script> piege")
    simuler([piege], [verdicts_juge(2)])
    jeu = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "l echappement", "public": "ado", "nb_items": 2},
    ).json()

    page = client.get(f"/projection/{jeu['id']}").text
    bloc = page.split('type="application/json">')[1].split("</script>")[0]
    assert "\\u003c" in bloc
    assert "</script> piege" not in bloc


def test_en_mode_rejeu_un_theme_inedit_renvoie_503_et_non_500(client, monkeypatch):
    # Scenario de la demo publique : l'instance rejoue des fixtures et un
    # visiteur saisit un theme qui n'a jamais ete genere.
    from app import modele
    from app.transport import TransportRejeu

    monkeypatch.setattr(modele, "_transport", TransportRejeu(Path("aucun_dossier")))

    reponse = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "un theme inedit", "public": "ado"},
    )

    assert reponse.status_code == 503
    assert "démonstration" in reponse.json()["detail"]


# --- Protection de la generation payante ---


def test_en_mode_api_sans_code_la_generation_est_refusee(client, monkeypatch):
    # Le scenario redoute : instance en ligne qui appelle un modele
    # facture, sans code. Elle doit refuser, pas ouvrir la porte.
    configurer(monkeypatch, mode="api", code="")

    reponse = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "le cinema", "public": "ado"},
    )

    assert reponse.status_code == 403
    assert "CODE_GENERATION" in reponse.json()["detail"]


def test_en_mode_api_un_mauvais_code_est_refuse(client, monkeypatch):
    configurer(monkeypatch, mode="api", code="le-bon-code")

    reponse = client.post(
        "/api/jeux",
        json={
            "format_code": "quiz_express",
            "theme": "le cinema",
            "public": "ado",
            "code": "le-mauvais-code",
        },
    )

    assert reponse.status_code == 403


def test_en_mode_rejeu_aucun_code_n_est_exige(client, simuler, monkeypatch):
    # Le rejeu n'emet aucun appel, donc ne coute rien : exiger un code
    # empecherait une demo publique de fonctionner.
    configurer(monkeypatch, mode="rejeu", code="")
    simuler([sortie_questions(2)], [verdicts_juge(2)])

    reponse = client.post(
        "/api/jeux",
        json={"format_code": "quiz_express", "theme": "sans code", "public": "ado", "nb_items": 2},
    )

    assert reponse.status_code == 201
