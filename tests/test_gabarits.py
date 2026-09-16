"""Le piege des accolades : les gabarits contiennent du JSON d'exemple."""

import pytest

from app.catalogue import CATALOGUE, gabarit_du_format
from app.gabarits import GABARIT_PAR_PRIMITIVE, remplir_gabarit
from app.schemas import Primitive


def test_remplit_les_placeholders_connus():
    rendu = remplir_gabarit(
        "Genere {nb_items} items sur {theme} pour un public {public}.",
        nb_items=10,
        theme="le cinema",
        public="ado",
    )
    assert rendu == "Genere 10 items sur le cinema pour un public ado."


def test_laisse_intactes_les_accolades_du_json_d_exemple():
    # Un str.format() classique leverait KeyError ici : c'est la raison
    # pour laquelle remplir_gabarit existe.
    gabarit = "Reponds par un tableau d'objets {question, propositions} sur {theme}."
    rendu = remplir_gabarit(gabarit, theme="le sport")
    assert "{question, propositions}" in rendu
    assert "le sport" in rendu


def test_laisse_un_placeholder_connu_sans_valeur_tel_quel():
    assert remplir_gabarit("Theme : {theme}, format : {nom_format}", theme="X") == (
        "Theme : X, format : {nom_format}"
    )


@pytest.mark.parametrize("primitive", list(Primitive))
def test_chaque_primitive_a_un_gabarit_qui_se_remplit(primitive):
    rendu = remplir_gabarit(
        GABARIT_PAR_PRIMITIVE[primitive],
        theme="le cinema",
        public="ado",
        nb_items=10,
        nom_format="Dingbats",
    )
    for placeholder in ("{theme}", "{public}", "{nb_items}", "{nom_format}"):
        assert placeholder not in rendu


def test_le_gabarit_des_dingbats_precise_que_l_enonce_est_affichable():
    format_jeu = next(f for f in CATALOGUE if f["code"] == "dingbats")
    gabarit = gabarit_du_format(format_jeu["code"], format_jeu["primitive"])
    assert "emojis" in gabarit
