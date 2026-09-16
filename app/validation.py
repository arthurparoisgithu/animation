"""Niveau 1 de validation : deterministe, en code, sans appel de modele.

Gratuit, instantane, certain. S'execute avant le juge : ce qui est rejete
ici ne coute aucun appel. Toutes les fonctions de ce module sont pures, ce
qui les rend testables sans reseau ni base.
"""

from dataclasses import dataclass, field

from pydantic import ValidationError

from app.normalisation import cle, contient, identiques, normaliser
from app.schemas import SCHEMA_PAR_PRIMITIVE, Enigme, Primitive, Question, VraiFaux

# Longueurs maximales, reprises telles quelles des gabarits de prompt :
# le modele a recu la contrainte, on verifie qu'il l'a respectee.
LONGUEUR_QUESTION_MAX = 140
LONGUEUR_PROPOSITION_MAX = 60
LONGUEUR_ENONCE_MAX = 200
LONGUEUR_EXPLICATION_MAX = 300

NB_PROPOSITIONS = 4
SOLUTION_MOTS_MAX = 2

# Formulations qui rendent une question injouable a l'oral.
FORMULES_INTERDITES = (
    "toutes ces reponses",
    "toutes les reponses",
    "aucune de ces reponses",
    "aucune des reponses",
    "les deux",
    "a et b",
)

VERDICTS = ("vrai", "faux")
PART_VRAIES_MIN = 0.30
PART_VRAIES_MAX = 0.70
# En dessous de deux items, une repartition n'a pas de sens.
LOT_MIN_POUR_REPARTITION = 2


@dataclass(frozen=True)
class MotifRejet:
    """Un item refuse, et pourquoi.

    index vaut None quand le rejet porte sur le lot entier et non sur un
    item precis (cas de la repartition vrai/faux).
    """

    motif: str
    index: int | None = None

    def __str__(self) -> str:
        if self.index is None:
            return f"lot : {self.motif}"
        return f"item {self.index} : {self.motif}"


@dataclass
class Resultat:
    """Ce qui sort de la validation : les items retenus et les motifs de rejet."""

    items: list = field(default_factory=list)
    rejets: list[MotifRejet] = field(default_factory=list)

    @property
    def est_valide(self) -> bool:
        return not self.rejets


def _trop_long(texte: str, maximum: int) -> bool:
    return len(texte) > maximum


def valider_question(item: Question) -> list[str]:
    """Regles propres a la primitive question. Retourne la liste des motifs."""
    motifs: list[str] = []

    if _trop_long(item.question, LONGUEUR_QUESTION_MAX):
        motifs.append(
            f"question de {len(item.question)} caracteres, {LONGUEUR_QUESTION_MAX} maximum"
        )

    if len(item.propositions) != NB_PROPOSITIONS:
        motifs.append(
            f"{len(item.propositions)} propositions, il en faut exactement {NB_PROPOSITIONS}"
        )

    if any(not proposition.strip() for proposition in item.propositions):
        motifs.append("proposition vide")

    for proposition in item.propositions:
        if _trop_long(proposition, LONGUEUR_PROPOSITION_MAX):
            motifs.append(
                f"proposition de {len(proposition)} caracteres, "
                f"{LONGUEUR_PROPOSITION_MAX} maximum"
            )

    # Deux formes normalisees : la cle sert a comparer des reponses entre
    # elles (elle ignore les determinants), le texte normalise sert a
    # reconnaitre les formules interdites telles qu'elles sont ecrites.
    cles = [cle(proposition) for proposition in item.propositions]
    normalisees = [normaliser(proposition) for proposition in item.propositions]

    vues: set[str] = set()
    for proposition in cles:
        if proposition and proposition in vues:
            motifs.append(f"proposition en doublon apres normalisation : « {proposition} »")
        vues.add(proposition)

    for proposition in normalisees:
        if proposition in FORMULES_INTERDITES:
            motifs.append(f"formule interdite en proposition : « {proposition} »")

    # La regle centrale de la primitive : une bonne reponse, une seule, et
    # elle doit figurer parmi les propositions.
    occurrences = cles.count(cle(item.bonne_reponse))
    if occurrences == 0:
        motifs.append("la bonne reponse ne figure pas parmi les propositions")
    elif occurrences > 1:
        motifs.append(f"la bonne reponse figure {occurrences} fois parmi les propositions")

    return motifs


