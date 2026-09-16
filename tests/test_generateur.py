"""Le generateur, teste sans reseau : l'appel au modele est simule.

Ce qui est verifie ici, c'est l'orchestration : l'ordre des deux niveaux,
la boucle de tentatives, et le fait que rien d'invalide ne ressort.
"""

import json

import pytest

from app import generateur, juge as module_juge
from app.gabarits import GABARIT_QUESTION
from app.generateur import GenerationEchouee, generer
from app.schemas import NiveauRejet, Primitive
from tests.conftest import ModeleSimule, sortie_questions, verdicts_juge


@pytest.fixture
def simuler(monkeypatch):
    """Branche un modele simule sur la generation et sur le juge.

    generateur et juge importent `appeler` directement, il faut donc
    remplacer le nom dans chacun des deux modules et non dans app.modele.
    """

    def brancher(reponses_generation, reponses_juge=()):
        modele = ModeleSimule(reponses_generation)
        juge = ModeleSimule(list(reponses_juge))
        monkeypatch.setattr(generateur, "appeler", modele)
        monkeypatch.setattr(module_juge, "appeler", juge)
        return modele, juge

    return brancher


def lancer(nb_items=3, avec_juge=True):
    return generer(
        primitive=Primitive.question,
        gabarit=GABARIT_QUESTION,
        nom_format="Quiz express",
        theme="le cinema",
        public="ado",
        nb_items=nb_items,
        avec_juge=avec_juge,
    )


def test_un_lot_entierement_valide_passe_en_une_tentative(simuler):
    modele, juge = simuler([sortie_questions(3)], [verdicts_juge(3)])

    resultat = lancer()

    assert len(resultat.items) == 3
    assert resultat.rejets == []
    assert resultat.tentatives == 1
    assert len(modele.prompts) == 1


def test_le_prompt_recoit_bien_les_valeurs_demandees(simuler):
    modele, _ = simuler([sortie_questions(3)], [verdicts_juge(3)])

    lancer()

    prompt = modele.prompts[0]
    assert "le cinema" in prompt
    assert "ado" in prompt
    assert "{theme}" not in prompt


def test_le_deterministe_passe_avant_le_juge(simuler):
    # Un lot entierement invalide ne doit declencher aucun appel au juge :
    # c'est le levier de cout principal du projet.
    invalide = json.dumps(
        [{"question": "Q ?", "propositions": ["A", "B"], "bonne_reponse": "A", "anecdote": "x"}] * 3
    )
    _, juge = simuler([invalide, invalide, invalide], [])

    with pytest.raises(GenerationEchouee):
        lancer()

    assert juge.prompts == []


def test_une_tentative_ne_redemande_que_les_items_manquants(simuler):
    # Deux valides sur trois, puis un dernier a la deuxieme passe.
    premier_lot = json.loads(sortie_questions(3))
    premier_lot[2]["bonne_reponse"] = "Absente des propositions"

    modele, _ = simuler(
        [json.dumps(premier_lot), sortie_questions(1, depart=90)],
        [verdicts_juge(2), verdicts_juge(1)],
    )

    resultat = lancer(nb_items=3)

    assert len(resultat.items) == 3
    assert resultat.tentatives == 2
    assert "1 questions" in modele.prompts[1]  # on ne redemande que ce qui manque
    assert any(rejet.niveau is NiveauRejet.deterministe for rejet in resultat.rejets)


def test_un_rejet_du_juge_est_trace_avec_son_niveau(simuler):
    simuler(
        [sortie_questions(2), sortie_questions(2, depart=50)],
        [verdicts_juge(2, accepte=False), verdicts_juge(2)],
    )

    resultat = lancer(nb_items=2)

    assert len(resultat.items) == 2
    assert any(rejet.niveau is NiveauRejet.juge for rejet in resultat.rejets)
    assert any("fait inexact" in rejet.motif for rejet in resultat.rejets)


def test_echoue_apres_trois_tentatives_en_disant_pourquoi(simuler):
    illisible = "Bien sur ! Voici vos questions :"
    simuler([illisible, illisible, illisible], [])

    with pytest.raises(GenerationEchouee) as erreur:
        lancer()

    assert "3 tentatives" in str(erreur.value)
    assert len(erreur.value.rejets) == 3


def test_un_juge_illisible_ne_laisse_rien_passer(simuler):
    # Si le juge repond n'importe quoi, le contenu n'est pas controle :
    # il ne doit surtout pas etre accepte par defaut.
    simuler([sortie_questions(2)] * 3, ["le juge bavarde"] * 3)

    with pytest.raises(GenerationEchouee):
        lancer(nb_items=2)


def test_sans_juge_seul_le_deterministe_s_applique(simuler):
    _, juge = simuler([sortie_questions(3)], [])

    resultat = lancer(avec_juge=False)

    assert len(resultat.items) == 3
    assert juge.prompts == []


def test_le_taux_de_rejet_est_calcule_sur_les_items_produits(simuler):
    lot = json.loads(sortie_questions(4))
    lot[3]["propositions"] = ["A", "B", "C"]  # 3 propositions : rejete
    simuler([json.dumps(lot)], [verdicts_juge(3)])

    resultat = lancer(nb_items=3)

    assert len(resultat.items) == 3
    assert len(resultat.rejets) == 1
    assert resultat.taux_rejet == pytest.approx(0.25)
