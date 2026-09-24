# Rapport de validation — PISTE Studio V0.24.1

## Statut

**AUTOMATISATION DE RECETTE : VALIDÉE ✅**

**RECETTE RÉELLE PISTE 0 : À EXÉCUTER SUR LES MÉDIAS LOCAUX ⏳**

La V0.24.1 ajoute un contrôle de production reproductible sans prétendre remplacer la validation du film par un humain.

## Validation automatisée

Suite de référence après intégration V0.24.1 :

- **151 tests passés / 151** ;
- JavaScript : PASS ;
- Chromium / Playwright : PASS ;
- API / CLI : PASS.

## Critères contrôlés

Le rapport `production-run` vérifie sur la version timeline publiée :

- au moins 5 plans vidéo ;
- au moins un clip audio ;
- au moins un fade ;
- au moins une automation de volume ;
- au moins un titre / overlay ;
- un carton final ;
- un élément connecté à la Storyline ;
- un livrable Delivery existant avec conformité PASS.

Le rapport incorpore également le Production Readiness V0.24.0.

## Validation humaine obligatoire

Même si tous les critères machine sont présents, le statut maximum automatique est :

`AWAITING_HUMAN_REVIEW`

PISTE Studio ne déclare jamais seul que la recette film est réussie.

La validation finale doit confirmer notamment :

- ordre et rythme des plans ;
- raccords ;
- IN / OUT réellement voulus ;
- synchronisation et équilibre audio ;
- titres et carton final ;
- absence de média manquant ou substitué ;
- rendu Tesseract fidèle à la timeline ;
- livrable final regardable de bout en bout.

## Commande

```bash
piste-studio production-run \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --save
```

Une version précise peut être imposée avec `--version Vxxx`.

## API

- `GET /api/production-run`
- `POST /api/production-run` pour enregistrer le rapport.

## Prochaine étape

Exécuter le protocole `PRODUCTION_TEST_V0.24.md` sur un vrai extrait PISTE 0 de 30–60 secondes avec le Tesseract installé sur la machine de production.

La V0.24.1 ne sera déclarée totalement terminée qu'après cette exécution et la revue humaine du fichier final.
