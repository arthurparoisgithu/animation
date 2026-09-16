"""Enregistrement et rejeu des reponses de modele.

Ce qui est verifie ici : ce qu'on rejoue est exactement ce qu'on a
enregistre, et un rejeu sans fixture echoue bruyamment plutot que de
repartir en silence vers un appel facture.
"""

import json

import pytest

from app.transport import (
    DOSSIER_FIXTURES,
    FixtureIntrouvable,
    TransportEnregistre,
    TransportRejeu,
    chemin_fixture,
    construire,
    empreinte,
)

MODELE = "claude-haiku-4-5-20251001"


class FauxModele:
    """Tient lieu d'appel reseau : compte les appels et renvoie du texte."""

    def __init__(self, reponses: list[str]) -> None:
        self.reponses = list(reponses)
        self.appels = 0

    def __call__(self, prompt: str, *, modele: str, max_tokens: int = 4096) -> str:
        self.appels += 1
        return self.reponses.pop(0)


def test_l_empreinte_est_stable_pour_le_meme_appel():
    assert empreinte("un prompt", MODELE) == empreinte("un prompt", MODELE)


def test_l_empreinte_change_avec_le_prompt():
    assert empreinte("un prompt", MODELE) != empreinte("un autre prompt", MODELE)


def test_l_empreinte_change_avec_le_modele():
    # La meme question posee a deux modeles donne deux appels distincts :
    # rejouer l'un a la place de l'autre serait une erreur silencieuse.
    assert empreinte("un prompt", MODELE) != empreinte("un prompt", "claude-sonnet-5")


def test_le_nom_de_fixture_reste_lisible(tmp_path):
    chemin = chemin_fixture("Tu generes 6 questions pour un jeu.\nTheme : X.", MODELE, tmp_path)
    assert chemin.name.startswith("tu-generes-6-questions-pour-un-jeu")
    assert chemin.suffix == ".json"


def test_enregistre_puis_rejoue_a_l_identique(tmp_path):
    faux = FauxModele(['[{"question": "Q ?"}]'])
    enregistreur = TransportEnregistre(faux, tmp_path)

    original = enregistreur("un prompt", modele=MODELE)

    rejoueur = TransportRejeu(tmp_path)
    assert rejoueur("un prompt", modele=MODELE) == original
    # Le rejeu n'a pas rappele le modele.
    assert faux.appels == 1


def test_le_rejeu_ne_rappelle_jamais_le_modele(tmp_path):
    faux = FauxModele(["reponse"])
    TransportEnregistre(faux, tmp_path)("un prompt", modele=MODELE)

    rejoueur = TransportRejeu(tmp_path)
    for _ in range(5):
        rejoueur("un prompt", modele=MODELE)

    assert faux.appels == 1


def test_une_fixture_absente_echoue_explicitement(tmp_path):
    with pytest.raises(FixtureIntrouvable) as erreur:
        TransportRejeu(tmp_path)("prompt jamais enregistre", modele=MODELE)

    # Le message doit dire quoi faire, pas seulement que ca a rate.
    assert "campagne" in str(erreur.value)


def test_la_fixture_conserve_le_prompt_et_la_reponse(tmp_path):
    faux = FauxModele(["la reponse brute du modele"])
    TransportEnregistre(faux, tmp_path)("le prompt envoye", modele=MODELE)

    fichier = next(tmp_path.glob("*.json"))
    contenu = json.loads(fichier.read_text(encoding="utf-8"))

    # Le prompt est conserve : une fixture doit etre relisible par un
    # humain, sinon elle ne prouve rien.
    assert contenu["prompt"] == "le prompt envoye"
    assert contenu["reponse"] == "la reponse brute du modele"
    assert contenu["modele"] == MODELE
    assert contenu["enregistre_le"]


def test_la_reponse_est_enregistree_meme_si_elle_est_invalide(tmp_path):
    # Une sortie cassee est la fixture la plus interessante du projet :
    # c'est elle qui prouve que la validation attrape quelque chose.
    cassee = "Bien sur ! Voici vos questions :"
    TransportEnregistre(FauxModele([cassee]), tmp_path)("un prompt", modele=MODELE)

    assert TransportRejeu(tmp_path)("un prompt", modele=MODELE) == cassee


def test_construire_renvoie_le_bon_transport(tmp_path):
    assert isinstance(construire("rejeu", tmp_path), TransportRejeu)
    assert isinstance(construire("enregistrement", tmp_path), TransportEnregistre)
    assert type(construire("api")).__name__ == "TransportApi"


def test_un_mode_inconnu_est_refuse():
    with pytest.raises(ValueError):
        construire("gratuit")


def test_le_dossier_par_defaut_est_a_la_racine():
    assert DOSSIER_FIXTURES.name == "fixtures"


def test_un_dossier_de_fixtures_vide_ne_fait_pas_echouer_le_rejeu(tmp_path, monkeypatch):
    """Un dossier vide est l'etat normal tant qu'aucune campagne n'a tourne.

    C'est ce qui permet a une premiere mise en ligne de reussir avant meme
    d'avoir enregistre quoi que ce soit : une demo vide vaut mieux qu'un
    deploiement qui echoue.
    """
    from scripts import campagne

    monkeypatch.setattr(campagne, "DOSSIER_FIXTURES", tmp_path)

    assert campagne.lancer(enregistrer=False, avec_base=False) == 0
