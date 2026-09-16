"""Gabarits de prompt, un par primitive.

Ces textes sont la source de verite du seed : ils sont copies dans
format_jeu.gabarit_prompt en base. Le code ne fait ensuite qu'y substituer
les placeholders. Ajouter un format, c'est une ligne en base et un gabarit,
zero ligne de Python.
"""

import re

from app.schemas import Primitive

GABARIT_QUESTION = """Tu generes {nb_items} questions pour un jeu d'animation en club de vacances.
Theme : {theme}. Public : {public}.
Contraintes : exactement 4 propositions par question, une seule correcte, les trois autres plausibles mais indiscutablement fausses. Question de 140 caracteres maximum, propositions de 60 caracteres maximum. Pas de « toutes ces reponses » ni « aucune de ces reponses ». Faits verifiables uniquement, aucune question d'actualite de moins de deux ans. Ajoute une anecdote d'une phrase pour que l'animateur ait quelque chose a dire apres la reponse.
Reponds uniquement par un tableau JSON d'objets {question, propositions, bonne_reponse, anecdote}, sans texte autour et sans balises de code."""

GABARIT_ENIGME = """Tu generes {nb_items} enigmes de type {nom_format} pour un jeu d'animation.
Theme : {theme}. Public : {public}.
Contraintes : une seule solution possible, formulee en un ou deux mots. La solution ne doit apparaitre ni dans l'enonce ni dans l'indice, sous aucune forme ni variante. L'indice doit reduire la difficulte sans donner la reponse. Enonce de 200 caracteres maximum.
Reponds uniquement par un tableau JSON d'objets {enonce, solution, indice}, sans texte autour et sans balises de code."""

GABARIT_VRAI_FAUX = """Tu generes {nb_items} affirmations a trancher pour un jeu d'animation.
Theme : {theme}. Public : {public}.
Contraintes : environ la moitie de vraies. Chaque affirmation doit etre surprenante mais verifiable dans une encyclopedie generaliste. Les mots « vrai » et « faux » ne doivent pas figurer dans l'affirmation. Explication de 300 caracteres maximum.
Reponds uniquement par un tableau JSON d'objets {affirmation, verdict, explication}, verdict valant exactement "vrai" ou "faux", sans texte autour et sans balises de code."""

# Precision propre aux dingbats : l'enonce doit etre affichable, pas dessine.
COMPLEMENT_DINGBATS = """
Precision : l'enonce est un rebus visuel compose d'emojis et de jeux typographiques directement affichables en HTML (positions, repetitions, barres, exposants). Ce n'est jamais une image a dessiner ni une description d'image."""

GABARIT_PAR_PRIMITIVE = {
    Primitive.question: GABARIT_QUESTION,
    Primitive.enigme: GABARIT_ENIGME,
    Primitive.vrai_faux: GABARIT_VRAI_FAUX,
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
