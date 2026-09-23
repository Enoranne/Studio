# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions et PATCH**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.13 — Storyline magnétique

La V0.13 transforme la Storyline de la V0.12 en un véritable système de montage ripple avec connexions éditoriales :

- déplacement d’un plan STORY = **réordonnancement magnétique** ;
- les plans STORY se recalent sans trou à partir du point de départ de la Storyline ;
- trim IN/OUT d’un plan STORY = **ripple trim** ;
- les plans situés en aval se décalent automatiquement ;
- TITLES / VO / MUSIC / SFX peuvent être reliés à un plan parent ;
- un élément connecté conserve son anchorOffset quand son parent se déplace ;
- l’Inspector permet d’attacher, changer de parent ou détacher un élément ;
- supprimer un plan referme la Storyline ; ses anciens enfants sont détachés plutôt que supprimés ;
- l’API valide la timeline transformée et vérifie les HARD/SOFT LOCKS avant validation ;
- les anciennes timelines V0.12 ne sont pas modifiées silencieusement au chargement.

L’interface conserve les acquis V0.12 : workspaces ASSEMBLE / EDIT / REVIEW, Browser à filmstrips, Viewer SOURCE / PROGRAM, Inspector contextuel, Timeline Index, panneaux repliables, sélection IN/OUT, Favorite/Reject, Canon, Trailer-safe et Spoiler.

### Modèle de connexion

Un élément connecté stocke parentClipId, anchorOffset et connectionMode=follow. Si le parent se décale de +3 s, l’enfant suit de +3 s tout en conservant son offset relatif.

### Sécurité

La V0.13 distingue deux validations : une validation locale immédiate (bornes, collisions, durée source, pistes verrouillées, cohérence des connexions), puis une validation serveur du schéma de timeline et des locks du projet. Un ripple qui ferait traverser un HARD LOCK à un plan, un titre ou un son est refusé.

### État technique

- master protégé par SHA-256 ;
- canon YAML et locks HARD / SOFT / OPEN ;
- catalogue média SQLite ;
- application locale FastAPI + UI navigateur ;
- Storyline magnétique + connexions parent/enfant ;
- timeline multi-pistes, drag/drop, ripple trim, Source IN, gain et fades ;
- publication de timeline en versions V001+ ;
- bridge Tesseract version-pinné ;
- authoring vidéo et audio transactionnel ;
- preview, filmstrip et export ;
- CI Python + contrôle syntaxique JavaScript.

### Limites V0.13

- Favorite/Reject reste un état UI de session, non persisté côté backend ;
- le point de connexion est actuellement un offset temporel, pas encore un marqueur graphique déplaçable indépendant ;
- les fades audio ne sont pas encore transformés en enveloppes natives Tesseract ;
- les titres restent décrits dans timeline.json ;
- le premier test avec le vrai CLI Tesseract et les vrais rushes PISTE 0 reste à effectuer sur la machine de l’utilisateur.

## Installation

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

Lancer l’application :

    piste-studio-app --project /chemin/vers/PISTE_0

## Workflow

1. ASSEMBLE : définir les plages source et construire la Storyline.
2. EDIT : réordonner les plans, trimmer en ripple et connecter VO/SFX/TITLES.
3. REVIEW : contrôler Viewer, Index, Locks et décisions.
4. Enregistrer puis Publier pour créer V001+.
5. Tesseract pour matérialiser la version publiée.
6. Preview / Export.

## Tests

    pip install -e '.[dev]'
    pytest -q
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check

Voir aussi START_HERE.md, ROADMAP.md, THIRD_PARTY.md et LICENSE_NOTE.md.
