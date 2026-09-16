"""Le catalogue de depart : dix formats, trois primitives.

C'est la demonstration de l'idee centrale du projet. Ces dix formats ne
contiennent aucune logique : ils decrivent quand jouer, avec quel materiel,
et quel gabarit de prompt utiliser. Ajouter un onzieme format se fait ici et
en base, sans toucher une ligne de code de generation ou de validation.
"""

from app.gabarits import COMPLEMENT_DINGBATS, GABARIT_PAR_PRIMITIVE
from app.schemas import Materiel, Moment, Primitive

CATALOGUE: list[dict] = [
    {
        "code": "quiz_express",
        "nom": "Quiz express",
        "primitive": Primitive.question,
        "publics": ["ado", "adulte", "general"],
        "moment": Moment.cafe_apero,
        "materiel": Materiel.aucun,
        "regle_animateur": (
            "L'animateur lit la question a voix haute et les quatre propositions. "
            "Les equipes annoncent leur lettre en levant la main. "
            "Un point par bonne reponse, on enchaine sans temps mort."
        ),
        "nb_items_defaut": 10,
    },
    {
        "code": "quiz_minis",
        "nom": "Le quiz des minis",
        "primitive": Primitive.question,
        "publics": ["mini", "junior"],
        "moment": Moment.veillee_enfants,
        "materiel": Materiel.videoprojecteur,
        "regle_animateur": (
            "Question projetee, les enfants repondent tous ensemble a voix haute. "
            "On ne compte pas les points : on applaudit chaque bonne reponse. "
            "L'anecdote sert a relancer entre deux questions."
        ),
        "nb_items_defaut": 8,
    },
    {
        "code": "quiz_thematique",
        "nom": "Quiz a theme",
        "primitive": Primitive.question,
        "publics": ["general"],
        "moment": Moment.soiree_adultes,
        "materiel": Materiel.videoprojecteur,
        "regle_animateur": (
            "Toutes les questions portent sur un meme theme annonce a l'avance. "
            "Les equipes ecrivent leur reponse sur une ardoise, revelation simultanee. "
            "Deux points si la reponse est trouvee sans l'anecdote."
        ),
        "nb_items_defaut": 12,
    },
    {
        "code": "speed_quiz",
        "nom": "Speed quiz par equipes",
        "primitive": Primitive.question,
        "publics": ["ado", "adulte", "general"],
        "moment": Moment.soiree_adultes,
        "materiel": Materiel.videoprojecteur,
        "regle_animateur": (
            "Chronometre de trente secondes par question, la premiere equipe qui "
            "buzze repond. Mauvaise reponse : la main passe a l'equipe suivante. "
            "L'animateur enchaine vite, le rythme fait le jeu."
        ),
        "nb_items_defaut": 15,
    },
    {
        "code": "dingbats",
        "nom": "Dingbats",
        "primitive": Primitive.enigme,
        "publics": ["junior", "ado", "adulte", "general"],
        "moment": Moment.veillee_enfants,
        "materiel": Materiel.videoprojecteur,
        "regle_animateur": (
            "Un rebus visuel est projete, les equipes cherchent l'expression cachee. "
            "L'animateur donne l'indice au bout d'une minute. "
            "La premiere equipe qui trouve marque le point."
        ),
        "nb_items_defaut": 10,
    },
    {
        "code": "personnage_mystere",
        "nom": "Personnage mystere",
        "primitive": Primitive.enigme,
        "publics": ["junior", "ado", "adulte", "general"],
        "moment": Moment.soiree_adultes,
        "materiel": Materiel.aucun,
        "regle_animateur": (
            "L'animateur lit l'enonce, les equipes proposent un nom a tour de role. "
            "Chaque mauvaise proposition fait perdre un point a l'equipe. "
            "L'indice n'est lache que si personne ne trouve."
        ),
        "nb_items_defaut": 8,
    },
    {
        "code": "devinettes",
        "nom": "Devinettes",
        "primitive": Primitive.enigme,
        "publics": ["mini", "junior"],
        "moment": Moment.veillee_enfants,
        "materiel": Materiel.aucun,
        "regle_animateur": (
            "L'animateur lit la devinette, les enfants repondent en levant la main. "
            "L'indice est donne tres vite : l'objectif est qu'ils trouvent. "
            "Aucun score, on enchaine tant que l'attention tient."
        ),
        "nb_items_defaut": 10,
    },
    {
        "code": "anagrammes",
        "nom": "Anagrammes",
        "primitive": Primitive.enigme,
        "publics": ["ado", "adulte", "general"],
        "moment": Moment.cafe_apero,
        "materiel": Materiel.videoprojecteur,
        "regle_animateur": (
            "Les lettres melangees sont projetees, chacun cherche le mot d'origine. "
            "Premier a crier la solution, premier servi. "
            "L'indice donne la categorie du mot."
        ),
        "nb_items_defaut": 12,
    },
    {
        "code": "le_scoop",
        "nom": "Le scoop",
        "primitive": Primitive.vrai_faux,
        "publics": ["junior", "ado", "adulte", "general"],
        "moment": Moment.soiree_adultes,
        "materiel": Materiel.aucun,
        "regle_animateur": (
            "L'animateur annonce l'affirmation sur le ton du journal televise. "
            "Le public se deplace : a gauche si c'est vrai, a droite si c'est faux. "
            "Ceux qui se trompent s'assoient, le dernier debout gagne."
        ),
        "nb_items_defaut": 12,
    },
    {
        "code": "incroyable_vrai",
        "nom": "Incroyable mais vrai",
        "primitive": Primitive.vrai_faux,
        "publics": ["adulte", "general"],
        "moment": Moment.cafe_apero,
        "materiel": Materiel.aucun,
        "regle_animateur": (
            "Chaque table parie sur l'affirmation avant la revelation. "
            "L'animateur lit l'explication a voix haute : c'est elle qui fait le jeu. "
            "Une mise doublee pour les tables qui osent l'affirmation la plus improbable."
        ),
        "nb_items_defaut": 10,
    },
]


def gabarit_du_format(code: str, primitive: Primitive) -> str:
    """Le gabarit de la primitive, plus l'eventuel complement propre au format."""
    gabarit = GABARIT_PAR_PRIMITIVE[primitive]
    if code == "dingbats":
        gabarit += COMPLEMENT_DINGBATS
    return gabarit
