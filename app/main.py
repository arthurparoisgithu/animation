"""Point d'entree de l'application.

Lancement en developpement :
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import routeur_api, routeur_pages

app = FastAPI(
    title="Generateur de jeux d'animation",
    description=(
        "Genere, valide et projette des jeux pour animateurs. "
        "Trois primitives de contenu couvrent l'ensemble du catalogue de formats."
    ),
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(routeur_api)
app.include_router(routeur_pages)


@app.get("/sante", tags=["technique"])
def sante() -> dict[str, str]:
    """Route de vie, utile pour verifier que le serveur repond."""
    return {"statut": "ok"}
