# Générateur de jeux d'animation

## Contexte

Je m'appelle Arthur Parois. Je construis ce projet comme sixième pièce d'un dossier de
candidature en alternance (contrat de professionnalisation, Paris), visant notamment la
formation Développeur IA de Simplon.

Le dossier contient déjà deux sites Next.js livrés à des clients, un cours interactif sur
les fonctions n8n et un workflow n8n multi-agents d'audit. Il ne contient **aucune ligne de
Python**, et c'est précisément ce que ce projet doit corriger.

J'ai été animateur socioculturel pendant trois ans (clubs de vacances, périscolaire, EHPAD).
Ce projet outille le métier que je connais de l'intérieur.

## Ce que fait le produit

Un générateur de jeux prêts à projeter pour animateurs. L'animateur choisit un format de
jeu, un thème et un public ; l'outil génère les items, les valide, les enregistre, et les
affiche en mode projection.

Le problème réel : préparer les jeux prend des heures de soirée, et c'est du travail
répétitif qui recommence à chaque nouveau groupe.

## L'idée d'architecture centrale

**Je ne code pas vingt jeux. Je code trois primitives de génération.**

Le mécanisme d'un jeu (comment on y joue) n'a pas besoin d'être généré : il est fixe et
l'animateur le connaît. Ce qui manque à l'animateur, c'est le **contenu** : les questions,
les énigmes, les affirmations. Or vingt jeux différents ne produisent que quelques formes
de contenu.

| Primitive | Ce que le modèle produit | Formats couverts |
|---|---|---|
| `question` | question + 4 propositions + bonne réponse + anecdote | quiz express, quiz des minis, quiz thématique, speed quiz |
| `enigme` | énoncé + solution + indice | dingbats, personnage mystère, devinettes, anagrammes |
| `vrai_faux` | affirmation + verdict + explication | le scoop, incroyable mais vrai, deux vérités un mensonge |

Conséquence : **ajouter un format = une ligne en base et un gabarit de prompt, zéro ligne de
Python.** Ajouter une primitive, ça c'est du code. Cette séparation entre ce qui se
configure et ce qui se développe est le point d'architecture que je veux pouvoir expliquer
en entretien.

Primitives gardées pour la v2, hors périmètre pour l'instant : `consigne` (mimes, défis,
gages) et `contrainte` (ABC song, Mexico, mots imposés). Raison : leur contenu ne peut pas
être validé automatiquement, or la validation est le cœur du projet. On commence par ce
qu'on peut prouver.

## Modèle de données

Conventions Python : `snake_case` partout, colonnes comprises.

### `format_jeu` — le catalogue, saisi à la main, jamais généré

| champ | type | rôle |
|---|---|---|
| code | text (PK) | `quiz_express`, `dingbats`… |
| nom | text | affiché à l'animateur |
| primitive | enum | question, enigme, vrai_faux |
| publics | text[] | mini, junior, ado, adulte, general |
| moment | enum | cafe_apero, veillee_enfants, soiree_adultes, grand_jeu |
| materiel | enum | aucun, videoprojecteur, sono, accessoires |
| regle_animateur | text | comment on y joue, 3 lignes |
| gabarit_prompt | text | avec placeholders `{theme}`, `{public}`, `{nb_items}` |
| nb_items_defaut | int | |

`publics` en tableau Postgres est volontaire : ça me donne l'occasion d'écrire une vraie
requête SQL avec l'opérateur de contenance plutôt que de tout passer par l'ORM.

### `jeu` — les instances générées

| champ | type |
|---|---|
| id | uuid |
| format_code | text (FK → format_jeu) |
| theme | text |
| public | enum |
| contenu | jsonb (les items, structure propre à la primitive) |
| favori | bool |
| cree_le | timestamptz |

### `rejet` — la métrique de validation

| champ | type |
|---|---|
| id | uuid |
| format_code | text |
| primitive | enum |
| motif | text |
| niveau | enum (deterministe, juge) |
| cree_le | timestamptz |

## Catalogue de départ

Dix formats à insérer en seed. Ils ne couvrent que trois primitives : c'est le but.

