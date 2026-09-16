"""Une regle, un test, plus des sorties de modele volontairement cassees."""

import pytest

from app.schemas import Primitive
from app.validation import valider_lot, valider_question
from app.schemas import Question


def question_valide(**remplacements) -> Question:
    """Un item correct, dont chaque test casse un seul aspect."""
    base = {
        "question": "Quel est le plus haut sommet du monde ?",
        "propositions": ["L'Everest", "Le K2", "Le Mont Blanc", "Le Kilimandjaro"],
        "bonne_reponse": "L'Everest",
        "anecdote": "Il grandit d'environ 4 millimetres par an.",
    }
    return Question(**{**base, **remplacements})


def test_une_question_correcte_ne_produit_aucun_motif():
    assert valider_question(question_valide()) == []


def test_refuse_un_nombre_de_propositions_different_de_quatre():
    motifs = valider_question(question_valide(propositions=["A", "B", "C"]))
    assert any("exactement 4" in motif for motif in motifs)


def test_refuse_un_doublon_de_proposition_apres_normalisation():
    # Le modele produit regulierement la meme proposition a la casse pres.
    motifs = valider_question(
        question_valide(propositions=["L'Everest", "l everest", "Le K2", "Le Mont Blanc"])
    )
    assert any("doublon" in motif for motif in motifs)


def test_refuse_une_bonne_reponse_absente_des_propositions():
    motifs = valider_question(question_valide(bonne_reponse="L'Annapurna"))
    assert any("ne figure pas" in motif for motif in motifs)


def test_accepte_une_bonne_reponse_ecrite_differemment():
    # "everest" et "L'Everest" sont la meme reponse : la normalisation doit
    # eviter un rejet inutile, qui couterait une regeneration.
    assert valider_question(question_valide(bonne_reponse="everest")) == []


def test_refuse_une_bonne_reponse_presente_deux_fois():
    motifs = valider_question(
        question_valide(
            propositions=["L'Everest", "Everest", "Le K2", "Le Mont Blanc"],
            bonne_reponse="L'Everest",
        )
    )
    assert any("figure 2 fois" in motif for motif in motifs)


def test_refuse_une_question_trop_longue():
    motifs = valider_question(question_valide(question="Q" * 141))
    assert any("140 maximum" in motif for motif in motifs)


def test_accepte_une_question_a_la_limite_exacte():
    assert valider_question(question_valide(question="Q" * 140)) == []


def test_refuse_une_proposition_trop_longue():
    longue = "P" * 61
    motifs = valider_question(
        question_valide(
            propositions=[longue, "Le K2", "Le Mont Blanc", "Le Kilimandjaro"],
            bonne_reponse="Le K2",
        )
    )
    assert any("60 maximum" in motif for motif in motifs)


def test_refuse_une_proposition_vide():
    motifs = valider_question(
        question_valide(
            propositions=["L'Everest", "   ", "Le Mont Blanc", "Le Kilimandjaro"]
        )
    )
    assert any("vide" in motif for motif in motifs)


@pytest.mark.parametrize(
    "formule", ["Toutes ces reponses", "Aucune de ces reponses", "Les deux"]
)
def test_refuse_les_formules_injouables(formule):
    motifs = valider_question(
        question_valide(
            propositions=["L'Everest", "Le K2", "Le Mont Blanc", formule],
            bonne_reponse="L'Everest",
        )
    )
    assert any("formule interdite" in motif for motif in motifs)


# --- Sorties de modele volontairement cassees, ecrites en dur ---

SORTIE_CHAMP_MANQUANT = [
    {
        "question": "Quelle est la capitale de l'Australie ?",
        "propositions": ["Canberra", "Sydney", "Melbourne", "Perth"],
        "bonne_reponse": "Canberra",
        # anecdote absente
    }
]

SORTIE_CHAMP_EN_TROP = [
    {
        "question": "Quelle est la capitale de l'Australie ?",
        "propositions": ["Canberra", "Sydney", "Melbourne", "Perth"],
        "bonne_reponse": "Canberra",
        "anecdote": "Elle a ete choisie comme compromis entre Sydney et Melbourne.",
        "difficulte": "moyenne",
    }
]

SORTIE_MAUVAIS_TYPE = [
    {
        "question": "Quelle est la capitale de l'Australie ?",
        "propositions": "Canberra, Sydney, Melbourne, Perth",
        "bonne_reponse": "Canberra",
        "anecdote": "Une anecdote.",
    }
]

SORTIE_PAS_UN_OBJET = ["Canberra"]


@pytest.mark.parametrize(
    "sortie",
    [
        SORTIE_CHAMP_MANQUANT,
        SORTIE_CHAMP_EN_TROP,
        SORTIE_MAUVAIS_TYPE,
        SORTIE_PAS_UN_OBJET,
    ],
)
def test_les_sorties_cassees_sont_rejetees_et_n_entrent_pas_en_base(sortie):
    resultat = valider_lot(Primitive.question, sortie)
    assert resultat.items == []
    assert len(resultat.rejets) == 1
    assert resultat.rejets[0].index == 0


def test_le_lot_separe_les_items_valides_des_rejetes():
    bon = {
        "question": "Quelle est la capitale de l'Australie ?",
        "propositions": ["Canberra", "Sydney", "Melbourne", "Perth"],
        "bonne_reponse": "Canberra",
        "anecdote": "Elle a ete choisie comme compromis entre Sydney et Melbourne.",
    }
    mauvais = {**bon, "bonne_reponse": "Brisbane"}

    resultat = valider_lot(Primitive.question, [bon, mauvais])

    assert len(resultat.items) == 1
    assert len(resultat.rejets) == 1
    assert resultat.rejets[0].index == 1
    assert not resultat.est_valide
