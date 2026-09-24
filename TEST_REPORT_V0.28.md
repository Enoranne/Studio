# Rapport de validation — PISTE Studio V0.28

## Statut

**UX NAVIGATION & CONTEXT SYSTEM : FUSIONNÉE DANS MAIN ✅**

Commit de fusion : `87267103bef73a851415f866fe02dee50b666899`

## Validation automatisée

Tête finale de la PR #4 :

- **170 tests passés / 170** ;
- syntaxe JavaScript : PASS ;
- tests Python : PASS ;
- tests Chromium / navigation réelle : PASS ;
- compatibilité `Cmd/Ctrl + K` historique : PASS ;
- tests contractuels V0.28 : PASS.

## Paliers validés

### V0.28.1 — Langage visuel contextuel

- VIDEO ;
- AUDIO ;
- TRANSCRIPT ;
- EDITORIAL / AI ;
- DELIVERY ;
- PROJET.

La couleur reste un signal secondaire et chaque contexte conserve un libellé
explicite.

### V0.28.2 — Aide contextuelle

- Guidée ;
- Minimale ;
- Désactivée ;
- préférence locale persistée ;
- micro-textes courts orientés vers la conséquence de l’action.

### V0.28.3 — Recherche universelle

La palette `Cmd/Ctrl + K` couvre désormais :

- Actions ;
- Aller à ;
- Aide ;
- Ressources.

Une barre visible rend également la recherche découvrable sans raccourci
clavier.

### V0.28.4 — Actions contextuelles

La zone **UTILE ICI** suggère quelques raccourcis adaptés au contexte sans
masquer les fonctions avancées.

Les noms accessibles ont été différenciés des boutons historiques afin
d’éviter les ambiguïtés clavier/lecteur d’écran.

### V0.28.5 — FAQ et ressources

Aide intégrée pour Storyline, Locks, transcription VO, VO→image, audio et
Delivery, plus :

- raccourcis ;
- workflow PISTE ;
- glossaire ;
- principes de sécurité.

### V0.28.6 — Sémantique de l’action

Le footer différencie :

- ANALYSE ;
- PROPOSITION ;
- APPLICATION ;
- RENDU.

Ce badge décrit la nature de l’action, pas son résultat final.

### V0.28.7 — Préférences UX

- Confort / Compact ;
- couleurs contextuelles activées / neutralisées ;
- actions contextuelles visibles / masquées ;
- aide Guidée / Minimale / Désactivée.

Ces réglages restent locaux et ne modifient ni Canon, ni Storyline, ni médias.

## Régressions attrapées pendant la validation

La progression par paliers a permis de corriger avant fusion :

1. les nouveaux scripts UX initialement absents de la whitelist FastAPI
   `/ui/` ;
2. le conflit entre l’ancien moteur de palette et le nouveau moteur universel ;
3. des noms accessibles trop proches de boutons existants comme
   « Alternatives » et « Export » ;
4. la conservation explicite des anciennes commandes dynamiques
   « Carton final », « Continuité voisins » et « Delivery Festival/social ».

## Packaging

La version Python/FastAPI/Tauri est alignée sur **0.28.0**.

Les builds macOS ARM64 / Intel sont une validation distincte. Ils ne doivent
être déclarés validés qu’après réussite effective de leurs jobs et smoke tests.