| code | nom | primitive | publics | moment | matériel |
|---|---|---|---|---|---|
| `quiz_express` | Quiz express | question | ado, adulte, general | cafe_apero | aucun |
| `quiz_minis` | Le quiz des minis | question | mini, junior | veillee_enfants | videoprojecteur |
| `quiz_thematique` | Quiz à thème | question | general | soiree_adultes | videoprojecteur |
| `speed_quiz` | Speed quiz par équipes | question | ado, adulte, general | soiree_adultes | videoprojecteur |
| `dingbats` | Dingbats | enigme | junior, ado, adulte, general | veillee_enfants, soiree_adultes | videoprojecteur |
| `personnage_mystere` | Personnage mystère | enigme | junior, ado, adulte, general | soiree_adultes | aucun |
| `devinettes` | Devinettes | enigme | mini, junior | veillee_enfants | aucun |
| `anagrammes` | Anagrammes | enigme | ado, adulte, general | cafe_apero | videoprojecteur |
| `le_scoop` | Le scoop | vrai_faux | junior, ado, adulte, general | soiree_adultes | aucun |
| `incroyable_vrai` | Incroyable mais vrai | vrai_faux | adulte, general | cafe_apero | aucun |

## Gabarits de prompt

Un par primitive, stocké en base dans `format_jeu.gabarit_prompt`. Le code ne fait
qu'y substituer les placeholders. Sortie JSON stricte, sans texte autour, sans balises de
code.

### `question`

> Tu génères {nb_items} questions pour un jeu d'animation en club de vacances.
> Thème : {theme}. Public : {public}.
> Contraintes : exactement 4 propositions par question, une seule correcte, les trois autres
> plausibles mais indiscutablement fausses. Question de 140 caractères maximum, propositions
> de 60 caractères maximum. Pas de « toutes ces réponses » ni « aucune de ces réponses ».
> Faits vérifiables uniquement, aucune question d'actualité de moins de deux ans.
> Ajoute une anecdote d'une phrase pour que l'animateur ait quelque chose à dire après la
> réponse.
> Réponds uniquement par un tableau JSON d'objets {question, propositions, bonne_reponse, anecdote}.

### `enigme`

> Tu génères {nb_items} énigmes de type {nom_format} pour un jeu d'animation.
> Thème : {theme}. Public : {public}.
> Contraintes : une seule solution possible, formulée en un ou deux mots. La solution ne doit
> apparaître ni dans l'énoncé ni dans l'indice, sous aucune forme ni variante. L'indice doit
> réduire la difficulté sans donner la réponse. Énoncé de 200 caractères maximum.
> Réponds uniquement par un tableau JSON d'objets {enonce, solution, indice}.

### `vrai_faux`

> Tu génères {nb_items} affirmations à trancher pour un jeu d'animation.
> Thème : {theme}. Public : {public}.
> Contraintes : environ la moitié de vraies. Chaque affirmation doit être surprenante mais
> vérifiable dans une encyclopédie généraliste. Les mots « vrai » et « faux » ne doivent pas
> figurer dans l'affirmation. Explication de 300 caractères maximum.
> Réponds uniquement par un tableau JSON d'objets {affirmation, verdict, explication}.

Pour `dingbats`, préciser dans le gabarit que l'énoncé est composé d'emojis et de jeux
typographiques affichables en HTML, pas une image à dessiner.

## Validation

C'est le cœur du projet et ce que je raconterai en entretien.

Un modèle génère un quizz avec un aplomb total, et la bonne réponse est parfois fausse,
absente des propositions ou présente deux fois. Une énigme générée est souvent insoluble,
ou contient sa propre solution. Or l'animateur est devant cinquante personnes quand il
découvre le problème.

**Rien n'entre en base sans avoir passé les deux niveaux.**

### Niveau 1 — déterministe (code)

Gratuit, instantané, certain. S'exécute en premier ; ce qui est rejeté ici ne coûte aucun
appel de modèle.

Commun : le JSON respecte le schéma Pydantic de la primitive, aucun champ vide, longueurs
maximales respectées.

`question` : exactement 4 propositions, aucun doublon après normalisation, la bonne réponse
figure une et une seule fois parmi elles.

`enigme` : la solution normalisée n'apparaît ni dans l'énoncé ni dans l'indice ; l'indice
diffère de la solution.

`vrai_faux` : verdict dans {vrai, faux} ; ni « vrai » ni « faux » dans l'affirmation ;
répartition entre 30 % et 70 % de vraies sur l'ensemble du lot.

Fonction utilitaire `normaliser(texte)` partagée : minuscules, accents retirés, ponctuation
retirée, espaces réduits. C'est elle qui rend les comparaisons fiables, et c'est la première
chose à couvrir de tests.

