# PISTE Studio Local App — v0.21

L’application locale relie l’interface de montage au moteur PISTE Studio via FastAPI.

## Audio Delivery V0.21

Le **Master Check** contrôle le mix rendu, après sommation des clips audio audibles de la timeline.

Le rendu temporaire local via ffmpeg prend en compte :

- Mute / Solo des pistes ;
- gain dB ;
- automation de volume ;
- fades ;
- pan ;
- overlaps et crossfades explicites ;
- placement temporel des clips.

Le master de contrôle est produit en PCM stéréo 48 kHz / 24 bits dans le cache du projet. Les sources restent immuables.

### Mesure master

Après rendu, PISTE Studio mesure :

- LUFS intégré du mix final ;
- true peak master ;
- LRA ;
- threshold loudness.

Le contrôle compare séparément :

- l’écart à la cible loudness ;
- le dépassement éventuel du ceiling true peak.

Le résultat est **PASS** ou **WARN**, avec les raisons visibles.

### Presets et politique

Les presets de livraison sont des **repères configurables**. PISTE Studio ne prétend pas qu’une cible LUFS unique convient à tous les diffuseurs.

La cible LUFS, le ceiling TP et la tolérance restent modifiables.

### Limiteur

Le limiteur master est **désactivé par défaut**.

Il n’est ajouté au rendu de contrôle que si l’utilisateur coche explicitement l’option. Il n’existe aucune normalisation ou limitation automatique silencieuse.

### Rapport exportable

Chaque Master Check écrit un rapport JSON dans :

`reports/audio/<edit>_master_check.json`

Le rapport contient :

- cible choisie ;
- mesure réelle du master ;
- statut PASS/WARN ;
- écarts constatés ;
- nombre de clips sommés ;
- état du limiteur ;
- politique de sécurité appliquée.

L’interface permet de télécharger directement ce rapport.

## Audio V0.20

L’Inspector conserve les fonctions V0.20 :

- analyse source LUFS / true peak / LRA / silences ;
- normalisation non destructive proposée puis validée ;
- estimation de risque de clipping par clip ;
- ducking VO / DIALOGUE vers MUSIC ;
- crossfades explicites et réversibles.

Le rapport de clipping V0.20 reste volontairement une estimation **par clip**. Le Master Check V0.21 est, lui, une mesure du **mix rendu après sommation**.

## Timeline

Schema courant : **v4**.

Les propriétés audio couvrent :

- rôle ;
- gain dB ;
- pan ;
- fades ;
- automation ;
- solo/mute ;
- crossfade.

## Accès UI

Dans la Command Palette `Ctrl/Cmd+K` :

- **Audio · Analyser loudness**
- **Audio · Normaliser**
- **Audio · Vérifier clipping**
- **Audio · Ducking VO**
- **Audio · Master Check**

Le Master Check est un contrôle projet : il n’ajoute pas de panneau permanent à l’interface.

## Sécurité

Normalisation, ducking et crossfade restent réversibles via checkpoint/Undo.

Le Master Check :

- ne modifie pas la timeline ;
- ne modifie pas les sources ;
- produit uniquement un rendu temporaire et un rapport ;
- n’active un limiteur que sur choix explicite.
