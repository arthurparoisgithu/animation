"""Le catalogue est de la donnee : ces tests verifient qu'elle est coherente."""

from app.catalogue import CATALOGUE, gabarit_du_format
from app.schemas import Materiel, Moment, Primitive, Public


def test_dix_formats_au_depart():
    assert len(CATALOGUE) == 10


def test_les_codes_sont_uniques():
    codes = [format_jeu["code"] for format_jeu in CATALOGUE]
    assert len(codes) == len(set(codes))


def test_les_dix_formats_ne_couvrent_que_trois_primitives():
    # C'est l'idee centrale du projet : vingt jeux, trois formes de contenu.
    primitives = {format_jeu["primitive"] for format_jeu in CATALOGUE}
    assert primitives == set(Primitive)


def test_chaque_format_est_coherent():
    publics_connus = {public.value for public in Public}
    for format_jeu in CATALOGUE:
        assert format_jeu["publics"], format_jeu["code"]
        assert set(format_jeu["publics"]) <= publics_connus, format_jeu["code"]
        assert isinstance(format_jeu["moment"], Moment), format_jeu["code"]
        assert isinstance(format_jeu["materiel"], Materiel), format_jeu["code"]
        assert format_jeu["nb_items_defaut"] > 0, format_jeu["code"]
        assert len(format_jeu["regle_animateur"]) > 50, format_jeu["code"]
        assert gabarit_du_format(format_jeu["code"], format_jeu["primitive"])
