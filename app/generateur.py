"""Orchestration : generer, valider en deterministe, juger, recommencer.

L'ordre compte. Le deterministe passe en premier parce qu'il est gratuit :
un item mal forme ne doit jamais consommer un appel au juge.
"""

from dataclasses import dataclass, field

from app.config import reglages
from app.gabarits import remplir_gabarit
from app.juge import juger
from app.modele import SortieIllisible, appeler, extraire_json
from app.schemas import NiveauRejet, Primitive
from app.validation import valider_lot, valider_repartition


class GenerationEchouee(RuntimeError):
    """Le nombre d'items demande n'a pas ete atteint apres toutes les tentatives."""

    def __init__(self, message: str, rejets: list["RejetTrace"]) -> None:
        super().__init__(message)
        self.rejets = rejets


@dataclass(frozen=True)
class RejetTrace:
    """Un rejet, avec le niveau qui l'a produit : c'est ce qui part en base."""

    motif: str
    niveau: NiveauRejet
    tentative: int


@dataclass
class ResultatGeneration:
    items: list = field(default_factory=list)
    rejets: list[RejetTrace] = field(default_factory=list)
    tentatives: int = 0

    @property
    def taux_rejet(self) -> float:
        """Part des items produits qui ont ete refuses."""
        total = len(self.items) + len(self.rejets)
        return len(self.rejets) / total if total else 0.0


def construire_prompt(
    gabarit: str, *, theme: str, public: str, nb_items: int, nom_format: str
) -> str:
    """Le seul travail du code sur le prompt : substituer les placeholders."""
    return remplir_gabarit(
        gabarit,
        theme=theme,
        public=public,
        nb_items=nb_items,
        nom_format=nom_format,
    )


def generer(
    *,
    primitive: Primitive,
    gabarit: str,
    nom_format: str,
    theme: str,
    public: str,
    nb_items: int,
    avec_juge: bool = True,
) -> ResultatGeneration:
    """Produit nb_items items valides, ou echoue en disant pourquoi.

    A chaque tentative on ne redemande que ce qui manque : les items deja
    acceptes sont conserves.
    """
    resultat = ResultatGeneration()
    max_tentatives = reglages().max_tentatives

    for tentative in range(1, max_tentatives + 1):
        manquants = nb_items - len(resultat.items)
        if manquants <= 0:
            break
        # Apres le test de sortie, sinon le compteur rapporte une tentative
        # de trop : celle ou l'on a constate qu'il n'y avait plus rien a faire.
        resultat.tentatives = tentative

        prompt = construire_prompt(
            gabarit,
            theme=theme,
            public=public,
            nb_items=manquants,
            nom_format=nom_format,
        )

        try:
            brut = appeler(prompt, modele=reglages().modele_generation)
            donnees = extraire_json(brut)
        except SortieIllisible as erreur:
            resultat.rejets.append(
                RejetTrace(str(erreur), NiveauRejet.deterministe, tentative)
            )
            continue

        # Niveau 1 : gratuit, il passe en premier.
        # La repartition vrai/faux est verifiee a la fin, sur le jeu complet.
        niveau_1 = valider_lot(primitive, donnees, verifier_repartition=False)
        resultat.rejets.extend(
            RejetTrace(rejet.motif, NiveauRejet.deterministe, tentative)
            for rejet in niveau_1.rejets
        )

        retenus = niveau_1.items
        if not retenus:
            continue

        # Niveau 2 : ne voit que ce qui a survecu au niveau 1.
        if avec_juge:
            niveau_2 = juger(retenus, primitive=primitive, theme=theme, public=public)
            resultat.rejets.extend(
                RejetTrace(rejet.motif, NiveauRejet.juge, tentative)
                for rejet in niveau_2.rejets
            )
            retenus = niveau_2.items

        resultat.items.extend(retenus)

    resultat.items = resultat.items[:nb_items]

    if len(resultat.items) < nb_items:
        raise GenerationEchouee(
            f"{len(resultat.items)} items valides sur {nb_items} demandes "
            f"apres {resultat.tentatives} tentatives",
            resultat.rejets,
        )

    # Regle de lot, jugee sur le jeu final assemble et non passe par passe.
    if primitive is Primitive.vrai_faux:
        motifs = valider_repartition(resultat.items)
        if motifs:
            resultat.rejets.extend(
                RejetTrace(motif, NiveauRejet.deterministe, resultat.tentatives)
                for motif in motifs
            )
            raise GenerationEchouee(
                "repartition vrai/faux hors des bornes : " + " ; ".join(motifs),
                resultat.rejets,
            )

    return resultat