### Niveau 2 — juge (modèle)

Seulement ce que le code ne peut pas trancher : exactitude factuelle et adéquation au
public. Un appel, en Haiku, verdict binaire plus motif.

Échec : on régénère, **3 tentatives maximum**, puis erreur explicite. Chaque rejet est
enregistré avec son motif. Le taux de rejet par format est une métrique affichée dans
l'interface : c'est la preuve que la validation sert à quelque chose.

Principe général du projet : *un modèle à qui on ne donne rien à mesurer invente.*

## Stack

**Python. C'est une décision arrêtée, ne me propose pas de repasser en JavaScript.**

FastAPI · Pydantic · SQLAlchemy · PostgreSQL · Jinja2 et JavaScript natif pour l'interface,
servie par FastAPI · pytest · GitHub Actions.

Pas de front Next.js : mon dossier en contient déjà deux, je n'ai rien à prouver côté front.
Ici l'objet de la démonstration est le back-end Python.

La clé d'API vit dans `.env`, jamais dans le code, jamais commitée. Vérifie le `.gitignore`
avant le premier commit.

## Modèle et coût

**Haiku 4.5 pour la génération et pour le juge** (1 $ / 5 $ par million de tokens en entrée
et en sortie, le moins cher de la gamme Claude). Sur une sortie JSON bien contrainte, il
suffit. Ordre de grandeur : un demi-centime par jeu généré.

Escalade : si le taux de rejet dépasse 20 % sur un format, ce format passe en Sonnet et je
note la raison dans le `JOURNAL.md`. Pas d'escalade « au cas où ».

Autres leviers : le déterministe avant le juge ; même format + même thème + même public déjà
en base, on ressert au lieu de régénérer ; plafond de dépense côté console.

Si le projet est mis en ligne : la démo publique affiche des jeux déjà en base, la génération
réelle est protégée par un code. Sinon ma clé paie pour les visiteurs.

## Étapes, dans cet ordre

1. **Socle** : venv, `requirements.txt`, `git init`, `.gitignore`, FastAPI qui répond sur
   une route. Premier commit, rien d'autre.
2. **Les schémas Pydantic** des trois primitives, et la fonction `normaliser`.
3. **Le générateur seul**, en script lancé à la main, sur la primitive `question`
   uniquement, sans base ni API. Étape la plus formatrice, on prend le temps.
4. **La validation déterministe**, les trois primitives.
5. **Les tests** : pytest sur la validation et sur `normaliser`. Fonctions pures,
   déterministes, aucune dépendance réseau : un test par règle, plus des cas de sortie de
   modèle volontairement cassée écrits en dur.
6. **L'intégration continue** : workflow GitHub Actions qui lance pytest à chaque push.
7. **Le juge**, et le comptage des rejets.
8. **La base** : SQLAlchemy, les trois tables, migrations, seed du catalogue.
9. **L'API** : les endpoints ; `/docs` sert d'interface de test.
10. **L'interface** : choix du format filtré par public / moment / matériel, formulaire de
    génération, liste, mode projection plein écran (touches fléchées, gros texte, fond
    sombre).
11. **Le README** : le problème, la solution, comment lancer, captures. Écrit en dernier,
    pas bâclé.

Ne pas sauter l'étape 3 pour aller à l'API. Déboguer un appel de modèle à travers une couche
HTTP quand on débute en Python, c'est deux soirées perdues.

## Pièges à ne pas ignorer

- **Paroles de chansons** : œuvres protégées. On ne les génère pas, on ne les stocke pas. Le
  karaoké à trous de la v2 fonctionnera avec un texte collé par l'animateur ; l'outil choisit
  seulement quels mots masquer.
- **Noms de marques** : les formats télévisés et leurs noms d'épreuves sont déposés. Les
  formats du catalogue portent mes propres noms.
- **Blind test et jeux photo** : l'audio et l'image ne se génèrent pas ici. La playlist, si
  (titre, artiste, année, réponse attendue). Le générateur produit la liste, pas le média.

## Pour le dossier

- Commits réguliers et lisibles, en français, un commit par unité de travail. La régularité
  de l'historique compte autant que le code.
- Un `JOURNAL.md` rempli après chaque session : ce que j'ai compris, ce qui a coincé, comment
  je l'ai résolu. Rappelle-le-moi si j'oublie.
- Repo public : aucun nom de client, aucune clé, aucune donnée personnelle.
