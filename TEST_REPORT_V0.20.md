# PISTE Studio v0.20 — Rapport de validation Audio Intelligence & Loudness

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **69 tests passés / 69** sur le dernier commit fonctionnel V0.20.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Scénario navigateur : normalisation, clipping, ducking et crossfade acceptés sans `pageerror`.

## Analyse loudness locale

PISTE Studio utilise ffmpeg localement pour mesurer les sources audio :

- LUFS intégré ;
- true peak source ;
- loudness range (LRA) ;
- threshold loudness ;
- plages de silence.

Les analyses sont persistées dans SQLite avec version d’analyse.

## Normalisation non destructive

La normalisation :

- part d’une cible LUFS choisie ;
- respecte un ceiling true peak choisi ;
- limite le gain proposé si nécessaire ;
- ne réécrit pas le média source ;
- applique le delta au gain du clip ;
- translate également les keyframes existants ;
- exige une acceptation humaine ;
- crée un checkpoint avant application.

Le scénario Chromium valide notamment :

- source -20 LUFS ;
- true peak -4 dBTP ;
- cible -16 LUFS ;
- ceiling -1.5 dBTP ;
- gain théorique +4 dB ;
- gain accepté +2.5 dB car limité par le true peak.

## Clipping

Le rapport de clipping V0.20 est explicitement une **estimation par clip** :

source true peak + gain maximal du clip/automation.

Il ne prétend pas mesurer le true peak du master final ni l’addition de plusieurs sources simultanées.

## Ducking

Sur un clip MUSIC, PISTE Studio détecte les chevauchements avec VO et DIALOGUE et propose :

- réduction configurable ;
- attack ;
- release ;
- enveloppe de volume éditable ;
- liste des clips de parole ayant déclenché la proposition.

La proposition ne modifie rien avant acceptation humaine.

Le scénario Chromium valide l’acceptation et la création des points d’automation sur le clip MUSIC.

## Crossfade

V0.20 autorise un overlap audio sur une même piste uniquement lorsqu’il est explicitement déclaré comme crossfade réciproque.

Le crossfade :

- concerne deux clips audio de la même piste ;
- crée l’overlap nécessaire lorsque les clips sont adjacents ;
- ajoute fade out / fade in ;
- stocke `crossfadeWith` ;
- stocke `crossfadeDuration` ;
- passe par validation humaine.

Le scénario Chromium valide un crossfade de 0.50 s et les badges sur les deux clips.

## Timeline schema v4

Le schema v4 conserve :

- gain dB ;
- pan ;
- rôle ;
- fades ;
- volume automation ;
- Mute / Solo ;
- relation de crossfade.

Les collisions arbitraires restent interdites.

## Limites assumées

V0.20 ne fournit pas encore :

- mesure LUFS du **master mixé final** ;
- true peak master final ;
- limiteur/mastering automatique ;
- norme de diffusion imposée ;
- détection sémantique de respiration ;
- correction destructive des sources.

Ces points appartiennent à V0.21 Audio Delivery & Master Check.

## Validation CI

Dernier commit fonctionnel V0.20 validé :

- workflow GitHub Actions : 35920871304 ;
- 69 passed ;
- 1 warning Starlette/TestClient sans incidence fonctionnelle ;
- avertissement GitHub Actions Node.js 20 → 24 sur actions externes, sans incidence PISTE Studio.

## Conclusion

V0.20 transforme le mixage V0.19 en chaîne audio assistée mais contrôlée : PISTE Studio mesure, estime et propose ; l’utilisateur reste responsable de l’application des changements.

La prochaine étape logique est V0.21 : rendre temporairement le mix complet, mesurer ce master et comparer le résultat réel aux objectifs de livraison.
