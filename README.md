# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH, historique de sécurité et décisions éditoriales**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.16 — Editorial Intelligence

La V0.16 ajoute une couche d’intelligence éditoriale **explicable et réversible** au-dessus de la V0.15.

### Favorite / Reject persistants

Les plages marquées dans SOURCE sont désormais stockées dans SQLite :

- Favorite ;
- Reject ;
- IN / OUT exacts ;
- coexistence de plusieurs plages sur un même rush ;
- suppression individuelle depuis l’Inspector.

Un Favorite ou Reject survit donc au rechargement du projet.

### Marqueurs éditoriaux

La timeline accepte désormais des marqueurs persistants :

- Note ;
- Décision ;
- Beat ;
- Vigilance.

Ils sont positionnés sur la règle de timeline et stockés par edit. Le raccourci `M` ouvre le composeur de marqueur.

### Editorial Source Selector

Depuis une source ou un clip STORY, **Alternatives** ouvre un tiroir latéral proposant d’autres prises.

Le classement est déterministe et explicable. Les signaux actuellement pris en compte sont :

- tags communs ;
- média canonique ;
- trailer-safe ;
- rating ;
- plages Favorite ;
- plages Reject ;
- niveau de spoiler ;
- statut média.

Chaque suggestion affiche :

- la prise ;
- la plage source conseillée ;
- les raisons du classement ;
- un aperçu ou la possibilité de charger la plage en SOURCE.

**Aucun remplacement de la Storyline n’est automatique.** Le Source Selector ne modifie pas le montage sans action explicite de l’utilisateur.

### Fondations conservées

- UX V0.15 : Focus Mode, Command Palette, Viewer Overlays ;
- Storyline magnétique et ripple ;
- connexions parent/enfant ;
- Canon et HARD/SOFT/OPEN Locks ;
- checkpoint persistant et Undo ;
- versions V001+ ;
- Tesseract bridge et authoring ;
- tests Python, JavaScript et Chromium.

### Limites connues

- le Source Selector travaille actuellement sur les métadonnées cataloguées, pas encore sur une analyse visuelle/sémantique automatique des images ;
- les filmstrips utilisent encore les médias locaux plutôt que des vignettes backend pré-calculées ;
- le point de connexion graphique reste à rendre directement manipulable ;
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
- `M` : Marker
- `Ctrl/Cmd+Z` : Undo

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `UX_GUIDE.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
