"""Gabarits de prompt, un par primitive.

Ces textes sont la source de verite du seed : ils sont copies dans
format_jeu.gabarit_prompt en base. Le code ne fait ensuite qu'y substituer
les placeholders. Ajouter un format, c'est une ligne en base et un gabarit,
zero ligne de Python.
"""

import re

from app.schemas import Primitive

GABARIT_QUESTION = """Tu génères {nb_items} questions pour un jeu d'animation en club de vacances.
Thème : {theme}. Public : {public}.
Contraintes : exactement 4 propositions par question, une seule correcte, les trois autres plausibles mais indiscutablement fausses. Question de 140 caractères maximum, propositions de 60 caractères maximum. Pas de « toutes ces réponses » ni « aucune de ces réponses ». Faits vérifiables uniquement, aucune question d'actualité de moins de deux ans. Ajoute une anecdote d'une phrase pour que l'animateur ait quelque chose à dire après la réponse.
Réponds uniquement par un tableau JSON d'objets {question, propositions, bonne_reponse, anecdote}, sans texte autour et sans balises de code."""

GABARIT_ENIGME = """Tu génères {nb_items} énigmes de type {nom_format} pour un jeu d'animation.
Thème : {theme}. Public : {public}.
Contraintes : une seule solution possible, formulée en un ou deux mots. La solution ne doit apparaître ni dans l'énoncé ni dans l'indice, sous aucune forme ni variante. L'indice doit réduire la difficulté sans donner la réponse. Énoncé de 200 caractères maximum.
Réponds uniquement par un tableau JSON d'objets {enonce, solution, indice}, sans texte autour et sans balises de code."""

GABARIT_VRAI_FAUX = """Tu génères {nb_items} affirmations à trancher pour un jeu d'animation.
Thème : {theme}. Public : {public}.
Contraintes : environ la moitié de vraies. Chaque affirmation doit être surprenante mais vérifiable dans une encyclopédie généraliste. Les mots « vrai » et « faux » ne doivent pas figurer dans l'affirmation. Explication de 300 caractères maximum.
Réponds uniquement par un tableau JSON d'objets {affirmation, verdict, explication}, verdict valant exactement "vrai" ou "faux", sans texte autour et sans balises de code."""

# Precision propre aux dingbats : l'enonce doit etre affichable, pas dessine.
COMPLEMENT_DINGBATS = """
Précision : l'énoncé est un rébus visuel composé d'emojis et de jeux typographiques directement affichables en HTML (positions, répétitions, barres, exposants). Ce n'est jamais une image à dessiner ni une description d'image."""

# Precision propre a l'escape game : les enigmes ne sont pas independantes.
# Tout le format tient dans ce paragraphe — c'est le sujet de la demonstration.
COMPLEMENT_ESCAPE_GAME = """
Précision : les énigmes forment une progression unique et se lisent dans l'ordre. Elles jalonnent une même histoire liée au thème, de la plus accessible à la plus difficile, chacune ouvrant l'étape suivante. L'énoncé peut situer l'étape dans le récit en une phrase courte avant de poser l'énigme, sans dépasser la limite de caractères."""

GABARIT_PAR_PRIMITIVE = {
    Primitive.question: GABARIT_QUESTION,
    Primitive.enigme: GABARIT_ENIGME,
    Primitive.vrai_faux: GABARIT_VRAI_FAUX,
}

# Le complement propre a un format, quand la primitive seule ne suffit pas.
# Un dictionnaire et non une suite de « if » : ajouter un format precise ici
# une entree, jamais une branche. Une branche par format, c'est le glissement
# qui finit par ramener la logique de chaque jeu dans le code.
COMPLEMENT_PAR_FORMAT: dict[str, str] = {
    "dingbats": COMPLEMENT_DINGBATS,
    "escape_game": COMPLEMENT_ESCAPE_GAME,
}

# Les placeholders reconnus. Tout ce qui ressemble a {autre chose} est laisse
# tel quel : les gabarits contiennent des accolades JSON d'exemple, et un
# str.format() classique s'y casserait les dents.
_PLACEHOLDER = re.compile(r"\{(theme|public|nb_items|nom_format|items)\}")


def remplir_gabarit(gabarit: str, **valeurs: object) -> str:
    """Substitue les placeholders connus, sans toucher au reste du texte."""

    def remplacer(correspondance: re.Match[str]) -> str:
        cle = correspondance.group(1)
        if cle not in valeurs:
            return correspondance.group(0)
        return str(valeurs[cle])

    return _PLACEHOLDER.sub(remplacer, gabarit)
