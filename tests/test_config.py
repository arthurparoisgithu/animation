"""La configuration doit accepter ce que l'hebergeur fournit reellement."""

import pytest

from app.config import Reglages


@pytest.mark.parametrize(
    "fournie, attendue",
    [
        # Ce que Fly.io, Render et Heroku creent tout seuls.
        (
            "postgres://u:p@interne.flycast:5432/animation",
            "postgresql+psycopg://u:p@interne.flycast:5432/animation",
        ),
        (
            "postgresql://u:p@localhost:5432/animation",
            "postgresql+psycopg://u:p@localhost:5432/animation",
        ),
        # Deja explicite : on n'y touche pas.
        (
            "postgresql+psycopg://u:p@localhost:5432/animation",
            "postgresql+psycopg://u:p@localhost:5432/animation",
        ),
    ],
)
def test_le_pilote_est_ajoute_a_l_url_de_l_hebergeur(fournie, attendue):
    assert Reglages(database_url=fournie).database_url == attendue


def test_le_mot_de_passe_survit_a_la_reecriture():
    # Une reecriture naive sur "postgres" casserait un mot de passe
    # contenant ce mot.
    url = "postgres://animation:postgres_secret@hote:5432/base"
    reecrite = Reglages(database_url=url).database_url
    assert reecrite == "postgresql+psycopg://animation:postgres_secret@hote:5432/base"


def test_le_mode_par_defaut_est_l_appel_reel():
    assert Reglages().mode_modele == "api"


def test_un_mot_de_passe_contenant_un_pourcent_passe_intact():
    # Les hebergeurs generent des mots de passe aleatoires qui contiennent
    # des « % » (encodes %25 dans l'URI). Ce caractere a deja casse la
    # migration une fois, en etant pris pour une interpolation configparser.
    url = "postgres://animation:anim%25pass@interne.flycast:5432/animation"
    assert Reglages(database_url=url).database_url == (
        "postgresql+psycopg://animation:anim%25pass@interne.flycast:5432/animation"
    )
