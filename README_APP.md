# PISTE Studio Local App — v0.16

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

### Favorite / Reject
Les plages IN/OUT marquées sont stockées dans SQLite et réhydratées dans le Browser.

### Markers
`M` ouvre le composeur. Les marqueurs Note / Décision / Beat / Vigilance sont persistés par edit et affichés sur la règle.

### Editorial Source Selector
Depuis l’Inspector d’une source ou d’un clip STORY, **Alternatives** ouvre un tiroir de candidats. Chaque proposition contient une fenêtre source et des raisons de classement.

Le sélecteur est consultatif : aucun remplacement de la Storyline n’est automatique.

## Backend connecté

- project.yaml, canon.yaml, locks.yaml ;
- catalogue SQLite ;
- plages éditoriales et marqueurs SQLite ;
- streaming local des médias ;
- timeline schema v2 ;
- historique de checkpoints ;
- publication V001+ ;
- Tesseract vidéo + audio ;
- preview / filmstrip / export.

Aucun média du projet n’est envoyé vers un serveur distant par PISTE Studio.
