# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH et historique de sécurité**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.15 — UX Refinement

La V0.15 ne cherche pas à ajouter de puissance au moteur : elle rend l’outil plus agréable et plus rapide à utiliser.

### Interface

- Viewer plus dominant dans EDIT et REVIEW ;
- Browser à filmstrips plus grands et plus visuels ;
- réduction des bordures, badges et textes permanents ;
- hiérarchie visuelle plus proche d’une workstation de montage que d’un dashboard web ;
- Inspector plus sobre ;
- Storyline et pistes audio plus lisibles ;
- workspaces ASSEMBLE / EDIT / REVIEW davantage différenciés.

### Focus Mode

Chaque panneau principal peut devenir temporairement l’espace de travail complet :

- Browser ;
- Viewer ;
- Timeline ;
- Inspector.

Utiliser `~` sur le panneau courant, le bouton `⛶` ou Échap pour revenir.

### Command Palette

`Ctrl/Cmd+K` ouvre une palette de commandes pour accéder rapidement aux workspaces, modes Viewer, panneaux, Focus Mode, Undo, sauvegarde et publication sans multiplier les boutons permanents.

### Viewer Overlays

Le menu Overlays permet d’afficher/masquer :

- timecode / version ;
- état du mix ;
- plage IN/OUT en SOURCE.

Le mix est volontairement masqué par défaut pour alléger l’image.

### Fondations conservées

- Storyline magnétique ;
- ripple trim ;
- connexions parent/enfant ;
- HARD/SOFT/OPEN Locks ;
- checkpoint persistant et Undo ;
- timeline schema v2 ;
- versions V001+ ;
- Tesseract bridge et authoring ;
- tests Python, JavaScript et Chromium.

### Direction produit

Voir `UX_GUIDE.md` pour les règles de conception : contenu avant interface, progressive disclosure, couleurs sémantiques, Viewer-first et tests comportementaux réels.

### Limites connues

- Favorite/Reject n’est pas encore persisté côté backend ;
- le point de connexion reste un offset temporel ;
- les filmstrips utilisent encore le média local plutôt que des vignettes backend pré-calculées ;
- le premier test avec le vrai CLI Tesseract et les vrais rushes PISTE 0 reste à effectuer.

## Installation

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

Lancer :

    piste-studio-app --project /chemin/vers/PISTE_0

## Raccourcis principaux

- `1 / 2 / 3` : Assemble / Edit / Review
- `Ctrl/Cmd+K` : Command Palette
- `~` : Focus Mode
- `B` : Browser
- `I` : Inspector
- `P` : SOURCE / PROGRAM
- `F` : Favorite
- `X` : Reject
- `Ctrl/Cmd+Z` : Undo

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `UX_GUIDE.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
