# PISTE Studio Local App — v0.17

L’application locale relie l’interface de montage au moteur PISTE Studio via FastAPI.

## Expérience utilisateur

- ASSEMBLE : Browser dominant ;
- EDIT : Browser + Viewer + Inspector + Storyline ;
- REVIEW : Viewer dominant et Timeline Index ;
- Viewer SOURCE / PROGRAM ;
- Focus Mode avec `~` ;
- Command Palette avec `Ctrl/Cmd+K` ;
- Overlays Viewer configurables ;
- Undo persistant avec `Ctrl/Cmd+Z`.

## Editorial Intelligence

- Favorite / Reject persistants ;
- Markers ;
- Source Selector explicable ;
- aucune modification automatique de la Storyline.

## Media Intelligence V0.17

### Analyser
Le bouton **Analyser** inspecte localement les vidéos cataloguées lorsque `ffmpeg` et `ffprobe` sont disponibles.

### Filmstrips
Des filmstrips JPEG sont mis en cache côté backend. Le Browser les affiche au repos puis repasse au skimming vidéo au survol.

### Prises proches
L’Inspector affiche les caractéristiques techniques du rush et propose **Prises proches**.

La proximité combine :
- empreinte perceptuelle visuelle ;
- nom de fichier ;
- durée.

### Continuité
Les tags structurés `character:`, `prop:`, `decor:` et `look:` enrichissent les raisons du Source Selector.

La V0.17 ne reconnaît pas automatiquement les personnages ou objets : elle exploite les tags existants et une empreinte visuelle générique.

## Backend connecté

- project.yaml, canon.yaml, locks.yaml ;
- catalogue SQLite ;
- media_analysis SQLite ;
- plages éditoriales et marqueurs ;
- cache filmstrip local ;
- streaming local des médias ;
- timeline schema v2 ;
- historique de checkpoints ;
- publication V001+ ;
- Tesseract vidéo + audio.

Aucun média du projet n’est envoyé vers un serveur distant par PISTE Studio.
