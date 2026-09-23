# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH, historique de sécurité, décisions éditoriales et intelligence média locale**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.17 — Media Intelligence

La V0.17 ajoute une première couche d’analyse locale des rushes, conçue pour améliorer le Browser et le Source Selector sans envoyer les médias vers un service externe.

### Analyse technique locale

Lorsque `ffmpeg` et `ffprobe` sont disponibles, PISTE Studio peut extraire :

- durée ;
- résolution ;
- cadence ;
- codec vidéo ;
- pixel format ;
- codec audio ;
- canaux / sample rate ;
- débit / format conteneur.

Si la durée catalogue est absente, elle peut être complétée automatiquement depuis le probe.

### Filmstrips backend

PISTE Studio peut générer un filmstrip JPEG de plusieurs images dans le cache local du projet.

Le Browser utilise ce filmstrip comme vue de repos, puis repasse au **skimming vidéo** au survol lorsque la source locale est accessible.

Le cache n’est pas versionné dans Git.

### Empreinte visuelle locale

Pour chaque vidéo analysée, PISTE Studio échantillonne plusieurs images réduites en niveaux de gris et calcule une petite empreinte perceptuelle.

Cette empreinte sert uniquement à mesurer une **proximité visuelle globale entre prises**. Elle ne reconnaît pas un personnage, un accessoire ou une action.

### Prises proches

Depuis l’Inspector, **Prises proches** classe les autres rushes selon :

- empreinte visuelle lorsqu’elle est disponible ;
- tokens du nom de fichier ;
- proximité de durée.

L’interface indique quels signaux ont été utilisés.

### Source Selector enrichi

L’Editorial Source Selector de V0.16 utilise désormais aussi, avec un poids modéré :

- proximité visuelle locale ;
- proximité nom/durée ;
- facettes de continuité structurées dans les tags.

Exemples de tags de continuité :

- `character:malo`
- `prop:fisher`
- `decor:salon`
- `look:warm-tungsten`

Une correspondance peut donc produire des raisons comme :

- Continuité personnage : malo
- Continuité décor : salon
- Prise visuellement proche

La décision reste humaine et la Storyline n’est jamais remplacée automatiquement.

### Dégradation propre

Si `ffmpeg` ou `ffprobe` n’est pas installé :

- PISTE Studio reste utilisable ;
- l’analyse retourne explicitement `TOOLS_UNAVAILABLE` ;
- les fonctions éditoriales basées sur les métadonnées continuent de fonctionner.

## Fondations conservées

- Favorite / Reject persistants ;
- Markers ;
- Source Selector explicable ;
- UX Viewer-first, Focus Mode, Command Palette et Overlays ;
- Storyline magnétique et ripple ;
- Canon et HARD/SOFT/OPEN Locks ;
- checkpoint / Undo ;
- versions V001+ ;
- Tesseract bridge et authoring ;
- tests Python, JavaScript et Chromium.

## Ce que V0.17 ne prétend pas encore faire

La reconnaissance automatique de **Malo**, du **Fisher Price**, d’un décor précis, d’une émotion ou d’une action n’est pas encore implémentée.

La continuité sémantique repose actuellement sur les tags structurés du catalogue. Une future couche de vision pourra proposer ces tags automatiquement, mais devra conserver la même politique : résultats explicables, validation humaine et traitement local ou explicitement autorisé.

## Dépendances média optionnelles

L’analyse V0.17 utilise `ffmpeg` et `ffprobe` s’ils sont présents sur la machine. Ils ne sont pas installés automatiquement par le package Python.

## Installation

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

Lancer :

    piste-studio-app --project /chemin/vers/PISTE_0

Dans l’interface :

1. **Scanner** catalogue les médias.
2. **Analyser** lance l’analyse locale et génère les filmstrips.
3. Sélectionner un rush affiche les informations Media Intelligence.
4. **Prises proches** compare les prises.
5. **Alternatives** ouvre le Source Selector enrichi.

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `UX_GUIDE.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
