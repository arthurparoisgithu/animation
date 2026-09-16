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


# --- Alignement avec le cahier des charges ---

def _table_du_cahier_des_charges() -> dict[str, dict]:
    """Relit la table du catalogue directement dans CLAUDE.md.

    Ce test garde le code et la specification alignes. Il a deja servi :
    trois noms affiches a l'animateur avaient perdu leurs accents en cours
    de route (« Quiz a theme » au lieu de « Quiz à thème »), ce qui se
    voyait a l'ecran sans qu'aucun test ne s'en plaigne.
    """
    import pathlib

    texte = pathlib.Path("CLAUDE.md").read_text(encoding="utf-8")
    bloc = texte.split("## Catalogue de départ")[1].split("## Gabarits")[0]

    table = {}
    for ligne in bloc.splitlines():
        if not ligne.startswith("| `"):
            continue
        cellules = [c.strip() for c in ligne.strip("|").split("|")]
        table[cellules[0].strip("`")] = {
            "nom": cellules[1],
            "primitive": cellules[2],
            "publics": [p.strip() for p in cellules[3].split(",")],
            "moments": [m.strip() for m in cellules[4].split(",")],
            "materiel": cellules[5],
        }
    return table


def test_le_catalogue_du_code_correspond_au_cahier_des_charges():
    attendu = _table_du_cahier_des_charges()
    reel = {format_jeu["code"]: format_jeu for format_jeu in CATALOGUE}

    assert set(attendu) == set(reel)

    for code, spec in attendu.items():
        format_jeu = reel[code]
        assert format_jeu["nom"] == spec["nom"], code
        assert format_jeu["primitive"].value == spec["primitive"], code
        assert format_jeu["publics"] == spec["publics"], code
        assert format_jeu["materiel"].value == spec["materiel"], code
        # Deux formats se jouent a plusieurs moments dans la table ;
        # le catalogue en retient un, qui doit figurer parmi eux.
        assert format_jeu["moment"].value in spec["moments"], code


def test_les_noms_affiches_sont_en_francais_accentue():
    # Garde-fou simple : un nom ou une regle sans accent trahit du texte
    # ecrit a la va-vite, et ca se voit a l'ecran.
    accentues = "àâäéèêëîïôöùûüç"
    corpus = " ".join(
        f["nom"] + " " + f["regle_animateur"] for f in CATALOGUE
    ).lower()
    assert any(lettre in corpus for lettre in accentues)
    # Fautes precises deja rencontrees.
    for faute in ("Quiz a theme", "Personnage mystere", "Speed quiz par equipes"):
        assert faute not in corpus.title() and faute.lower() not in corpus
