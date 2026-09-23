# PISTE Studio Local App — v0.15

L’application locale relie l’interface de montage au moteur PISTE Studio via FastAPI.

## Expérience utilisateur

- `ASSEMBLE` : Browser dominant, Inspector et Index retirés pour privilégier la sélection.
- `EDIT` : Browser + Viewer + Inspector + Storyline.
- `REVIEW` : Viewer dominant et Timeline Index.
- Viewer `SOURCE / PROGRAM`.
- Focus Mode `~` sur Browser, Viewer, Timeline ou Inspector.
- Command Palette `Ctrl/Cmd+K`.
- Overlays Viewer configurables.
- Browser à filmstrips plus grands.
- Storyline magnétique et connexions parent/enfant.
- Undo persistant `Ctrl/Cmd+Z`.

## Backend connecté

- project.yaml, canon.yaml, locks.yaml ;
- catalogue SQLite ;
- streaming local des médias ;
- timeline persistante schema v2 ;
- historique de checkpoints ;
- publication en V001+ ;
- authoring Tesseract vidéo + audio ;
- preview / filmstrip / export.

## Principes

Voir `UX_GUIDE.md` : contenu avant interface, progressive disclosure, Viewer-first, couleurs sémantiques et validation des interactions dans Chromium.

Aucun média du projet n’est envoyé vers un serveur distant par PISTE Studio.
