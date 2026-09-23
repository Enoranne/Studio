# PISTE Studio Local App — v0.19

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

## Audio Editing & Mixing

### Clip audio

Chaque clip possède désormais :

- rôle ;
- gain dB ;
- pan ;
- fade in/out ;
- volume automation.

### Timeline

Les clips audio montrent :

- waveform ;
- ligne d’automation ;
- keyframes ;
- poignées de fade.

### Playback

La preview utilise Web Audio :

- GainNode ;
- StereoPannerNode ;
- bus par piste ;
- master ;
- Mute/Solo ;
- meters L/R.

### Tesseract

Le gain statique est matérialisé.
Pan/fades/automation restent conservés dans le plan et le manifest, sans invention de champs Tesseract non confirmés.

## Intelligence

- Editorial Intelligence ;
- Media Intelligence ;
- Semantic Vision ;
- aucune décision automatique sur la Storyline.

## Backend connecté

- timeline schema v3 ;
- project/canon/locks ;
- catalogue SQLite ;
- historiques/checkpoints ;
- versions V001+ ;
- Tesseract bridge.

Aucun média n’est envoyé vers un serveur distant par PISTE Studio.
