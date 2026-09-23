# Démarrage rapide — PISTE Studio v0.14

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
