# PISTE Studio Local App — v0.20

L’application locale relie l’interface de montage au moteur PISTE Studio via FastAPI.

## Audio V0.20

### Loudness

Sur un clip audio catalogué, l’Inspector affiche :

- LUFS-I ;
- true peak source ;
- LRA ;
- nombre de plages silencieuses détectées.

L’analyse utilise ffmpeg localement.

### Normalisation

La cible LUFS et le ceiling true peak sont configurables.

PISTE Studio propose un delta de gain non destructif puis attend **Accepter** avant modification du clip.

Si le true peak empêche d’atteindre la cible, la proposition le signale.

### Clipping

Le rapport Clipping est une estimation par clip à partir du true peak source et du gain maximal du clip/automation.

Ce n’est pas une mesure du master final.

### Ducking

Sur MUSIC :

- recherche des chevauchements VO / DIALOGUE ;
- génération d’une enveloppe avec attack/release ;
- affichage avant application ;
- validation humaine ;
- keyframes éditables après acceptation.

### Crossfade

Entre deux clips audio adjacents de même piste :

- overlap explicite ;
- fades réciproques ;
- relation crossfade enregistrée ;
- collisions audio arbitraires toujours interdites.

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

## Sécurité

Normalisation, ducking et crossfade créent un checkpoint avant sauvegarde côté backend.

Les fichiers source ne sont jamais réécrits.

## Limites

La mesure master finale après sommation de plusieurs clips n’est pas encore incluse. Elle est prévue en V0.21.
