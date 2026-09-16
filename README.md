# Générateur de jeux d'animation

Outil de préparation de jeux pour animateurs : on choisit un format, un thème et un
public, l'outil génère le contenu, **le valide**, l'enregistre et l'affiche en mode
projection.

![Mode projection](docs/captures/projection.png)

---

## Le problème

J'ai été animateur socioculturel pendant trois ans — clubs de vacances, périscolaire,
EHPAD. Préparer les jeux prend des heures de soirée, et c'est du travail répétitif qui
recommence intégralement à chaque nouveau groupe.

Un modèle de langage sait écrire un quiz en quelques secondes. Le problème, c'est qu'il
l'écrit avec un aplomb total, et que la bonne réponse est parfois fausse, absente des
propositions, ou présente deux fois. Une énigme générée est souvent insoluble, ou
contient sa propre solution. Or l'animateur est devant cinquante personnes quand il
découvre le problème.

**Ce projet n'est donc pas un projet de génération. C'est un projet de validation.**

---

## L'idée d'architecture

Je ne code pas vingt jeux. **Je code trois primitives de génération.**

Le mécanisme d'un jeu — comment on y joue — n'a pas besoin d'être généré : il est fixe et
l'animateur le connaît. Ce qui lui manque, c'est le *contenu*. Or vingt jeux différents ne
produisent que quelques formes de contenu.

| Primitive | Ce que le modèle produit | Formats couverts |
|---|---|---|
| `question` | question + 4 propositions + bonne réponse + anecdote | quiz express, quiz des minis, quiz à thème, speed quiz |
| `enigme` | énoncé + solution + indice | dingbats, personnage mystère, devinettes, anagrammes |
| `vrai_faux` | affirmation + verdict + explication | le scoop, incroyable mais vrai |

**Conséquence : ajouter un format, c'est une ligne en base et un gabarit de prompt, zéro
ligne de Python.** Ajouter une primitive, ça c'est du code. Cette séparation entre ce qui
se configure et ce qui se développe est le point d'architecture central du projet.

Le catalogue de départ contient dix formats pour trois primitives : c'est la démonstration.

---

## La validation, en deux niveaux

**Rien n'entre en base sans avoir passé les deux.**

### Niveau 1 — déterministe, en code

Gratuit, instantané, certain. Il s'exécute **en premier** : ce qui est rejeté ici ne coûte
aucun appel de modèle. C'est le principal levier de coût du projet.

| Primitive | Règles |
|---|---|
| commun | schéma Pydantic respecté, aucun champ vide, aucun champ en trop, longueurs maximales |
| `question` | exactement 4 propositions, aucun doublon après normalisation, la bonne réponse figure une fois et une seule |
| `enigme` | la solution n'apparaît ni dans l'énoncé ni dans l'indice, variantes comprises ; solution de deux mots maximum |
| `vrai_faux` | verdict dans `{vrai, faux}`, le mot ne figure pas dans l'affirmation, et 30 à 70 % de vraies sur le lot |

Tout repose sur deux fonctions partagées, dans `app/normalisation.py` :

- `normaliser(texte)` — minuscules, accents et ponctuation retirés, espaces réduits ;
- `contient(texte, terme)` — comparaison **mot à mot** et non par sous-chaîne, sinon la
  solution « or » serait détectée dans le mot « corps » et toutes les énigmes seraient
  rejetées à tort.

Ce sont les premières fonctions couvertes par les tests.

### Niveau 2 — le juge

Un second appel de modèle, qui ne tranche **que ce que le code ne peut pas trancher** :
exactitude factuelle et adéquation au public. Verdict binaire par item, plus un motif.

Un juge injoignable ou illisible rejette tout le lot : du contenu non contrôlé ne doit
jamais passer par défaut.

### Et si ça échoue

On régénère — en ne redemandant que les items manquants — **trois tentatives maximum**,
puis erreur explicite. Chaque rejet est enregistré avec son motif et son niveau.

**Le taux de rejet par format est affiché dans l'interface** : c'est la preuve que la
validation sert à quelque chose. Au-delà de 20 % sur un format, il passe en Sonnet et la
raison est notée dans le `JOURNAL.md`.

