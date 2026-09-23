# PISTE Studio Local App — v0.22

L’application locale relie l’interface de montage au moteur PISTE Studio via FastAPI.

## Editorial Vision V0.22.1

Le premier refinement V0.22 propose des fenêtres IN/OUT à partir des ruptures visuelles détectées localement par ffmpeg.

### Accès

- Inspector **MEDIA INTELLIGENCE** → **Fenêtres IN/OUT** ;
- Command Palette → **Vision · Fenêtres IN/OUT**.

### Fonctionnement

PISTE Studio applique un détecteur de changement de scène au rush puis construit les segments entre deux ruptures successives.

Chaque candidat contient :

- Source IN ;
- Source OUT ;
- durée ;
- rupture précédente/suivante lorsqu’elles existent ;
- méthode utilisée ;
- seuil de détection.

Sensibilités UI :

- Faible : seuil 0,45 ;
- Normale : seuil 0,32 ;
- Forte : seuil 0,22.

Une durée minimale de 0,75 s évite de présenter les micro-segments les moins utiles.

### Politique éditoriale

Le résultat est une suggestion, pas une décision de montage.

- aucune coupe automatique ;
- aucune insertion automatique ;
- aucune modification de Storyline ;
- **Prévisualiser** ne change pas le montage ;
- **Charger IN/OUT** modifie uniquement la plage SOURCE sélectionnée.

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


## Préflight export audio

Chaque rapport Master Check enregistre une empreinte SHA-256 de l’état audio pertinent de la timeline : clips audio, timing, source IN, gain, automation, fades, pan, crossfades et Mute/Solo.

Au moment d’un export :

- **PASS** : le rapport correspond au mix courant ;
- **WARN** : le rapport est à jour mais signale un écart ;
- **STALE** : le mix a changé depuis le dernier rapport ;
- **MISSING** : aucun rapport exploitable n’existe.

Seul PASS laisse partir l’export sans interruption visuelle.

Pour WARN, STALE ou MISSING, PISTE Studio affiche un préflight avec trois actions :

- **Lancer Master Check** ;
- **Exporter quand même** ;
- **Annuler**.

Le serveur ne bloque jamais automatiquement l’export : l’état audio est également renvoyé dans la réponse d’export pour rester traçable.

## Validation end-to-end ffmpeg

La CI installe désormais ffmpeg explicitement et exécute un test réel qui :

1. génère deux WAV synthétiques ;
2. construit un mix avec gain, automation, fades et pan ;
3. rend le master stéréo ;
4. mesure LUFS intégré, true peak et LRA avec ffmpeg/loudnorm ;
5. vérifie le rapport et l’empreinte du mix.

Ce test n’est pas simulé et n’est pas skipped dans la CI de référence V0.21.
