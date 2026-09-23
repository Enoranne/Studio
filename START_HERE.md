# Démarrage rapide — PISTE Studio v0.21

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


## Audio Mixing V0.19

1. Sélectionne ou dépose un clip audio dans la timeline.
2. Dans **AUDIO MIX**, règle :
   - rôle ;
   - gain dB ;
   - pan ;
   - fade in / fade out.
3. Utilise **+ Point au playhead** pour créer une automation de volume.
4. Déplace directement les points de volume ou les poignées de fade sur le clip.
5. Utilise **M** pour Mute et **S** pour Solo sur les pistes audio.
6. Contrôle les meters L/R dans le Viewer.
7. Enregistre la timeline : le format V3 conserve gain, pan, rôles, fades et automation.
8. À l’authoring Tesseract, le gain statique est appliqué ; les autres paramètres restent préservés tant que le schéma Tesseract installé ne confirme pas leur automation native.


## Audio Intelligence V0.20

1. Sélectionne un clip audio.
2. Clique **Analyser loudness** pour mesurer LUFS, true peak, LRA et silences.
3. Choisis une cible LUFS et un ceiling TP.
4. Clique **Normaliser** puis examine le delta proposé avant **Accepter**.
5. Utilise **Clipping** pour voir les clips dont le true peak estimé dépasse le plafond choisi.
6. Sur un clip MUSIC, utilise **Ducking VO** pour générer une enveloppe selon les chevauchements VO/DIALOGUE.
7. Pour deux clips audio adjacents de même piste, utilise **Crossfade suivant**.
8. Ajuste ensuite manuellement les fades et keyframes si nécessaire.
9. Avant une livraison finale, mesure le master rendu : le rapport V0.20 reste une estimation par clip.


## Audio Delivery V0.21

1. Termine d’abord le mix avec les outils V0.19 / V0.20.
2. Ouvre la Command Palette avec **Ctrl/Cmd+K**.
3. Lance **Audio · Master Check**.
4. Choisis un preset de référence ou règle directement :
   - cible LUFS ;
   - ceiling true peak ;
   - tolérance loudness.
5. Laisse **Limiteur master** décoché pour mesurer le mix tel qu’il est réellement.
6. Clique **Mesurer le master**.
7. Lis séparément le LUFS-I master, le true peak et le statut PASS/WARN.
8. Télécharge le rapport JSON si tu dois conserver une preuve de contrôle.
9. N’active le limiteur que volontairement si tu veux comparer un rendu limité.

Les presets sont des repères configurables et ne remplacent jamais les spécifications du diffuseur ou du festival concerné.
