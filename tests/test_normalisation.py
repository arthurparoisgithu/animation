"""Tests de la fonction partagee par toute la validation.

Si normaliser se trompe, toutes les comparaisons du projet se trompent.
C'est la premiere chose a couvrir.
"""

import pytest

from app.normalisation import cle, contient, identiques, normaliser


@pytest.mark.parametrize(
    "entree, attendu",
    [
        ("Everest", "everest"),
        ("EVEREST", "everest"),
        ("  Everest  ", "everest"),
        ("l'Everest", "l everest"),
        ("Élément", "element"),
        ("Ça, où, naïf, cœur", "ca ou naif c ur"),
        ("Le   Mont    Blanc", "le mont blanc"),
        ("Réponse : 42 !", "reponse 42"),
        ("", ""),
        ("   ", ""),
        (None, ""),
        ("!!!???", ""),
    ],
)
def test_normaliser(entree, attendu):
    assert normaliser(entree) == attendu


def test_normaliser_retire_les_emojis():
    # Les dingbats contiennent des emojis : on ne veut pas les comparer.
    assert normaliser("🍎 + 🥧 = tarte") == "tarte"


def test_identiques_ignore_casse_accents_et_ponctuation():
    assert identiques("L'Everest !", "  everest ")
    assert not identiques("Everest", "K2")


@pytest.mark.parametrize(
    "texte, terme",
    [
        ("Le sommet est l'Everest", "everest"),
        ("Les everests du monde", "Everest"),  # variante au pluriel
        ("C'est le mont Blanc", "Mont Blanc"),  # terme de deux mots
        ("Réponse : ÉLÉPHANT", "elephant"),  # accents et casse
    ],
)
def test_contient_detecte_le_terme(texte, terme):
    assert contient(texte, terme)


@pytest.mark.parametrize(
    "texte, terme",
    [
        # Le piege du sous-chaine : "or" est dans "corps" en sous-chaine,
        # mais ce n'est pas le meme mot. C'est la raison d'etre de contient().
        ("Il a mal au corps", "or"),
        ("Le chateau est grand", "chat"),
        ("Une pomme", "poire"),
        ("", "solution"),
        ("un texte", ""),
        ("court", "un terme bien plus long que le texte"),
    ],
)
def test_contient_ne_declenche_pas_a_tort(texte, terme):
    assert not contient(texte, terme)


@pytest.mark.parametrize(
    "entree, attendu",
    [
        ("L'Everest", "everest"),
        ("Le Mont Blanc", "mont blanc"),
        ("Un chat", "chat"),
        ("Des pommes", "pommes"),
        ("Everest", "everest"),
        # Une reponse reduite a un determinant reste telle quelle, sinon
        # elle s'egaliserait avec n'importe quelle autre reponse vide.
        ("Les", "les"),
        ("", ""),
    ],
)
def test_cle_retire_les_determinants_de_tete(entree, attendu):
    assert cle(entree) == attendu


def test_deux_reponses_ecrites_differemment_ont_la_meme_cle():
    assert cle("Le Mont Blanc") == cle("mont blanc") == cle("MONT-BLANC")
