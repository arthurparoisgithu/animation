"""Configuration du projet, lue dans l'environnement ou dans .env.

pydantic-settings lit les variables d'environnement et les valide comme
n'importe quel modele Pydantic. La cle d'API n'apparait donc jamais en dur
dans le code : elle arrive par .env, qui est exclu du depot.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Reglages(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""

    # Haiku 4.5 pour la generation et pour le juge : le moins cher de la gamme,
    # suffisant sur une sortie JSON fortement contrainte.
    modele_generation: str = "claude-haiku-4-5-20251001"
    modele_juge: str = "claude-haiku-4-5-20251001"

    database_url: str = "postgresql+psycopg://animation:animation@localhost:5432/animation"

    # D'ou viennent les reponses du modele :
    #   api            appel reel, facture ;
    #   enregistrement appel reel, puis sauvegarde dans fixtures/ ;
    #   rejeu          relecture de fixtures/, aucun appel, aucun cout.
    # Une demo en ligne tourne en rejeu : elle montre de vraies sorties de
    # modele sans que ma cle paie pour les visiteurs.
    mode_modele: str = "api"

    # Nombre de passes de generation avant d'abandonner (cahier des charges : 3).
    max_tentatives: int = 3

    # Si renseigne, la generation reelle exige ce code. La demo publique peut
    # alors afficher les jeux deja en base sans que ma cle paie pour les visiteurs.
    code_generation: str = ""


@lru_cache
def reglages() -> Reglages:
    """Instance unique, construite au premier appel puis mise en cache."""
    return Reglages()
