# PISTE Studio Local App — v0.12

L’application locale relie l’interface de montage au moteur PISTE Studio via FastAPI.

## UX V0.12

- `ASSEMBLE` : Browser dominant ;
- `EDIT` : Browser + Viewer + Inspector + Timeline ;
- `REVIEW` : Viewer et Timeline Index prioritaires ;
- Viewer `SOURCE / PROGRAM` ;
- Browser filmstrip/skimming ;
- Inspector contextuel ;
- Timeline Index `CLIPS / LOCKS / DECISIONS`.

## Backend connecté

- `project.yaml`, `canon.yaml`, `locks.yaml` ;
- catalogue SQLite ;
- streaming local des médias ;
- timeline persistante ;
- publication en `V001+` ;
- authoring Tesseract vidéo + audio ;
- preview / filmstrip / export.

Aucun média du projet n’est envoyé vers un serveur distant par PISTE Studio.
