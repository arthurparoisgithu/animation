"""Les routes : une API JSON, et les pages servies par Jinja2.

/docs sert d'interface de test : FastAPI la genere a partir des
annotations de types et des modeles Pydantic ci-dessous.
"""

import json
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import reglages
from app.db import obtenir_session
from app.generateur import GenerationEchouee
from app.modele import AppelModeleEchoue
from app.modeles import Jeu
from app.requetes import (
    lister_formats,
    lister_jeux,
    obtenir_jeu,
    taux_de_rejet,
)
from app.schemas import Materiel, Moment, Public
from app.service import FormatInconnu, generer_et_enregistrer
from app.transport import FixtureIntrouvable

gabarits_html = Jinja2Templates(directory="app/templates")

routeur_api = APIRouter(prefix="/api", tags=["api"])
routeur_pages = APIRouter(tags=["pages"])


# --- Modeles d'entree et de sortie de l'API ---


class DemandeGeneration(BaseModel):
    format_code: str
    theme: str = Field(min_length=2, max_length=120)
    public: Public
    nb_items: int | None = Field(default=None, ge=1, le=30)
    # Sur une demo publique, la generation reelle est protegee par un code,
    # sinon ma cle d'API paie pour les visiteurs.
    code: str | None = None
    reutiliser: bool = True


class JeuResume(BaseModel):
    id: uuid.UUID
    format_code: str
    theme: str
    public: Public
    favori: bool
    nb_items: int

    @classmethod
    def depuis(cls, jeu: Jeu) -> "JeuResume":
        return cls(
            id=jeu.id,
            format_code=jeu.format_code,
            theme=jeu.theme,
            public=jeu.public,
            favori=jeu.favori,
            nb_items=len(jeu.contenu),
        )


class JeuComplet(JeuResume):
    contenu: list
    resservi: bool = False

    @classmethod
    def depuis(cls, jeu: Jeu, *, resservi: bool = False) -> "JeuComplet":
        resume = JeuResume.depuis(jeu)
        return cls(**resume.model_dump(), contenu=jeu.contenu, resservi=resservi)


def _verifier_code(fourni: str | None) -> None:
    """Protege la generation quand — et seulement quand — elle coute.

    La regle est fermee par defaut : en mode « api », un code est
    obligatoire. Sans cette contrainte, une instance mise en ligne avec
    MODE_MODELE=api et sans CODE_GENERATION laisserait n'importe quel
    visiteur declencher des appels factures sur ma cle. Le defaut
    dangereux est celui qui coute de l'argent : il doit etre impossible a
    atteindre par oubli.

    En mode « rejeu » aucun appel n'est emis, donc aucun code n'est exige.
    """
    configuration = reglages()

    if configuration.mode_modele != "api":
        return

    attendu = configuration.code_generation
    if not attendu:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Génération désactivée : cette instance appelle un modèle facturé "
            "mais n'a pas de CODE_GENERATION. Renseigne-le, ou passe en "
            "MODE_MODELE=rejeu pour une démonstration sans coût.",
        )

    # compare_digest plutot que « != » : la comparaison ne s'arrete pas au
    # premier caractere different, donc le temps de reponse ne renseigne
    # pas sur le nombre de caracteres corrects.
    if not secrets.compare_digest(fourni or "", attendu):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "La génération est protégée par un code sur cette instance.",
        )


# --- API ---


@routeur_api.get("/formats", summary="Le catalogue, filtre")
def formats(
    public: Public | None = None,
    moment: Moment | None = None,
    materiel: Materiel | None = None,
    session: Session = Depends(obtenir_session),
) -> list[dict]:
    return lister_formats(session, public=public, moment=moment, materiel=materiel)


