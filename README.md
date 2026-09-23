# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH, historique de sécurité, décisions éditoriales, intelligence média, continuité visuelle et mixage audio**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.19 — Audio Editing & Mixing

La V0.19 rééquilibre PISTE Studio en donnant enfin à l’audio une profondeur comparable au montage vidéo.

### Timeline audio schema v3

Chaque clip audio peut maintenant stocker :

- rôle : `dialogue / vo / music / ambience / sfx` ;
- gain en dB : `-60 dB → +12 dB` ;
- pan : `-1 → +1` ;
- fade in / fade out ;
- enveloppe de volume avec keyframes ;
- connexion Storyline existante.

Les anciennes timelines utilisant `gain: 0..1` restent lisibles et sont automatiquement converties en `gainDb`.

### Preview Web Audio

Le navigateur utilise un vrai graphe Web Audio :

- GainNode par clip ;
- StereoPannerNode lorsque disponible ;
- bus par piste ;
- bus master ;
- Mute ;
- Solo ;
- meters stéréo L/R.

Le gain positif est donc réellement prévisualisable : `+3 dB` n’est plus limité par `HTMLAudioElement.volume`.

### Automation

Les clips audio affichent directement :

- forme d’onde ;
- ligne de volume ;
- keyframes ;
- poignée de fade in ;
- poignée de fade out.

Les keyframes sont manipulables sur le clip et depuis l’Inspector.

Le bouton **+ Point au playhead** ajoute un point d’automation au temps courant.

### Inspector Audio Mix

L’Inspector expose maintenant :

- rôle ;
- gain dB ;
- pan ;
- fade in ;
- fade out ;
- liste des points d’automation.

Les actions audio courantes sont également disponibles dans la Command Palette.

### Solo / Mute

Les pistes audio disposent de :

- `M` — Mute ;
- `S` — Solo ;
- `L` — Lock.

Le Solo est persisté dans la timeline.

### Tesseract

Le plan d’authoring V0.19 conserve désormais :

- `gain_db` ;
- `pan` ;
- `role` ;
- fades ;
- enveloppe de volume.

Le gain statique est matérialisé dans la couche Audio Tesseract.

En revanche, PISTE Studio **n’invente pas** une API d’automation Tesseract : pan, fades et keyframes restent conservés dans le plan/manifest tant que le schéma Tesseract installé ne confirme pas une représentation native compatible.

### Ce qui reste pour V0.20

- analyse loudness LUFS ;
- peak / true peak backend ;
- normalisation ;
- ducking VO/MUSIC proposé et modifiable ;
- crossfades audio ;
- éventuellement bus/faders de piste plus avancés.

## Fondations conservées

- Semantic Vision V0.18 ;
- Media Intelligence ;
- Favorite / Reject ;
- Source Selector ;
- Storyline magnétique ;
- Canon / Locks ;
- checkpoint / Undo ;
- versions V001+ ;
- bridge Tesseract.

## Installation

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

Avec vision optionnelle :

    pip install -e '.[vision]'

Lancer :

    piste-studio-app --project /chemin/vers/PISTE_0

## Workflow audio

1. Importe/catalogue les sources audio.
2. Dépose une source sur VO / MUSIC / SFX.
3. Sélectionne le clip.
4. Règle gain, pan, rôle et fades dans **AUDIO MIX**.
5. Ajoute des keyframes au playhead ou déplace-les directement.
6. Utilise Mute/Solo pour contrôler le mix.
7. Vérifie les meters L/R dans le Viewer.
8. Enregistre puis publie la timeline.

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `UX_GUIDE.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
