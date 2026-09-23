# PISTE Studio Local App — v0.14

L’application locale relie l’interface de montage au moteur PISTE Studio via FastAPI.

## UX

- `ASSEMBLE` : Browser dominant ;
- `EDIT` : Browser + Viewer + Inspector + Storyline ;
- `REVIEW` : Viewer et Timeline Index prioritaires ;
- Viewer `SOURCE / PROGRAM` ;
- Browser filmstrip/skimming ;
- Inspector contextuel ;
- Storyline magnétique et connexions parent/enfant ;
- Timeline Index `CLIPS / LOCKS / DECISIONS` ;
- bouton Undo et raccourci `Ctrl/Cmd+Z`.

## Hardening V0.14

- checkpoint persistant avant une opération ripple/reorder validée ;
- restauration backend de la timeline précédente ;
- test Chromium réel de la navigation et des workspaces ;
- contrôle syntaxique de tous les JavaScript ;
- début de centralisation d’état via `PisteState`.

## Backend connecté

- `project.yaml`, `canon.yaml`, `locks.yaml` ;
- catalogue SQLite ;
- streaming local des médias ;
- timeline persistante schema v2 ;
- historique de checkpoints ;
- publication en `V001+` ;
- authoring Tesseract vidéo + audio ;
- preview / filmstrip / export.

Aucun média du projet n’est envoyé vers un serveur distant par PISTE Studio.
