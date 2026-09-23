# Démarrage rapide — PISTE Studio v0.18

## 1. Installer

```bash
python -m venv .venv
```

macOS / Linux :

```bash
source .venv/bin/activate
pip install -e .
```

Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
pip install -e .
```

## 2. Lancer

Projet de démonstration :

```bash
piste-studio-app --project demo/PISTE_0_DEMO
```

Projet réel :

```bash
piste-studio-app --project /chemin/vers/PISTE_0
```

L’application s’ouvre sur `http://127.0.0.1:8765/`.

## 3. Workflow UI V0.13

1. Place les vidéos dans `rushes/` et les sons dans `audio/`.
2. Clique **Scanner projet**.
3. Monte dans la timeline et clique **Enregistrer**.
4. Clique **Publier version** : la timeline est figée en `edits/<edit>/V001/timeline.json`.
5. Si le CLI Tesseract configuré est prêt, clique **Authorer Tesseract**.
6. Utilise **Preview** puis **Export**.

Le `.tsrct` est créé dans le dossier de version, jamais dans `master/`.


## Storyline magnétique

Dans EDIT, déplacer un plan STORY réordonne la Storyline et recale l’aval. Trimmer un plan produit un ripple. Les titres, VO, musiques et SFX peuvent être reliés à un plan parent depuis l’Inspector ; ils suivent alors automatiquement son déplacement.


## Sécurité d’édition V0.14

Avant chaque reorder/ripple validé, PISTE Studio crée un checkpoint persistant. Utilisez **Undo** ou **Ctrl/Cmd+Z** pour restaurer l’état précédent. Les tests CI ouvrent désormais l’interface dans Chromium et vérifient les clics de navigation en plus des tests Python et du contrôle syntaxique JavaScript.


## UX V0.15

- **ASSEMBLE** : sélectionner et préparer les sources avec un Browser dominant.
- **EDIT** : montage principal avec Viewer, Inspector et Storyline.
- **REVIEW** : lecture avec Viewer dominant et Index.
- **Focus Mode** : survoler un panneau puis utiliser `~`, ou cliquer sur `⛶`.
- **Command Palette** : `Ctrl/Cmd+K`.
- **Overlays Viewer** : choisir l’affichage du timecode, du mix et de la plage IN/OUT.
- **Échap** : fermer un menu ou quitter le Focus.


## Editorial Intelligence V0.16

1. Dans SOURCE, règle IN / OUT.
2. Utilise **F** pour enregistrer la plage comme Favorite ou **X** pour Reject.
3. Utilise **M** dans la timeline pour poser une Note, Décision, Beat ou Vigilance.
4. Depuis l’Inspector, clique **Alternatives** pour ouvrir l’Editorial Source Selector.
5. Lis les raisons proposées et prévisualise les candidats.
6. **Charger la plage** ne modifie que la sélection SOURCE ; la Storyline n’est jamais remplacée automatiquement.


## Media Intelligence V0.17

1. Place les rushes dans `rushes/`.
2. Clique **Scanner**.
3. Clique **Analyser** pour lancer ffprobe/ffmpeg localement et générer les filmstrips.
4. Sélectionne un rush : l’Inspector affiche ses caractéristiques techniques.
5. Clique **Prises proches** pour comparer les autres rushes.
6. Utilise des tags structurés comme `character:malo`, `prop:fisher`, `decor:salon` ou `look:warm-tungsten` pour enrichir les contrôles de continuité.
7. **Alternatives** utilise ces signaux avec Favorite/Reject, Canon, Safe et Spoiler.

Si ffmpeg/ffprobe n’est pas présent, le reste de PISTE Studio continue de fonctionner et l’analyse affiche explicitement que les outils sont indisponibles.


## Semantic Vision V0.18

1. Commence par valider quelques tags de référence sur des rushes fiables :
   - `character:malo`
   - `prop:fisher`
   - `decor:salon`
   - `look:warm-tungsten`
2. Installe la vision locale si souhaité : `pip install -e '.[vision]'`.
3. Sélectionne un rush puis clique **Analyser vision**.
4. Si le modèle n’est pas déjà en cache, PISTE Studio demande une autorisation explicite avant téléchargement.
5. Clique **Proposer continuité**.
6. Examine le score, le seuil et les rushes de référence.
7. **Accepter** écrit le tag ; **Rejeter** mémorise le refus.
8. Aucune proposition ne modifie la Storyline.

La vision locale fonctionne comme une aide à la continuité, pas comme une décision automatique d’identité.
