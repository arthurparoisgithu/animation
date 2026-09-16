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

---

## Session 2 — enregistrer une fois, rejouer toujours

### Le problème à résoudre

Je n'ai pas encore lancé une seule génération réelle, et chaque appel coûte. Si le
projet ne sait fonctionner qu'avec une clé d'API active, alors : les tests dépendent du
réseau, la démo en ligne fait payer ma clé pour les visiteurs, et un recruteur qui clone
le dépôt ne voit rien tourner.

### Ce que j'ai compris sur le coût

En vérifiant la tarification réelle de Haiku 4.5 (1 $ / 5 $ par million de tokens),
j'arrive à **environ 1 centime par jeu de 10 items**, pas un demi : mon estimation
initiale oubliait l'appel au juge. Le juge coûte ~0,30 ¢, la génération ~0,64 ¢. Cent
jeux ≈ 1 €. Ça ne change pas la décision, mais c'est un chiffre que je dois pouvoir
annoncer juste.

Deux leviers écartés après vérification, et savoir *pourquoi* on les écarte vaut mieux
que les appliquer au hasard : le **Batch API** (−50 %) est asynchrone, donc inutilisable
pour une génération à la demande ; le **cache de prompt** ne s'applique pas, mes gabarits
faisant quelques centaines de tokens, sous le minimum cachable.

### La solution : une couture, trois implémentations

`app/transport.py`. Le générateur et le juge continuent d'appeler `modele.appeler()` ;
c'est cette fonction qui délègue au transport actif.

- `TransportApi` — l'appel réel, le seul qui coûte.
- `TransportEnregistre` — décore un transport et écrit la réponse brute sur disque.
- `TransportRejeu` — relit le disque, ne touche jamais au réseau.

Ce que j'aime dans ce découpage : **aucun `if mode == ...` dans le générateur**. La
logique métier ignore complètement d'où vient la réponse. C'est le genre de séparation
que je saurai défendre.

### Décisions de conception

**L'empreinte inclut le modèle, pas seulement le prompt.** La même question posée à
Haiku et à Sonnet sont deux appels différents ; rejouer l'un à la place de l'autre serait
une erreur silencieuse, donc invisible.

**Le nom de fichier reste lisible** : début du prompt en slug + empreinte courte. Sinon
les fixtures s'appellent `a1b2c3d4.json` et ne sont inspectables qu'une par une. Une
fixture doit pouvoir être relue par un humain, sinon elle ne prouve rien.

**On enregistre la réponse brute, avant validation.** Une sortie rejetée est la fixture
la plus intéressante du projet : c'est elle qui prouve que la validation attrape quelque
chose de réel et pas de théorique.

**Une fixture absente lève une erreur, elle ne retombe pas sur un appel réel.** C'est le
point le plus important du module. Un repli silencieux vers l'API ferait dépenser une
démo publique sans prévenir.

### Ce qui a coincé

**Le trou que je n'avais pas vu.** Une fois le mode rejeu en place, j'ai testé le
scénario réel : un visiteur de la démo saisit un thème jamais généré. `FixtureIntrouvable`
remontait jusqu'à FastAPI sans être rattrapée — **erreur 500**. Or c'est le cas d'usage
normal d'une démo publique, pas un cas limite. Corrigé en 503 avec un message qui dit
quoi faire. Leçon : tester le mode dégradé avec le scénario du visiteur, pas seulement
avec le mien.

**J'ai failli committer de fausses fixtures.** Pour prouver la chaîne sans clé, j'ai
écrit un faux modèle produisant du JSON plausible, et la campagne a généré 20 fixtures.
Elles marchent parfaitement — et elles sont fausses. Les committer aurait fait passer du
contenu fabriqué pour une mesure réelle, exactement ce que le projet reproche aux modèles.
Elles sont restées dans le scratchpad ; `fixtures/` ne contient que son README tant
qu'aucune campagne réelle n'a tourné.

### Vérifications faites

Enregistrement puis rejeu sur les dix formats : **20 appels à l'enregistrement, 0 au
rejeu**, résultats identiques au format près. Puis la campagne contre une vraie base :
10 jeux, 60 items, 10 rejets enregistrés, sans un seul appel réseau.

133 tests passent, dont 14 contre Postgres.

### Reste à faire

- [ ] **La campagne réelle**, avec une clé, sur mon poste : `python -m scripts.campagne
      --enregistrer`. C'est la seule chose qui manque encore au projet.
- [ ] Regarder les taux de rejet obtenus et ajuster les gabarits en conséquence.
- [ ] Mettre en ligne en `MODE_MODELE=rejeu`, et obtenir un lien à mettre dans le
      dossier de candidature.

---

## Session 3 — préparation du déploiement

### Ce qui a été fait

`Dockerfile` et `fly.toml` : le déploiement est décrit par des fichiers versionnés, pas
par une suite de clics dans une interface. La `release_command` joue les migrations puis
le seed avant chaque mise en ligne.

### Trois bugs trouvés en préparant le déploiement

Aucun n'était visible en développement. Les trois ne se déclenchent qu'en conditions
réelles d'hébergement — c'est la leçon de cette session.

**1. `postgres://` contre `postgresql+psycopg://`.** Fly, Render et Heroku créent une
variable `DATABASE_URL` commençant par `postgres://`. SQLAlchemy 2 exige un pilote
explicite et refuse cette forme. Deux options : demander à l'utilisateur de définir une
variable différente de celle que l'hébergeur crée tout seul, ou réécrire l'URL. J'ai
choisi de réécrire — c'est l'application qui s'adapte à l'hébergeur, pas l'inverse.

