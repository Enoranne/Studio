# PISTE Studio Local App — v0.18

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

## Media Intelligence

- ffprobe / ffmpeg local ;
- filmstrips backend ;
- empreinte perceptuelle ;
- prises proches ;
- continuité structurée via tags.

## Semantic Vision V0.18

La vision locale est optionnelle.

### Références

Les tags déjà validés servent de références :

- `character:malo`
- `prop:fisher`
- `decor:salon`
- `look:warm-tungsten`

Un rush doit avoir un profil vision READY avant de pouvoir recevoir des propositions.

### Propositions

**Proposer continuité** compare le rush aux références de même facette.

Chaque proposition reste `PENDING` jusqu’à une décision utilisateur :

- Accepter → ajoute le tag ;
- Rejeter → mémorise le refus.

Aucune proposition ne modifie la Storyline.

### Modèle local

Installer l’extra :

    pip install -e '.[vision]'

Le modèle n’est pas téléchargé automatiquement. Si son cache est absent, l’interface peut demander une autorisation explicite de téléchargement. Seul le modèle est téléchargé ; les frames du projet restent locales.

## Backend connecté

- project.yaml, canon.yaml, locks.yaml ;
- catalogue SQLite ;
- media_analysis ;
- semantic_profiles ;
- semantic_tag_proposals ;
- plages éditoriales et marqueurs ;
- cache filmstrip / vision local ;
- timeline schema v2 ;
- historique de checkpoints ;
- publication V001+ ;
- Tesseract vidéo + audio.

Aucun média du projet n’est envoyé vers un serveur distant par PISTE Studio.
