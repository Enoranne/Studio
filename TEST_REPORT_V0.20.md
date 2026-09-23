# PISTE Studio v0.20 — Rapport de validation Audio Intelligence & Loudness

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **69 tests passés / 69**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Aucune `pageerror` dans le scénario V0.20 final.

## Loudness

Validé :

- parsing du rapport ffmpeg loudnorm ;
- LUFS intégré ;
- true peak source ;
- loudness range ;
- loudness threshold ;
- persistance SQLite ;
- détection de silences ;
- dégradation explicite si ffmpeg manque.

## Normalisation non destructive

Le moteur calcule :

- différence entre LUFS source et cible ;
- headroom true peak ;
- gain effectivement applicable ;
- LUFS estimé après correction ;
- true peak estimé après correction.

Cas testé :

- source : -20 LUFS ;
- TP : -4 dBTP ;
- cible : -16 LUFS ;
- ceiling : -1.5 dBTP ;
- gain théorique : +4 dB ;
- gain proposé : +2.5 dB ;
- proposition signalée comme limitée par true peak.

L’acceptation modifie le gain du clip et décale ses keyframes éventuels sans toucher au fichier source.

## Clipping

Le rapport V0.20 est volontairement nommé **risque de clipping par clip**.

Méthode :

    true peak source + gain maximal du clip/automation

Il ne prétend pas mesurer le true peak du master après sommation de plusieurs sources.

Les tests valident les statuts OK / RISK selon le ceiling choisi.

## Ducking

Le moteur :

- cible uniquement MUSIC ;
- cherche les chevauchements VO / DIALOGUE ;
- ignore SFX et autres rôles ;
- fusionne les intervalles de parole ;
- crée attack / réduction / release ;
- retourne une enveloppe proposée ;
- n’applique rien automatiquement.

Chromium valide :

- ouverture de Ducking VO ;
- présence du clip VO comme déclencheur ;
- acceptation ;
- création visible des quatre keyframes attendus sur MUSIC.

## Crossfade

Le moteur V0.20 :

- cible deux clips audio de même piste ;
- accepte des clips adjacents ;
- crée un overlap contrôlé ;
- ajoute fade out / fade in ;
- écrit une relation réciproque `crossfadeWith` ;
- écrit `crossfadeDuration`.

Timeline schema v4 :

- les overlaps même piste restent refusés par défaut ;
- seul un crossfade réciproque explicite est autorisé.

Chromium valide :

- ouverture de Crossfade suivant ;
- durée proposée 0,50 s ;
- acceptation ;
- présence des badges crossfade sur les deux clips.

## Checkpoint / réversibilité

Les routes d’application serveur créent un checkpoint avant sauvegarde pour :

- normalisation ;
- ducking ;
- crossfade.

Les médias source restent immuables.

## Scénario Chromium final

Le test navigateur couvre notamment :

- toutes les fonctions V0.15–V0.19 déjà présentes ;
- affichage LUFS et true peak source ;
- proposition de normalisation limitée par true peak ;
- acceptation de la normalisation ;
- nouveau gain visible sur le clip ;
- rapport Clipping ;
- proposition Ducking VO ;
- acceptation et automation visible ;
- proposition Crossfade ;
- acceptation et badges XF ;
- absence d’erreur JavaScript.

## Limites

- pas encore de mesure du master final rendu ;
- pas encore de true peak master après sommation ;
- pas encore de rapport de conformité livraison ;
- silence détecté != respiration sémantiquement pertinente ;
- aucune norme LUFS universelle n’est imposée ;
- aucun limiteur automatique ;
- automation Tesseract native toujours dépendante du schéma réellement installé.

## Avertissements CI

- Starlette/TestClient : dépréciation autour de httpx ;
- GitHub Actions : migration Node.js 20 → 24 pour certaines actions externes.

Ces avertissements ne correspondent pas à une régression PISTE Studio.

## Conclusion

V0.20 complète le rattrapage audio commencé en V0.19 : PISTE Studio sait désormais mesurer une source, raisonner sur une cible loudness, proposer une correction limitée par le true peak, détecter un risque de clipping, construire un ducking explicable et créer des crossfades réversibles, tout en maintenant l’utilisateur comme décisionnaire.
