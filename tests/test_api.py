"""Le chemin complet : requete HTTP, generation, validation, base, reponse.

L'appel au modele est simule, donc ces tests sont deterministes et gratuits.
Ils ont en revanche besoin d'un vrai Postgres : les tableaux, le jsonb et
l'operateur de contenance ne s'emulent pas en SQLite.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import generateur, juge as module_juge
from tests.conftest import ModeleSimule, base_requise, sortie_questions, verdicts_juge

pytestmark = base_requise


@pytest.fixture
def client():
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

    return TestClient(app)


@pytest.fixture
def simuler(monkeypatch):
    def brancher(reponses_generation, reponses_juge=()):
        monkeypatch.setattr(generateur, "appeler", ModeleSimule(reponses_generation))
        monkeypatch.setattr(module_juge, "appeler", ModeleSimule(list(reponses_juge)))

    return brancher


def test_la_route_de_vie_repond(client):
    assert client.get("/sante").json() == {"statut": "ok"}


def test_le_catalogue_contient_les_dix_formats(client):
    formats = client.get("/api/formats").json()
    assert len(formats) == 10


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
