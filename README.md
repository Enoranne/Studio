# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH, historique de sécurité, décisions éditoriales, intelligence média locale et continuité visuelle validée humainement**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.18 — Semantic Vision & Continuity

La V0.18 ajoute une couche de vision sémantique **optionnelle et locale** au-dessus de la Media Intelligence V0.17.

### Principe

PISTE Studio n’essaie pas de reconnaître un personnage uniquement parce qu’il connaît son nom.

La continuité spécifique repose sur des **références visuelles déjà validées** :

- un rush tagué `character:malo` devient une référence visuelle de Malo ;
- un rush tagué `prop:fisher` devient une référence de cet accessoire ;
- idem pour `decor:` et `look:`.

Les rushes analysés reçoivent un embedding local. PISTE Studio compare ensuite un rush candidat aux embeddings des références et peut proposer les mêmes tags.

### Tags proposés

Les facettes reconnues sont :

- `character:`
- `prop:`
- `decor:`
- `look:`

Chaque proposition affiche :

- le tag proposé ;
- un score de proximité ;
- le seuil utilisé pour cette facette ;
- le nombre de références ;
- la meilleure référence ;
- son niveau de similarité.

### Validation obligatoire

Une proposition commence en `PENDING`.

Deux actions seulement sont possibles :

- **Accepter** : le tag est ajouté au catalogue ;
- **Rejeter** : la proposition est mémorisée comme refusée.

Un tag rejeté ne réapparaît pas automatiquement lors d’un nouveau passage, sauf réinitialisation explicite.

Les politiques serveur imposent :

- `human_validation_required = true`
- `automatic_tag_write = false`
- `automatic_storyline_change = false`

### Vision locale

Le provider par défaut est un modèle CLIP local optionnel.

Installation des dépendances :

    pip install -e '.[vision]'

Le modèle n’est **pas téléchargé automatiquement**.

Si les dépendances sont installées mais que le modèle n’est pas déjà présent dans le cache local, l’interface peut proposer :

**Autoriser le téléchargement du modèle**

Cette action ne transmet aucun rush : elle télécharge uniquement le modèle configuré. Les images extraites des vidéos restent locales.

Le modèle peut être changé via :

    PISTE_VISION_MODEL=<model_id>

### Images de référence

PISTE Studio extrait quelques images des rushes avec ffmpeg dans :

    cache/vision/

Ces images sont temporaires/cache et ne sont pas versionnées dans Git.

### Dégradation propre

Sans `torch`, `transformers`, Pillow, ffmpeg ou modèle local :

- le montage reste fonctionnel ;
- Media Intelligence V0.17 reste disponible selon les outils présents ;
- Favorite/Reject, Markers et Source Selector continuent de fonctionner ;
- la vision sémantique indique explicitement ce qui manque.

## Fondations conservées

- filmstrips backend ;
- prises proches ;
- empreinte perceptuelle V0.17 ;
- Favorite / Reject persistants ;
- Editorial Source Selector ;
- Markers ;
- UX Viewer-first / Focus / Command Palette ;
- Storyline magnétique ;
- Canon et Locks ;
- checkpoint / Undo ;
- versions V001+ ;
- bridge Tesseract.

## Ce que V0.18 ne fait pas

V0.18 ne prétend pas qu’un embedding est une vérité d’identité.

Une proximité élevée avec des références `character:malo` signifie seulement que le rush ressemble suffisamment au groupe de références pour **proposer** ce tag.

L’utilisateur doit toujours valider.

## Installation

Base :

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

Avec vision locale optionnelle :

    pip install -e '.[vision]'

Lancer :

    piste-studio-app --project /chemin/vers/PISTE_0

## Workflow vision

1. Scanner les rushes.
2. Lancer **Analyser** pour la Media Intelligence.
3. Valider quelques tags de référence comme `character:malo` ou `prop:fisher`.
4. Installer/configurer la vision locale si souhaité.
5. Dans l’Inspector d’un rush, cliquer **Analyser vision**.
6. Cliquer **Proposer continuité**.
7. Examiner les références et le score.
8. **Accepter** ou **Rejeter** chaque proposition.

Aucun de ces choix ne modifie automatiquement la Storyline.

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `UX_GUIDE.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
