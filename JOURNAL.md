# Journal de développement

Ce que j'ai compris, ce qui a coincé, comment je l'ai résolu. Rempli après chaque session.

---

## Session 1 — mise en place complète du socle au mode projection

### Ce qui a été fait

Les onze étapes prévues dans le cahier des charges, dans l'ordre : socle FastAPI, schémas
Pydantic et normalisation, générateur en script manuel, validation déterministe, tests,
intégration continue, juge, base de données, API, interface, README.

120 tests passent, dont 13 contre un vrai Postgres.

### Ce que Python fait autrement que JavaScript

**L'environnement virtuel.** `npm install` crée un `node_modules/` local au projet,
l'isolation est automatique. `pip install` écrit par défaut dans le Python du système,
partagé par tous les projets. D'où le `venv` : un dossier avec son propre Python et son
propre pip. Tant que le prompt n'affiche pas `(.venv)`, tout `pip install` part dans le
système.

**FastAPI ne sert pas tout seul.** Contrairement à Express qui fait les deux, FastAPI
décrit l'application et `uvicorn` l'exécute. D'où `uvicorn app.main:app` — « dans le
module `app.main`, prends la variable `app` ».

**Les décorateurs.** `@app.get("/")` au-dessus d'une fonction se lit comme
`app.get("/", fonction)` en Express, écrit à l'envers.

**Les annotations de types servent vraiment à quelque chose.** FastAPI génère `/docs`,
valide les entrées et sérialise les sorties à partir d'elles. Ce ne sont pas des
commentaires comme les types TypeScript effacés à la compilation.

### Ce qui a coincé

**1. `normaliser` ne suffisait pas à comparer deux réponses.**

Trois tests ont échoué d'un coup au premier passage. Cause unique : `normaliser("L'Everest")`
donne `"l everest"` — l'apostrophe devient un espace et l'article élidé reste comme un mot
à part entière. Résultat : « L'Everest » et « Everest » étaient deux réponses différentes,
et un item parfaitement correct partait en régénération.

Solution : `normaliser` reste la fonction générale, et j'ai ajouté `cle()` qui normalise
*puis* retire les déterminants de tête. Les propositions et la bonne réponse se comparent
avec `cle()`, les formules interdites se cherchent dans le texte normalisé brut.

Ce n'est pas un détail cosmétique : chaque régénération inutile est un appel payé pour rien.

**2. Le compteur de tentatives rapportait toujours une tentative de trop.**

`resultat.tentatives = tentative` était placé avant le test de sortie de boucle. Un lot
valide du premier coup affichait donc « 2 tentatives ». Trouvé par un test qui vérifiait
exactement ça. Correction : déplacer l'affectation après le `break`.

**3. Le taux de rejet était faussé.**

Un item violant trois règles produisait trois entrées de rejet. Le taux se serait mis à
dépasser 100 % sur un lot bien cassé, et le seuil d'escalade vers Sonnet n'aurait plus
voulu dire grand-chose. Le taux compte des **items**, pas des motifs. Correction : un seul
rejet par item, les motifs regroupés dans une seule chaîne — on garde le diagnostic
complet sans fausser la mesure.

**4. Les accolades des gabarits cassent `str.format()`.**

Les gabarits se terminent tous par « Réponds uniquement par un tableau JSON d'objets
{question, propositions, bonne_reponse, anecdote} ». `str.format()` prend ces accolades
pour des placeholders et lève `KeyError`. J'ai écrit `remplir_gabarit()`, qui substitue
par expression régulière uniquement les placeholders connus et laisse tout le reste
intact.

J'ai reproduit exactement le même piège dans le gabarit du juge avant de m'en apercevoir.

**5. Postgres ne pouvait pas deviner le type des paramètres.**

La requête de filtrage du catalogue utilise `WHERE (:public IS NULL OR publics @> ...)`
pour rendre chaque filtre optionnel. Postgres refuse : `could not determine data type of
parameter $1`. Sans autre indice que `IS NULL`, il n'a rien pour inférer le type.