def valider_enigme(item: Enigme) -> list[str]:
    """Regles propres a la primitive enigme."""
    motifs: list[str] = []

    if _trop_long(item.enonce, LONGUEUR_ENONCE_MAX):
        motifs.append(
            f"enonce de {len(item.enonce)} caracteres, {LONGUEUR_ENONCE_MAX} maximum"
        )

    mots_solution = normaliser(item.solution).split()
    if len(mots_solution) > SOLUTION_MOTS_MAX:
        motifs.append(
            f"solution de {len(mots_solution)} mots, {SOLUTION_MOTS_MAX} maximum"
        )

    # Le defaut le plus frequent des enigmes generees : l'enonce contient
    # deja sa propre reponse.
    if contient(item.enonce, item.solution):
        motifs.append("la solution apparait dans l'enonce")

    if contient(item.indice, item.solution):
        motifs.append("la solution apparait dans l'indice")

    if identiques(item.indice, item.solution):
        motifs.append("l'indice est identique a la solution")

    return motifs


def valider_vrai_faux(item: VraiFaux) -> list[str]:
    """Regles propres a la primitive vrai_faux, item par item."""
    motifs: list[str] = []

    verdict = normaliser(item.verdict)
    if verdict not in VERDICTS:
        motifs.append(f"verdict « {item.verdict} » hors de {VERDICTS}")

    # Si l'affirmation contient le mot, elle donne sa propre reponse.
    for mot in VERDICTS:
        if contient(item.affirmation, mot):
            motifs.append(f"le mot « {mot} » figure dans l'affirmation")

    if _trop_long(item.explication, LONGUEUR_EXPLICATION_MAX):
        motifs.append(
            f"explication de {len(item.explication)} caracteres, "
            f"{LONGUEUR_EXPLICATION_MAX} maximum"
        )

    return motifs


def valider_repartition(items: list[VraiFaux]) -> list[str]:
    """Regle de lot : un jeu ou tout est vrai n'a aucun interet."""
    if len(items) < LOT_MIN_POUR_REPARTITION:
        return []

    vraies = sum(1 for item in items if normaliser(item.verdict) == "vrai")
    part = vraies / len(items)
    if not PART_VRAIES_MIN <= part <= PART_VRAIES_MAX:
        return [
            f"{vraies} affirmations vraies sur {len(items)} ({part:.0%}), "
            f"attendu entre {PART_VRAIES_MIN:.0%} et {PART_VRAIES_MAX:.0%}"
        ]
    return []


_REGLES_PAR_PRIMITIVE = {
    Primitive.question: valider_question,
    Primitive.enigme: valider_enigme,
    Primitive.vrai_faux: valider_vrai_faux,
}


def _motif_pydantic(erreur: ValidationError) -> str:
    """Traduit une ValidationError en un motif court et lisible."""
    details = []
    for faute in erreur.errors():
        chemin = ".".join(str(part) for part in faute["loc"]) or "item"
        details.append(f"{chemin} ({faute['msg']})")
    return "schema non respecte : " + ", ".join(details)


def valider_lot(
    primitive: Primitive,
    donnees: list[dict],
    *,
    verifier_repartition: bool = True,
) -> Resultat:
    """Valide une sortie brute de modele, item par item puis lot entier.

    donnees est la liste de dictionnaires issue du JSON du modele. Rien de
    ce qui sort d'ici en rejet ne doit entrer en base.

    verifier_repartition est mis a False par le generateur, qui appelle le
    modele plusieurs fois : la repartition vrai/faux doit etre jugee sur le
    jeu final assemble, pas sur chaque passe prise isolement.
    """
    schema = SCHEMA_PAR_PRIMITIVE[primitive]
    regles = _REGLES_PAR_PRIMITIVE[primitive]

    resultat = Resultat()

    for index, brut in enumerate(donnees):
        if not isinstance(brut, dict):
            resultat.rejets.append(
                MotifRejet("schema non respecte : objet JSON attendu", index)
            )
            continue

        try:
            item = schema.model_validate(brut)
        except ValidationError as erreur:
            resultat.rejets.append(MotifRejet(_motif_pydantic(erreur), index))
            continue

        motifs = regles(item)
        if motifs:
            resultat.rejets.extend(MotifRejet(motif, index) for motif in motifs)
            continue

        resultat.items.append(item)

    if verifier_repartition and primitive is Primitive.vrai_faux:
        for motif in valider_repartition(resultat.items):
            resultat.rejets.append(MotifRejet(motif))

    return resultat