![Taux de rejet](docs/captures/metriques.png)

> Principe général du projet : *un modèle à qui on ne donne rien à mesurer invente.*

---

## Stack

Python · FastAPI · Pydantic · SQLAlchemy · PostgreSQL · Alembic · Jinja2 et JavaScript
natif · pytest · GitHub Actions.

**Haiku 4.5 pour la génération et pour le juge.** C'est le moins cher de la gamme, et sur
une sortie JSON fortement contrainte il suffit. Ordre de grandeur : un demi-centime par
jeu généré.

Autres leviers de coût : le déterministe avant le juge ; même format + même thème + même
public déjà en base, on ressert au lieu de régénérer ; plafond de dépense côté console.

Pas de front Next.js : l'objet de la démonstration ici est le back-end Python.

---

## Lancer le projet

```bash
git clone https://github.com/arthurparoisgithu/animation.git
cd animation

python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # puis renseigner ANTHROPIC_API_KEY
```

Une base Postgres est nécessaire :

```bash
createdb animation
alembic upgrade head               # crée les trois tables
python -m scripts.seed             # insère les dix formats du catalogue
```

Puis :

```bash
uvicorn app.main:app --reload
```

- interface : <http://127.0.0.1:8000/>
- documentation OpenAPI, générée par FastAPI : <http://127.0.0.1:8000/docs>

### Générer sans passer par l'interface

```bash
python -m scripts.generer --format quiz_express --theme "le cinéma des années 90" --public ado
python -m scripts.generer --format dingbats --theme "les animaux" --public junior --sans-juge
```

`--sans-juge` évite l'appel au juge pendant la mise au point d'un gabarit : on ne paie
alors que la génération.

### Enregistrer une fois, rejouer toujours

Un appel de modèle coûte de l'argent et n'est jamais deux fois identique. Le projet
isole donc **une seule couture** — `app/transport.py` — et la branche de trois façons :

| Mode | Ce qui se passe | Coût |
|---|---|---|
| `api` | appel réel | ~1 centime par jeu |
| `enregistrement` | appel réel, puis la réponse brute est écrite dans `fixtures/` | idem, une fois |
| `rejeu` | la réponse enregistrée est relue, aucun réseau | zéro |

```bash
# Une seule fois, avec une clé d'API : c'est la seule commande qui coûte.
python -m scripts.campagne --enregistrer

# Ensuite, autant de fois qu'on veut, gratuitement.
python -m scripts.campagne --rejouer
```

Le générateur et le juge ne savent pas d'où vient la réponse — ils appellent
`modele.appeler()`, qui délègue au transport actif. Rien d'autre ne change.

Trois bénéfices, et le troisième est le plus important :

- **le coût** : une campagne payante, rejouée ensuite par les tests, par la démo et par
  quiconque clone le dépôt ;
- **le déterminisme** : mêmes entrées, mêmes sorties, donc un test qui passe aujourd'hui
  passera demain ;
- **la preuve** : ce sont de *vraies* sorties de modèle, défauts compris. Une fixture que
  la validation rejette vaut mieux qu'un cas inventé — elle montre que le problème est
  réel.

Un prompt absent des fixtures lève une erreur explicite plutôt que de repartir vers un
appel facturé : une démo en ligne ne doit pas se mettre à dépenser sans prévenir. Côté
API, ce cas renvoie un 503 avec un message lisible, pas un 500.

### Les tests

```bash
pytest
```

Les tests de validation et de génération ne touchent ni au réseau ni à la base : l'appel
au modèle est simulé, ils sont déterministes et gratuits. Ceux de l'API ont besoin d'un
Postgres joignable via `DATABASE_URL` ; sans lui ils sont ignorés, pas mis en échec.

GitHub Actions les lance à chaque push, avec un service Postgres. Aucun secret n'est
nécessaire : aucune clé d'API ne circule dans la CI.

---

## L'interface

Le catalogue se filtre par public, moment de la journée et matériel disponible — ce sont
les trois contraintes réelles d'un animateur qui prépare une soirée.

![Accueil](docs/captures/accueil.png)

