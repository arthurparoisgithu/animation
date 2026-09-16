# Image de production. Volontairement simple : une seule etape, pas de
# compilation a faire — psycopg[binary] fournit des roues precompilees.
FROM python:3.11-slim

# PYTHONUNBUFFERED : sans ca les logs restent bloques dans le tampon et
# n'apparaissent pas dans « fly logs ».
# PYTHONPATH : « import app » doit marcher quel que soit le repertoire
# courant du processus. Ne pas dependre du fait qu'uvicorn ajoute « . »
# au sys.path — c'est exactement l'hypothese qui avait casse la CI.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Les dependances d'abord, le code ensuite : Docker met cette couche en
# cache et ne reinstalle pas tout a chaque modification d'un fichier .py.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY fixtures/ ./fixtures/

# Un utilisateur non privilegie : un conteneur web n'a aucune raison de
# tourner en root.
RUN useradd --create-home --uid 1000 animation && chown -R animation:animation /app
USER animation

EXPOSE 8080

# PORT est fourni par l'hebergeur ; 8080 est la valeur par defaut de Fly.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
