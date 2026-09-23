# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par canon, locks, versions et PATCH. Le projet garde Tesseract séparé : Tesseract est un moteur externe installé par l’utilisateur, jamais redistribué ni modifié ici.

## V0.11

La timeline de l’interface peut désormais être enregistrée, publiée en version `V001+`, convertie en projet Tesseract, prévisualisée et exportée depuis l’application locale.

`timeline.json` est l’état éditorial autoritaire d’une version publiée. L’authoring crée des couches Tesseract natives `Video` et `Audio`, avec `activeRange` et `sourceRange` distincts. Le master et les médias sources ne sont jamais modifiés.

### État actuel

- master protégé par SHA-256 ;
- canon YAML et locks `HARD / SOFT / OPEN` ;
- catalogue média SQLite ;
- Media Library visuelle et timeline multi-pistes ;
- drag/drop, trim, Source IN, gain et fades ;
- application locale FastAPI + UI navigateur ;
- publication de timeline en versions `V001+` ;
- bridge Tesseract version-pinné ;
- authoring vidéo et audio transactionnel ;
- preview, filmstrip et export ;
- 27 tests automatisés.

### Limites V0.11

- les fades audio sont tracés mais pas encore transformés en enveloppes natives Tesseract ;
- les titres restent dans `timeline.json` ;
- aucun composant Tesseract n’est inclus ;
- le premier test avec le vrai CLI Tesseract et les vrais rushes PISTE 0 reste à effectuer sur la machine de l’utilisateur.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
piste-studio-app --project /chemin/vers/PISTE_0
```

Projet de démonstration : `piste-studio-app --project demo/PISTE_0_DEMO`.

## Workflow UI

1. Scanner projet
2. Monter et enregistrer
3. Publier version
4. Authorer Tesseract
5. Preview / Export

Voir `START_HERE.md`, `ROADMAP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