Le mode projection est fait pour un vidéoprojecteur : fond sombre, texte dimensionné en
unités relatives à la largeur d'écran, flèches pour naviguer, espace pour révéler la
réponse, `F` pour le plein écran.

![Projection d'un dingbat](docs/captures/projection-dingbats.png)

---

## Structure

```
app/
  normalisation.py   normaliser(), cle(), contient() — la base de toute comparaison
  schemas.py         les trois primitives en Pydantic, et les énumérations du catalogue
  validation.py      niveau 1 : les règles déterministes, fonctions pures
  gabarits.py        un gabarit de prompt par primitive
  catalogue.py       les dix formats de départ, source de vérité du seed
  transport.py       la couture : appel réel, enregistré, ou rejoué depuis fixtures/
  modele.py          appel Anthropic et extraction du JSON — tout le réseau est ici
  juge.py            niveau 2 : exactitude factuelle et adéquation au public
  generateur.py      orchestration : générer, valider, juger, recommencer
  modeles.py         les trois tables SQLAlchemy
  requetes.py        les requêtes SQL, dont le filtrage par tableau avec @>
  service.py         le lien entre le générateur et la base
  api.py             les routes JSON et les pages
scripts/
  generer.py         génération à la main, sans base ni API
  campagne.py        un jeu par format : enregistre les fixtures, ou les rejoue
  seed.py            insertion idempotente du catalogue
fixtures/            réponses de modèle enregistrées (voir fixtures/README.md)
tests/               133 tests, dont 14 contre un vrai Postgres
alembic/             migrations
```

---

## Choix que je peux défendre

- **Le tableau Postgres pour `publics`** plutôt qu'une table de liaison. Ça permet
  d'écrire le filtrage avec l'opérateur de contenance `@>` et un index GIN, en une clause
  au lieu d'une jointure.
- **`contient()` compare mot à mot.** Une comparaison par sous-chaîne rejetterait une
  énigme correcte dès que la solution est un mot court.
- **`cle()` retire les déterminants de tête.** Sans elle, « L'Everest » et « Everest »
  sont deux réponses différentes, et le générateur repart pour un tour alors que l'item
  était bon. Une régénération inutile, c'est un appel payé pour rien.
- **La substitution des placeholders passe par une expression régulière**, pas par
  `str.format()` : les gabarits contiennent des accolades JSON d'exemple, sur lesquelles
  `format()` échoue.
- **Un échec de génération renvoie 422, pas 500.** Ce n'est pas un bug, c'est la
  validation qui refuse de livrer du contenu non vérifié.
- **La répartition vrai/faux est vérifiée sur le jeu final assemblé**, pas passe par
  passe : c'est le lot complet que l'animateur projette.
- **Un item qui viole trois règles compte pour un rejet**, avec ses trois motifs. Le taux
  de rejet se mesure en items, pas en motifs.
- **Une seule couture pour l'appel de modèle**, et trois implémentations derrière. C'est
  ce qui rend le projet démontrable sans clé et testable sans réseau, sans une seule
  ligne de code conditionnel dans le générateur ou le juge.

---

## Limites assumées

- Deux primitives sont gardées pour plus tard : `consigne` (mimes, défis, gages) et
  `contrainte` (mots imposés). Leur contenu ne peut pas être validé automatiquement, or la
  validation est le cœur du projet. On commence par ce qu'on peut prouver.
- **Aucune parole de chanson** n'est générée ni stockée : ce sont des œuvres protégées.
- **Aucun nom de format télévisé** : les noms du catalogue sont les miens.
- **L'audio et l'image ne se génèrent pas ici.** Une playlist de blind test, si : titre,
  artiste, année, réponse attendue. L'outil produit la liste, pas le média.
- Si le projet est mis en ligne, la démo publique tourne en `MODE_MODELE=rejeu` et la
  génération réelle est protégée par un code (`CODE_GENERATION`). Un visiteur voit donc
  de vraies sorties de modèle et toute l'application, sans qu'un seul appel soit facturé.

---

Arthur Parois — [`JOURNAL.md`](JOURNAL.md) retrace le déroulé du développement.
