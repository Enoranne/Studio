# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions et PATCH**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.12 — interface orientée montage

La V0.12 remplace l’ancienne interface « tout visible en permanence » par une organisation inspirée de patterns éprouvés des NLE modernes, adaptée à PISTE Studio :

- workspaces `ASSEMBLE / EDIT / REVIEW` ;
- Browser à filmstrips et skimming ;
- Viewer intelligent `SOURCE / PROGRAM` ;
- Inspector contextuel ;
- Storyline vidéo principale + éléments connectés `TITLES / VO / MUSIC / SFX` ;
- Timeline Index `CLIPS / LOCKS / DECISIONS` ;
- panneaux Browser, Index et Inspector repliables ;
- sélection IN/OUT, Favorite/Reject, Canon, Trailer-safe, Spoiler ;
- publication de timeline en `V001+` puis authoring Tesseract.

La Storyline n’est **pas encore une vraie timeline magnétique** : le ripple automatique et l’attachement des éléments connectés sont prévus pour la V0.13.

### État technique

- master protégé par SHA-256 ;
- canon YAML et locks `HARD / SOFT / OPEN` ;
- catalogue média SQLite ;
- application locale FastAPI + UI navigateur ;
- timeline multi-pistes, drag/drop, trim, Source IN, gain et fades ;
- publication de timeline en versions `V001+` ;
- bridge Tesseract version-pinné ;
- authoring vidéo et audio transactionnel ;
- preview, filmstrip et export ;
- **29 tests automatisés**.

### Limites V0.12

- Favorite/Reject est encore un état UI de session, non persisté côté backend ;
- les vraies miniatures filmstrip ne sont pas encore pré-calculées : le Browser skim la vidéo locale lorsqu’elle est disponible ;
- ripple magnétique et connexions parent/enfant ne sont pas encore implémentés ;
- les fades audio ne sont pas encore transformés en enveloppes natives Tesseract ;
- les titres restent dans `timeline.json` ;
- le premier test avec le vrai CLI Tesseract et les vrais rushes PISTE 0 reste à effectuer sur la machine de l’utilisateur.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -e .
```

Lancer l’application :

```bash
piste-studio-app --project /chemin/vers/PISTE_0
```

Projet de démonstration :

```bash
piste-studio-app --project demo/PISTE_0_DEMO
```

## Workflow UI

1. `ASSEMBLE` : scanner, parcourir les rushes, définir IN/OUT, Favorite/Reject et ajouter à la Storyline.
2. `EDIT` : monter, trimmer, régler audio/titres, utiliser l’Inspector et l’Index.
3. `REVIEW` : privilégier le Viewer, les locks et les décisions.
4. **Enregistrer** puis **Publier** pour créer une version `V001+`.
5. **Tesseract** pour bootstrap + authoring de la version publiée.
6. **Preview / Export** pour contrôler la sortie.

## Tesseract

```bash
piste-studio tesseract configure \
  --root /chemin/vers/PISTE_0 \
  --expected-version 0.2.0
```

PISTE Studio refuse l’exécution si la version détectée ne correspond pas à la version épinglée.

## Tests

```bash
pip install -e '.[dev]'
pytest -q
```

État V0.12 :

```text
29 passed
```

Voir aussi `START_HERE.md`, `ROADMAP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
