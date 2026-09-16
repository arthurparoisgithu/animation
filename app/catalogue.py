"""Le catalogue de depart : dix formats, trois primitives.

C'est la demonstration de l'idee centrale du projet. Ces dix formats ne
contiennent aucune logique : ils decrivent quand jouer, avec quel materiel,
et quel gabarit de prompt utiliser. Ajouter un onzieme format se fait ici et
en base, sans toucher une ligne de code de generation ou de validation.
"""

from app.gabarits import COMPLEMENT_PAR_FORMAT, GABARIT_PAR_PRIMITIVE
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
            "L'animateur lit la question à voix haute et les quatre propositions. "
            "Les équipes annoncent leur lettre en levant la main. "
            "Un point par bonne réponse, on enchaîne sans temps mort."
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
            "Question projetée, les enfants répondent tous ensemble à voix haute. "
            "On ne compte pas les points : on applaudit chaque bonne réponse. "
            "L'anecdote sert à relancer entre deux questions."
        ),
        "nb_items_defaut": 8,
    },
    {
        "code": "quiz_thematique",
        "nom": "Quiz à thème",
        "primitive": Primitive.question,
        "publics": ["general"],
        "moment": Moment.soiree_adultes,
        "materiel": Materiel.videoprojecteur,
        "regle_animateur": (
            "Toutes les questions portent sur un même thème annoncé à l'avance. "
            "Les équipes écrivent leur réponse sur une ardoise, révélation simultanée. "
            "Deux points si la réponse est trouvée sans l'anecdote."
        ),
        "nb_items_defaut": 12,
    },
    {
        "code": "speed_quiz",
        "nom": "Speed quiz par équipes",
        "primitive": Primitive.question,
        "publics": ["ado", "adulte", "general"],
        "moment": Moment.soiree_adultes,
        "materiel": Materiel.videoprojecteur,
        "regle_animateur": (
            "Chronomètre de trente secondes par question, la première équipe qui "
            "buzze répond. Mauvaise réponse : la main passe à l'équipe suivante. "
            "L'animateur enchaîne vite, le rythme fait le jeu."
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
            "Un rébus visuel est projeté, les équipes cherchent l'expression cachée. "
            "L'animateur donne l'indice au bout d'une minute. "
            "La première équipe qui trouve marque le point."
        ),
        "nb_items_defaut": 10,
    },
    {
        "code": "personnage_mystere",
        "nom": "Personnage mystère",
        "primitive": Primitive.enigme,
        "publics": ["junior", "ado", "adulte", "general"],
        "moment": Moment.soiree_adultes,
        "materiel": Materiel.aucun,
        "regle_animateur": (
            "L'animateur lit l'énoncé, les équipes proposent un nom à tour de rôle. "
            "Chaque mauvaise proposition fait perdre un point à l'équipe. "
            "L'indice n'est lâché que si personne ne trouve."
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
            "L'animateur lit la devinette, les enfants répondent en levant la main. "
            "L'indice est donné très vite : l'objectif est qu'ils trouvent. "
            "Aucun score, on enchaîne tant que l'attention tient."
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
            "Les lettres mélangées sont projetées, chacun cherche le mot d'origine. "
            "Premier à crier la solution, premier servi. "
            "L'indice donne la catégorie du mot."
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
            "L'animateur annonce l'affirmation sur le ton du journal télévisé. "
            "Le public se déplace : à gauche si c'est vrai, à droite si c'est faux. "
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
            "Chaque table parie sur l'affirmation avant la révélation. "
            "L'animateur lit l'explication à voix haute : c'est elle qui fait le jeu. "
            "Une mise doublée pour les tables qui osent l'affirmation la plus improbable."
        ),
        "nb_items_defaut": 10,
    },
    {
        "code": "escape_game",
        "nom": "Escape game",
        "primitive": Primitive.enigme,
        "publics": ["junior", "ado", "adulte", "general"],
        "moment": Moment.grand_jeu,
        "materiel": Materiel.accessoires,
        "regle_animateur": (
            "Les énigmes se résolvent dans l'ordre : chacune ouvre l'étape suivante. "
            "Quarante-cinq minutes pour toute la chaîne, l'animateur lâche l'indice "
            "quand une équipe bloque plus de cinq minutes sur la même étape."
        ),
        "nb_items_defaut": 6,
    },
]


def gabarit_du_format(code: str, primitive: Primitive) -> str:
    """Le gabarit de la primitive, plus l'eventuel complement propre au format."""
    return GABARIT_PAR_PRIMITIVE[primitive] + COMPLEMENT_PAR_FORMAT.get(code, "")
