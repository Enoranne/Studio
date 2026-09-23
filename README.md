# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH et historique de sécurité**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.14 — Hardening

La V0.14 consolide les fondations avant de reprendre l’ajout de fonctions éditoriales.

### Fiabilité

- correction de la navigation réelle `Montage / Canon & Locks / Versions` ;
- démo migrée vers le schéma timeline v2 ;
- checkpoint persistant avant les opérations magnétiques ;
- Undo persistant via `Ctrl/Cmd+Z` et bouton `Undo` ;
- restauration de la timeline précédente côté backend ;
- les checkpoints suivent les branches d’édition : après un Undo, une nouvelle opération abandonne la branche future ;
- état d’historique exposé par l’API.

### Tests

La CI contrôle désormais trois niveaux :

1. tests Python du moteur et de l’API ;
2. `node --check` sur tous les modules JavaScript ;
3. **Chromium réel via Playwright**, avec clics sur les vues et workspaces et surveillance des erreurs de page.

Ce troisième niveau a déjà détecté une régression que les tests syntaxiques ne voyaient pas.

### Architecture UI

Un store central `PisteState` a été introduit pour commencer à réduire les variables globales. La migration reste volontairement progressive : workspace, mode SOURCE/PROGRAM, filtre Browser et mode Index y passent d’abord.

### Storyline

Les acquis V0.13 restent actifs :

- déplacement d’un plan STORY = réordonnancement magnétique ;
- ripple trim IN/OUT ;
- connexions parent/enfant pour TITLES / VO / MUSIC / SFX ;
- maintien de l’`anchorOffset` ;
- validation serveur des effets domino contre les locks ;
- migration prudente des anciennes timelines.

### Limites encore connues

- Favorite/Reject n’est pas encore persisté côté backend ;
- le point de connexion reste un offset temporel, pas encore un marqueur graphique manipulable ;
- les fades audio ne sont pas encore matérialisés en enveloppes natives Tesseract ;
- le premier test de bout en bout avec le **vrai CLI Tesseract et les vrais rushes PISTE 0** reste à effectuer sur la machine de l’utilisateur ;
- le refactor du state JavaScript n’est qu’amorcé.

## Installation

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

Lancer l’application :

    piste-studio-app --project /chemin/vers/PISTE_0

## Workflow

1. ASSEMBLE : parcourir les rushes et définir les plages source.
2. EDIT : construire/réordonner la Storyline, ripple trim, connecter audio/titres.
3. Chaque opération magnétique validée crée un checkpoint.
4. Ctrl/Cmd+Z ou Undo restaure le checkpoint précédent.
5. REVIEW : contrôler Viewer, Index, Locks et décisions.
6. Enregistrer puis Publier pour créer V001+.
7. Tesseract pour matérialiser la version publiée.

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
