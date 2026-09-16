"""Schemas Pydantic des trois primitives et enumerations du catalogue.

Ces modeles decrivent la forme attendue de la sortie du modele. Ils ne
portent que la structure : longueurs, doublons et coherence interne sont
verifies dans app/validation.py, pour que chaque regle violee produise un
motif de rejet lisible plutot qu'une erreur Pydantic brute.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Primitive(str, Enum):
    """Les trois formes de contenu que le modele sait produire."""

    question = "question"
    enigme = "enigme"
    vrai_faux = "vrai_faux"


class Public(str, Enum):
    mini = "mini"
    junior = "junior"
    ado = "ado"
    adulte = "adulte"
    general = "general"


class Moment(str, Enum):
    cafe_apero = "cafe_apero"
    veillee_enfants = "veillee_enfants"
    soiree_adultes = "soiree_adultes"
    grand_jeu = "grand_jeu"


class Materiel(str, Enum):
    aucun = "aucun"
    videoprojecteur = "videoprojecteur"
    sono = "sono"
    accessoires = "accessoires"


class NiveauRejet(str, Enum):
    """Quel des deux niveaux de validation a rejete l'item."""

    deterministe = "deterministe"
    juge = "juge"


class _Item(BaseModel):
    # str_strip_whitespace : le modele ajoute regulierement des espaces
    # de bordure, ils ne doivent pas fausser les comparaisons de longueur.
    # extra="forbid" : un champ en trop signale un modele qui a improvise,
    # et on prefere le savoir plutot que de l'ignorer silencieusement.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Question(_Item):
    question: str = Field(min_length=1)
    propositions: list[str]
    bonne_reponse: str = Field(min_length=1)
    anecdote: str = Field(min_length=1)


class Enigme(_Item):
    enonce: str = Field(min_length=1)
    solution: str = Field(min_length=1)
    indice: str = Field(min_length=1)


class VraiFaux(_Item):
    affirmation: str = Field(min_length=1)
    # Volontairement une chaine et non une enumeration : un verdict hors
    # champ doit produire un motif de rejet explicite, pas une ValidationError.
    verdict: str = Field(min_length=1)
    explication: str = Field(min_length=1)


SCHEMA_PAR_PRIMITIVE: dict[Primitive, type[_Item]] = {
    Primitive.question: Question,
    Primitive.enigme: Enigme,
    Primitive.vrai_faux: VraiFaux,
}