Premier réflexe : écrire `:public::text`. Nouvelle erreur, plus déroutante — cette fois
c'est SQLAlchemy qui se plaint, parce qu'il lit `:public::text` comme un nom de paramètre
et non comme un cast. Solution : `CAST(:public AS text)`, qui n'a aucune des deux
ambiguïtés.

**6. La CI est tombée deux fois, pour deux raisons que le local ne pouvait pas montrer.**

D'abord `FATAL: role "root" does not exist`, répété trois fois. Le *health check* du
service Postgres, `pg_isready` sans argument, reprend l'utilisateur du système — `root` sur
le runner — qui n'existe pas en base. Le service n'était donc jamais déclaré sain et le job
s'arrêtait avant d'installer quoi que ce soit : aucun test n'avait tourné. Corrigé avec
`pg_isready -U animation -d animation`.

En écrivant ce correctif j'ai failli mettre un commentaire `#` à l'intérieur du bloc `>-`
des options YAML. Dans un bloc scalaire, `#` n'est pas un commentaire : il serait entré
dans la chaîne passée à Docker.

Ensuite `ModuleNotFoundError: No module named 'app'`, sur les huit modules de test.
C'était une erreur de méthode de ma part : je lançais `python -m pytest` en local, et le
`-m` ajoute le dossier courant au `sys.path`. La CI lance `pytest` tout court, qui ne le
fait pas. Le projet marchait donc chez moi pour une raison qui n'existait pas sur le
runner.

Corrigé par `pythonpath = .` dans `pytest.ini`, et surtout : **désormais je vérifie avec
la commande exacte de la CI**, pas avec une variante qui m'arrange. J'ai reproduit
l'échec en retirant la ligne, puis vérifié qu'il disparaissait en la remettant.

### Décisions prises en cours de route

- **Alembic plutôt qu'un simple `create_all()`.** La migration initiale est écrite à la
  main et non autogénérée : l'ordre de création des types `ENUM` par rapport aux tables
  mérite d'être explicite, et ça m'évite de dépendre d'une base en marche pour produire la
  migration.
- **Le seed est idempotent** (`ON CONFLICT DO UPDATE`). Ça permet de corriger un gabarit de
  prompt et de rejouer le seed sans repartir d'une base vide — et je vais corriger ces
  gabarits souvent.
- **Un juge illisible rejette tout le lot.** La tentation était d'accepter par défaut quand
  le juge ne répond pas correctement. C'est exactement l'inverse qu'il faut faire : du
  contenu non contrôlé ne doit pas passer.
- **Les tests de l'API sont ignorés sans Postgres, pas mis en échec.** La suite de
  validation, elle, doit pouvoir tourner n'importe où sans rien installer.
- **Le JSON injecté dans la page de projection est échappé.** Un item contenant `</script>`
  fermerait le bloc et casserait la page. Les chevrons et l'esperluette partent en
  `<`, `>`, `&`.

### Ce que je retiens pour l'entretien

Le test qui compte le plus dans ce projet n'est pas celui qui vérifie qu'une question
valide passe. C'est celui qui vérifie qu'**un lot entièrement invalide ne déclenche aucun
appel au juge**. Il encode la décision d'architecture — le gratuit avant le payant — et il
casserait immédiatement si quelqu'un inversait les deux niveaux.

### Reste à faire

- [ ] Lancer une vraie génération avec une clé d'API et mesurer les taux de rejet réels
      par format. Les seuils à 20 % sont pour l'instant théoriques.
- [ ] Ajuster les gabarits en fonction de ces taux, et noter ici chaque ajustement.
- [ ] Décider si un format dépasse durablement 20 % et doit passer en Sonnet.
- [ ] Déploiement, avec `CODE_GENERATION` renseigné pour protéger la génération réelle.
