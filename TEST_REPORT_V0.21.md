# PISTE Studio v0.21 — Rapport de validation Audio Delivery & Master Check

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **76 tests passés / 76**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Le scénario navigateur ouvre **Audio · Master Check**, vérifie que le limiteur est désactivé par défaut, exécute le contrôle et affiche le résultat master.
- Aucune régression fonctionnelle détectée sur les acquis V0.01–V0.20.

## Rendu master

Validé :

- sélection des clips audio réellement audibles ;
- respect de Mute / Solo au niveau des pistes ;
- placement temporel des clips ;
- Source IN / durée ;
- gain dB ;
- automation de volume ;
- fade in / fade out ;
- pan stéréo ;
- overlaps / crossfades explicites ;
- sommation du mix avec ffmpeg ;
- master de contrôle PCM stéréo 48 kHz / 24 bits ;
- source média laissée intacte.

Le rendu de contrôle est écrit dans le cache du projet et peut être régénéré.

## Mesure après sommation

La V0.21 distingue désormais clairement :

1. la mesure loudness d’une **source** ;
2. l’estimation de clipping d’un **clip** ;
3. la mesure LUFS / true peak du **master réellement rendu après sommation**.

Le Master Check mesure :

- LUFS intégré ;
- true peak master ;
- LRA ;
- threshold loudness.

Le statut global est **PASS** seulement si :

- l’écart loudness reste dans la tolérance configurée ;
- le true peak reste sous le ceiling configuré.

Dans le cas contraire, le résultat est **WARN** et les raisons sont listées séparément.

## Presets

Validé :

- preset online de référence ;
- preset broadcast de référence ;
- mode personnalisé ;
- cible LUFS modifiable ;
- ceiling true peak modifiable ;
- tolérance loudness modifiable.

Politique UX : les presets sont présentés comme des **repères configurables**, jamais comme une norme universelle.

## Limiteur

Validé :

- limiteur absent du rendu par défaut ;
- activation uniquement sur choix explicite ;
- état du limiteur inscrit dans le rapport ;
- aucune normalisation master automatique.

Cette règle préserve le principe central de PISTE Studio : une modification du signal reste visible, volontaire et traçable.

## Rapport exportable

Chaque contrôle écrit un rapport JSON dans :

`reports/audio/<edit>_master_check.json`

Le rapport contient notamment :

- version de l’analyse ;
- date ;
- edit contrôlé ;
- preset et valeurs de cible ;
- mesures réelles ;
- statut PASS/WARN ;
- raisons éventuelles ;
- durée du rendu ;
- nombre de clips sommés ;
- état du limiteur ;
- politique de sécurité appliquée.

Une route dédiée permet son téléchargement depuis l’interface.

## Interface

Validé dans Chromium :

- chargement de `ux-audio-delivery.js` via FastAPI ;
- accès par `Ctrl/Cmd+K` → **Audio · Master Check** ;
- ouverture dans le tiroir contextuel existant ;
- pas de nouveau panneau permanent ;
- réglages cible LUFS / ceiling / tolérance ;
- case limiteur décochée par défaut ;
- lancement du contrôle ;
- affichage PASS ;
- affichage LUFS-I master ;
- affichage true peak master ;
- mise à jour de l’overlay MIX du Viewer ;
- lien de téléchargement du rapport JSON.

## Incidents détectés pendant l’intégration

La CI a permis d’identifier puis corriger trois défauts d’intégration avant validation finale :

1. un saut de ligne littéral `\\n` injecté dans `ux-polish.js`, provoquant une erreur de syntaxe JavaScript ;
2. un saut de ligne littéral et un numéro de version V0.20 restés dans `index.html` ;
3. `ux-audio-delivery.js` absent de la whitelist FastAPI des assets UI, ce qui provoquait un 404 navigateur.

Les trois problèmes sont corrigés et couverts par la CI finale.

## CI finale

Run GitHub Actions #318 :

- conclusion : **success** ;
- syntaxe JavaScript : **success** ;
- pytest : **76 passed** ;
- Chromium / Playwright : **success**.

## Avertissements CI

Un avertissement de dépréciation Starlette/TestClient autour de httpx reste présent. Il ne correspond pas à une régression PISTE Studio.

GitHub Actions signale également la transition Node.js 20 → 24 de certaines actions externes.

## Limites connues

- le Master Check mesure le mix audio décrit par la timeline PISTE Studio ;
- l’authoring Tesseract ne matérialise toujours que le gain statique tant que le schéma Tesseract installé ne confirme pas une automation native pour pan/fades/keyframes ;
- par conséquent, il ne faut pas assimiler automatiquement le rapport Master Check au signal audio d’un export Tesseract si ce dernier ne reproduit pas encore toutes les propriétés de mix ;
- les exigences exactes de loudness doivent toujours être vérifiées auprès du diffuseur ou du festival concerné.

## Conclusion

La V0.21 clôt le principal retard fonctionnel audio identifié après la refonte UX. PISTE Studio sait maintenant non seulement éditer et assister le mix, mais aussi **rendre et mesurer le master audio après sommation**, avec un contrôle de livraison explicable, configurable et non destructif.

La chaîne audio couvre désormais :

**édition → automation → analyse source → normalisation proposée → clipping estimé → ducking → crossfade → rendu master → LUFS/true peak master → rapport de contrôle**.