**2. Le `%` qui faisait échouer la migration.** Celui-là m'a coûté du temps et il est
instructif. `alembic/env.py` écrivait l'URL dans la configuration Alembic via
`config.set_main_option()`. Or cette configuration passe par `configparser`, qui traite
`%` comme une syntaxe d'interpolation. Un mot de passe contenant un `%` — et les
hébergeurs en génèrent — faisait donc planter la migration **avant même la tentative de
connexion**, avec un message parlant d'interpolation qui ne suggère rien de ce qui se
passe vraiment.

Corrigé en construisant le moteur directement, sans passer par `configparser`. Et pour
que le cas reste couvert, **la CI utilise maintenant un mot de passe contenant un `%`**
(`anim%pass`, encodé `anim%25pass` dans l'URI). J'ai vérifié les deux sens : cette URL
fait bien échouer l'ancien code, et passe avec le nouveau. Un garde-fou qu'on n'a pas vu
échouer ne garde rien.

**3. Mon conftest ignorait silencieusement quatorze tests.** En lançant la suite avec une
URL au format hébergeur, j'ai vu « 125 passed, 14 skipped » alors que la base tournait.
`_base_joignable()` construisait le moteur sans passer par la normalisation de
`Reglages` : la connexion échouait, l'exception était avalée, et les tests de base
étaient ignorés sans un mot.

Deux corrections. La normalisation, d'abord. Mais surtout le **changement de
sémantique** : on n'ignore plus que si `DATABASE_URL` n'est pas définie du tout. Si elle
est définie et que la base ne répond pas, l'erreur remonte. Une variable renseignée qui
ne marche pas est un problème à signaler, pas à contourner.

C'est la troisième fois dans ce projet que je tombe sur la même famille de problème : du
code qui passe pour une mauvaise raison. Le `python -m pytest` de la CI, le repli
silencieux vers l'API si une fixture manque, et maintenant ce skip. À chaque fois, le
correctif consiste à **rendre l'échec bruyant plutôt que confortable**.

### Ce que je n'ai pas pu vérifier

L'image Docker n'a pas été construite : le registre Docker Hub est bloqué par la
politique réseau de l'environnement où je travaille. J'ai validé tout le reste — le
`fly.toml` se parse, chaque chemin `COPY` existe, la `release_command` et la commande de
démarrage tournent réellement contre Postgres avec une URL au format Fly. Le `docker
build` reste à faire au premier déploiement.

### Vérifications faites

139 tests passent avec base, 125 sans. La commande de release crée les trois tables et
insère les dix formats. Le serveur répond sur le port 8080 : `/sante` pour le check de
Fly, l'accueil, le catalogue filtré, et un 503 lisible pour un thème absent des fixtures.

---

## Session 4 — revue avant mise en ligne

Le dépôt va devenir public et l'application accessible : j'ai relu le code en me
demandant ce qu'un visiteur mal intentionné, ou simplement moi un soir de fatigue,
pourrait en faire.

### Le vrai problème : la protection échouait « ouvert »

`_verifier_code` ne vérifiait le code *que s'il était renseigné*. Une instance déployée en
`MODE_MODELE=api` avec un `CODE_GENERATION` oublié laissait donc n'importe quel visiteur
déclencher des appels facturés sur ma clé — précisément ce que mon cahier des charges
cherchait à éviter.

Le défaut était à l'envers. La configuration manquante ouvrait la porte au lieu de la
fermer. Corrigé : en mode `api`, un code est **obligatoire**, et son absence produit un
403 qui dit quoi faire. En mode `rejeu` rien n'est exigé, puisque rien n'est facturé.

La règle que j'en retiens : **une protection qui ne s'applique que si on a pensé à la
configurer ne protège rien.** C'est l'absence de configuration qui doit bloquer.

Ce changement a cassé neuf tests d'un coup — ceux qui reposaient sur l'ancien
comportement permissif. C'était le bon signe : ils passaient tous parce que la porte était
ouverte. Ils configurent maintenant l'application comme une vraie instance.

### Deux corrections plus petites

**Comparaison du code en temps constant.** `!=` s'arrête au premier caractère différent,
donc le temps de réponse renseigne sur le nombre de caractères corrects.
`secrets.compare_digest` ne s'arrête pas. Sur un code de démo l'enjeu est faible, mais
c'est l'habitude qui compte, et elle ne coûte qu'un import.

**Une fragilité dans le `.dockerignore`, que j'avais introduite moi-même.** J'excluais
`*.md` avec une exception pour `fixtures/README.md`. Or `fixtures/` ne contient *que* ce
README tant qu'aucune campagne n'a tourné : si l'exception sautait, le dossier devenait
vide dans le contexte de build et `COPY fixtures/` échouait. Pour quelques kilo-octets de
Markdown, et sur un build que je ne peux pas tester ici. Règle supprimée, et j'ai simulé
le contexte de build fichier par fichier pour vérifier qu'aucun `COPY` ne pointe vers du
vide.

### Une limite assumée

`PATCH /api/jeux/{id}/favori` n'est pas authentifié : sur la démo, n'importe qui peut
basculer une étoile. Je le laisse. L'effet est nul, et ajouter une authentification pour
ça reviendrait à construire un système de comptes que le produit n'a pas. C'est noté dans
le README plutôt que masqué — une limite écrite vaut mieux qu'une limite découverte par
quelqu'un d'autre.

### Vérifications faites

143 tests passent (17 contre Postgres). Les deux modes vérifiés sur l'application
réellement lancée : `api` sans code répond 403 avec le message d'explication, `rejeu`
sans code fonctionne normalement.
