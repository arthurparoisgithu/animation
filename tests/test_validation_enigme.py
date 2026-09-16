"""La regle qui compte ici : une enigme ne doit pas contenir sa propre solution."""

import pytest

from app.schemas import Enigme, Primitive
from app.validation import valider_enigme, valider_lot


def enigme_valide(**remplacements) -> Enigme:
    base = {
        "enonce": "Je grandis de quatre millimetres par an et je culmine au Nepal.",
        "solution": "Everest",
        "indice": "Un sommet himalayen.",
    }
    return Enigme(**{**base, **remplacements})


def test_une_enigme_correcte_ne_produit_aucun_motif():
    assert valider_enigme(enigme_valide()) == []


def test_refuse_une_solution_presente_dans_l_enonce():
    motifs = valider_enigme(enigme_valide(enonce="L'Everest culmine au Nepal."))
    assert any("apparait dans l'enonce" in motif for motif in motifs)


def test_refuse_une_solution_presente_dans_l_enonce_sous_une_variante():
    # "Everests" au pluriel reste la solution : le rejet doit avoir lieu.
    motifs = valider_enigme(enigme_valide(enonce="Les everests du monde sont rares."))
    assert any("apparait dans l'enonce" in motif for motif in motifs)


def test_refuse_une_solution_presente_dans_l_indice():
    motifs = valider_enigme(enigme_valide(indice="C'est l'Everest, evidemment."))
    assert any("apparait dans l'indice" in motif for motif in motifs)


def test_refuse_un_indice_identique_a_la_solution():
    motifs = valider_enigme(enigme_valide(indice="everest"))
    assert motifs  # detecte par la regle de l'indice ou celle de l'identite


def test_ne_rejette_pas_sur_une_coincidence_de_sous_chaine():
    # "or" est dans "corps", mais ce n'est pas la solution presente.
    assert valider_enigme(
        Enigme(
            enonce="Ce metal a donne son nom a une couleur et fait mal au corps quand on le porte.",
            solution="or",
            indice="On le trouve en lingots.",
        )
    ) == []


def test_refuse_une_solution_de_plus_de_deux_mots():
    motifs = valider_enigme(
        enigme_valide(solution="le mont Everest du Nepal", enonce="Je culmine tres haut.")
    )
    assert any("2 maximum" in motif for motif in motifs)


def test_refuse_un_enonce_trop_long():
    motifs = valider_enigme(enigme_valide(enonce="E" * 201))
    assert any("200 maximum" in motif for motif in motifs)


def test_accepte_un_enonce_a_la_limite_exacte():
    assert valider_enigme(enigme_valide(enonce="E" * 200)) == []


SORTIE_SOLUTION_VIDE = [{"enonce": "Un enonce.", "solution": "", "indice": "Un indice."}]
SORTIE_INDICE_MANQUANT = [{"enonce": "Un enonce.", "solution": "Everest"}]


@pytest.mark.parametrize("sortie", [SORTIE_SOLUTION_VIDE, SORTIE_INDICE_MANQUANT])
def test_les_sorties_cassees_sont_rejetees(sortie):
    resultat = valider_lot(Primitive.enigme, sortie)
    assert resultat.items == []
    assert resultat.rejets
