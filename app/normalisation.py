"""Normalisation de texte, partagee par toute la validation deterministe.

C'est la brique la plus utilisee du projet : sans elle, comparer une bonne
reponse a une proposition revient a comparer deux chaines brutes, et
"L'Everest" != "l'everest" != "Everest ". Tout ce qui compare du texte dans
ce projet passe par ici.
"""

import re
import unicodedata

# Apres retrait des accents il ne reste que de l'ASCII : tout ce qui n'est ni
# lettre, ni chiffre, ni espace est de la ponctuation (y compris les emojis
# des dingbats, qu'on ne veut pas comparer).
_NON_ALPHANUM = re.compile(r"[^a-z0-9\s]")
_ESPACES = re.compile(r"\s+")

# Au-dela de cet ecart de longueur, deux mots ne sont plus une variante l'un
# de l'autre : "chat"/"chats" oui, "chat"/"chateau" non.
_ECART_VARIANTE_MAX = 2
_LONGUEUR_RACINE_MIN = 4


def normaliser(texte: str | None) -> str:
    """Minuscules, sans accents, sans ponctuation, espaces reduits.

    >>> normaliser("  L'Everest, 8 849 m !  ")
    'l everest 8 849 m'
    """
    if not texte:
        return ""

    # NFD separe chaque lettre accentuee en lettre + accent combinant ;
    # la categorie "Mn" (Mark, nonspacing) designe exactement ces accents.
    decompose = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in decompose if unicodedata.category(c) != "Mn")

    sans_ponctuation = _NON_ALPHANUM.sub(" ", sans_accents.lower())
    return _ESPACES.sub(" ", sans_ponctuation).strip()


# Determinants elides ou non, retires en tete de reponse. Sans ca,
# "L'Everest" et "Everest" sont deux reponses differentes, et le
# generateur repart pour un tour alors que l'item etait correct.
_DETERMINANTS = frozenset(
    {"le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "au", "aux"}
)


def cle(texte: str | None) -> str:
    """Forme canonique d'une reponse courte, pour comparer deux reponses.

    Normalise puis retire les determinants de tete.

    >>> cle("L'Everest")
    'everest'
    >>> cle("Le Mont Blanc") == cle("Mont Blanc")
    True
    """
    normalise = normaliser(texte)
    mots = normalise.split()
    while mots and mots[0] in _DETERMINANTS:
        mots.pop(0)
    # Si la reponse n'etait qu'un determinant, mieux vaut la garder telle
    # quelle que renvoyer une chaine vide qui s'egaliserait avec tout.
    return " ".join(mots) or normalise


def identiques(gauche: str | None, droite: str | None) -> bool:
    """Deux textes designent-ils la meme reponse ?"""
    return cle(gauche) == cle(droite)


def _meme_racine(mot: str, reference: str) -> bool:
    """Tolere les variantes courtes : pluriel, feminin, accord."""
    if mot == reference:
        return True
    court, long_ = sorted((mot, reference), key=len)
    if len(court) < _LONGUEUR_RACINE_MIN:
        return False
    return long_.startswith(court) and len(long_) - len(court) <= _ECART_VARIANTE_MAX


def contient(texte: str | None, terme: str | None) -> bool:
    """Le terme apparait-il dans le texte, au mot pres et variantes comprises ?

    La comparaison est faite mot a mot et non par sous-chaine : sinon la
    solution "or" serait detectee dans "corps", et toutes les enigmes
    seraient rejetees a tort.
    """
    mots_terme = normaliser(terme).split()
    mots_texte = normaliser(texte).split()
    if not mots_terme or len(mots_texte) < len(mots_terme):
        return False

    taille = len(mots_terme)
    for depart in range(len(mots_texte) - taille + 1):
        fenetre = mots_texte[depart : depart + taille]
        # Les mots qui precedent doivent correspondre exactement ; seul le
        # dernier mot peut varier (c'est lui qui porte l'accord).
        if fenetre[:-1] != mots_terme[:-1]:
            continue
        if _meme_racine(fenetre[-1], mots_terme[-1]):
            return True
    return False
