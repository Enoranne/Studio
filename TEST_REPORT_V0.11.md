# PISTE Studio v0.11 — Rapport de validation

Date : 23 septembre 2026

## Résultat

- Python : **27 tests passés / 27** (`pytest -q`).
- JavaScript : `node --check` valide pour `piste_studio/ui/editor.js` et `piste_studio/ui/backend.js`.
- Packaging Python hors-ligne : installation réussie avec `--no-build-isolation --no-deps`.
- Ressources UI embarquées vérifiées après installation : `index.html`, `style.css`, `editor.js`, `backend.js`.

## Chaîne couverte

- protection du master par SHA-256 ;
- HARD / SOFT / OPEN locks ;
- catalogue média SQLite et métadonnées ;
- brief teaser, versioning et PATCH ;
- persistance et validation de timeline multi-pistes ;
- publication de la timeline en `V001+` ;
- API locale FastAPI ;
- bridge Tesseract version-pinné ;
- bootstrap Tesseract ;
- authoring transactionnel vidéo + audio ;
- `activeRange` / `sourceRange` distincts ;
- gain statique audio ;
- preview / filmstrip / export ;
- protection contre une reconstruction silencieuse d'une version déjà authorée.

## Tesseract

Les tests Tesseract utilisent un **faux CLI contrôlé** reproduisant les contrats nécessaires de la documentation officielle v0.2.0. Cela permet de tester le bridge et les transactions sans prétendre avoir exécuté le moteur Mirage réel dans cet environnement.

Le premier essai de bout en bout avec le **CLI Tesseract réel et de vrais rushes PISTE 0** reste à effectuer sur la machine de l'utilisateur.

## Limites connues de v0.11

- les fades audio sont conservés dans `timeline.json` et dans le manifeste, mais ne sont pas encore transformés en enveloppes de volume natives Tesseract ;
- les titres restent éditoriaux dans `timeline.json` et ne sont pas encore matérialisés en couches texte Tesseract ;
- le mix navigateur est utile à la prévisualisation mais n'est pas considéré comme un rendu frame-accurate ;
- Tesseract n'est ni fourni, ni modifié, ni redistribué par PISTE Studio.