@routeur_api.post("/jeux", summary="Genere un jeu", status_code=status.HTTP_201_CREATED)
def creer_jeu(
    demande: DemandeGeneration,
    session: Session = Depends(obtenir_session),
) -> JeuComplet:
    _verifier_code(demande.code)

    try:
        jeu, resservi = generer_et_enregistrer(
            session,
            format_code=demande.format_code,
            theme=demande.theme,
            public=demande.public,
            nb_items=demande.nb_items,
            reutiliser=demande.reutiliser,
        )
    except FormatInconnu:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Format inconnu.")
    except FixtureIntrouvable:
        # Instance en mode rejeu : elle ne sait montrer que ce qui a deja
        # ete genere. Sans ce cas, une demo publique renverrait une 500 des
        # qu'un visiteur saisit un theme inedit.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Cette instance fonctionne en mode démonstration : elle rejoue des "
            "générations déjà réalisées. Choisis un thème déjà présent dans la "
            "liste des jeux enregistrés.",
        )
    except AppelModeleEchoue as erreur:
        # 502 et non 500 : ce n'est pas l'application qui est cassee, c'est
        # le service en amont qui n'a pas repondu. Et surtout, le motif part
        # en JSON jusqu'a l'ecran : une cle refusee ou un credit epuise se
        # corrige en trente secondes quand on sait lequel des deux c'est.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(erreur))
    except GenerationEchouee as erreur:
        # 422 et non 500 : ce n'est pas un bug, c'est la validation qui a
        # fait son travail et refuse de livrer du contenu non verifie.
        raise HTTPException(
            # 422 en clair : la constante Starlette correspondante est
            # depreciee et son remplacant n'existe pas dans toutes les versions.
            422,
            {
                "message": str(erreur),
                "rejets": [
                    {"niveau": rejet.niveau.value, "motif": rejet.motif}
                    for rejet in erreur.rejets
                ],
            },
        )

    return JeuComplet.depuis(jeu, resservi=resservi)


@routeur_api.get("/jeux", summary="Les jeux enregistres")
def jeux(
    favoris: bool = False,
    limite: int = 50,
    session: Session = Depends(obtenir_session),
) -> list[JeuResume]:
    return [JeuResume.depuis(jeu) for jeu in lister_jeux(session, favoris_seulement=favoris, limite=limite)]


@routeur_api.get("/jeux/{identifiant}", summary="Un jeu et son contenu")
def jeu(identifiant: uuid.UUID, session: Session = Depends(obtenir_session)) -> JeuComplet:
    trouve = obtenir_jeu(session, identifiant)
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jeu inconnu.")
    return JeuComplet.depuis(trouve)


@routeur_api.patch("/jeux/{identifiant}/favori", summary="Bascule le favori")
def basculer_favori(
    identifiant: uuid.UUID, session: Session = Depends(obtenir_session)
) -> JeuResume:
    trouve = obtenir_jeu(session, identifiant)
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jeu inconnu.")
    trouve.favori = not trouve.favori
    session.commit()
    session.refresh(trouve)
    return JeuResume.depuis(trouve)


@routeur_api.get("/metriques/rejets", summary="Taux de rejet par format")
def metriques(session: Session = Depends(obtenir_session)) -> list[dict]:
    """La preuve que la validation sert a quelque chose."""
    return taux_de_rejet(session)


# --- Pages ---


@routeur_pages.get("/", response_class=HTMLResponse, include_in_schema=False)
def page_accueil(request: Request, session: Session = Depends(obtenir_session)):
    return gabarits_html.TemplateResponse(
        request,
        "accueil.html",
        {
            "formats": lister_formats(session),
            "publics": list(Public),
            "moments": list(Moment),
            "materiels": list(Materiel),
            "jeux": [JeuResume.depuis(jeu) for jeu in lister_jeux(session, limite=20)],
            "code_requis": reglages().mode_modele == "api",
        },
    )


@routeur_pages.get("/jeu/{identifiant}", response_class=HTMLResponse, include_in_schema=False)
def page_jeu(identifiant: uuid.UUID, request: Request, session: Session = Depends(obtenir_session)):
    trouve = obtenir_jeu(session, identifiant)
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jeu inconnu.")
    return gabarits_html.TemplateResponse(
        request, "jeu.html", {"jeu": trouve, "format": trouve.format}
    )


def _donnees_projection(jeu: Jeu) -> str:
    """Serialise le jeu pour le bloc <script type="application/json">.

    Les chevrons sont echappes : sans ca, un item contenant « </script> »
    fermerait le bloc et casserait la page.
    """
    brut = json.dumps(
        {"primitive": jeu.format.primitive.value, "items": jeu.contenu},
        ensure_ascii=False,
    )
    return brut.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


@routeur_pages.get("/projection/{identifiant}", response_class=HTMLResponse, include_in_schema=False)
def page_projection(identifiant: uuid.UUID, request: Request, session: Session = Depends(obtenir_session)):
    trouve = obtenir_jeu(session, identifiant)
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jeu inconnu.")
    return gabarits_html.TemplateResponse(
        request,
        "projection.html",
        {
            "jeu": trouve,
            "format": trouve.format,
            "donnees_json": _donnees_projection(trouve),
        },
    )


@routeur_pages.get("/metriques", response_class=HTMLResponse, include_in_schema=False)
def page_metriques(request: Request, session: Session = Depends(obtenir_session)):
    return gabarits_html.TemplateResponse(
        request, "metriques.html", {"metriques": taux_de_rejet(session)}
    )
