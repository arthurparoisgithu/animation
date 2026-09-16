"""Regles item par item, plus la seule regle de lot du projet."""

import pytest

from app.schemas import Primitive, VraiFaux
from app.validation import valider_lot, valider_repartition, valider_vrai_faux


def affirmation_valide(**remplacements) -> VraiFaux:
    base = {
        "affirmation": "Le miel ne se perime jamais.",
        "verdict": "vrai",
        "explication": "Son acidite et sa faible teneur en eau empechent les bacteries de s'y developper.",
    }
    return VraiFaux(**{**base, **remplacements})


def test_une_affirmation_correcte_ne_produit_aucun_motif():
    assert valider_vrai_faux(affirmation_valide()) == []


@pytest.mark.parametrize("verdict", ["vrai", "faux", "Vrai", "FAUX", " vrai "])
def test_accepte_les_verdicts_a_la_casse_pres(verdict):
    assert valider_vrai_faux(affirmation_valide(verdict=verdict)) == []


@pytest.mark.parametrize("verdict", ["peut-etre", "true", "oui", "1"])
def test_refuse_un_verdict_hors_champ(verdict):
    motifs = valider_vrai_faux(affirmation_valide(verdict=verdict))
    assert any("hors de" in motif for motif in motifs)


@pytest.mark.parametrize(
    "affirmation",
    [
        "Il est vrai que le miel ne se perime jamais.",
        "C'est faux : le miel se perime.",
        "VRAI ou pas, le miel se conserve.",
    ],
)
def test_refuse_une_affirmation_qui_donne_sa_reponse(affirmation):
    motifs = valider_vrai_faux(affirmation_valide(affirmation=affirmation))
    assert any("figure dans l'affirmation" in motif for motif in motifs)


def test_refuse_une_explication_trop_longue():
    motifs = valider_vrai_faux(affirmation_valide(explication="E" * 301))
    assert any("300 maximum" in motif for motif in motifs)


def test_accepte_une_explication_a_la_limite_exacte():
    assert valider_vrai_faux(affirmation_valide(explication="E" * 300)) == []


def lot(nb_vraies: int, nb_fausses: int) -> list[VraiFaux]:
    return [affirmation_valide(verdict="vrai") for _ in range(nb_vraies)] + [
        affirmation_valide(verdict="faux") for _ in range(nb_fausses)
    ]


@pytest.mark.parametrize("vraies, fausses", [(5, 5), (3, 7), (7, 3), (4, 6)])
def test_accepte_une_repartition_equilibree(vraies, fausses):
    assert valider_repartition(lot(vraies, fausses)) == []


@pytest.mark.parametrize("vraies, fausses", [(10, 0), (0, 10), (9, 1), (2, 8)])
def test_refuse_une_repartition_desequilibree(vraies, fausses):
    assert valider_repartition(lot(vraies, fausses))


def test_ne_juge_pas_la_repartition_d_un_lot_d_un_seul_item():
    # Avec un seul item la part vaut 0 % ou 100 % : la regle n'a pas de sens.
    assert valider_repartition(lot(1, 0)) == []


def test_la_repartition_est_verifiee_sur_le_lot_complet():
    tout_vrai = [
        {"affirmation": f"Affirmation numero {i}.", "verdict": "vrai", "explication": "Parce que."}
        for i in range(4)
    ]
    resultat = valider_lot(Primitive.vrai_faux, tout_vrai)

    assert len(resultat.items) == 4  # chaque item est correct pris isolement
    assert any(rejet.index is None for rejet in resultat.rejets)  # mais le lot ne l'est pas
    assert not resultat.est_valide


def test_la_repartition_peut_etre_desactivee_pour_une_passe_intermediaire():
    tout_vrai = [
        {"affirmation": f"Affirmation numero {i}.", "verdict": "vrai", "explication": "Parce que."}
        for i in range(4)
    ]
    resultat = valider_lot(Primitive.vrai_faux, tout_vrai, verifier_repartition=False)
    assert resultat.est_valide
