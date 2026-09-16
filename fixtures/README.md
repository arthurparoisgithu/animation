# Fixtures : de vraies réponses de modèle, enregistrées une fois

Ce dossier est **vide tant qu'aucune campagne d'enregistrement n'a été lancée**.
Les fichiers qui s'y trouvent sont des réponses brutes de Haiku, telles qu'il les
a produites — avant toute validation.

## À quoi ça sert

Un appel de modèle coûte de l'argent et n'est jamais deux fois identique. Les
fixtures résolvent les deux problèmes d'un coup :

- **le coût** : une seule campagne payante, rejouée gratuitement ensuite par les
  tests, par la démo en ligne et par quiconque clone le dépôt ;
- **le déterminisme** : les mêmes entrées donnent les mêmes sorties, donc un
  test qui passe aujourd'hui passera demain ;
- **la preuve** : ce sont de vraies sorties de modèle, défauts compris. Une
  fixture que la validation rejette vaut mieux qu'un cas de test inventé — elle
  montre que le problème est réel, pas théorique.

## Comment les produire

```bash
# Une fois, avec une clé d'API. C'est la seule commande qui coûte.
python -m scripts.campagne --enregistrer
```

Puis committer les fichiers produits.

## Comment les rejouer

```bash
python -m scripts.campagne --rejouer              # remplit la base de démo
python -m scripts.campagne --rejouer --sans-base  # vérifie seulement
```

Ou, pour toute l'application, `MODE_MODELE=rejeu` dans `.env`.

## Format d'un fichier

Le nom combine le début du prompt et une empreinte de `(modèle, prompt)`, pour
rester lisible tout en restant unique.

```json
{
  "modele": "claude-haiku-4-5-20251001",
  "empreinte": "a1b2c3d4",
  "enregistre_le": "2026-09-16T15:00:00+00:00",
  "prompt": "Tu generes 6 questions pour un jeu d'animation…",
  "reponse": "[{\"question\": …}]"
}
```

Le prompt est conservé : une fixture doit pouvoir être relue par un humain,
sinon elle ne prouve rien.

## Ce qui n'a pas sa place ici

Des réponses fabriquées à la main. Les cas volontairement cassés vivent en dur
dans `tests/`, où l'on voit qu'ils sont inventés. Mélanger les deux ferait
passer du contenu fictif pour une mesure réelle.
