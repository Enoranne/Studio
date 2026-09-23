# PISTE Studio v0.14 — Rapport de validation

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **42 tests passés / 42** (`pytest -q`).
- JavaScript : **tous les modules UI passent `node --check`**.
- Navigateur : **test Playwright avec Chromium réel réussi**.
- Navigation testée par clic réel : Montage → Canon & Locks → Versions → Montage.
- Workspaces testés par clic réel : ASSEMBLE → REVIEW → EDIT.
- Les erreurs JavaScript de page sont capturées et font échouer la CI.

## Hardening couvert

- timeline schema v2 ;
- Storyline magnétique et ripple ;
- connexions parent/enfant ;
- validation des effets domino contre les locks ;
- checkpoint persistant avant opération magnétique ;
- Undo persistant via API et Ctrl/Cmd+Z ;
- branche d’historique tronquée après Undo + nouvelle édition ;
- état d’historique exposé par l’API ;
- navigation multi-vues réellement fonctionnelle ;
- store UI central `PisteState` amorcé ;
- démo migrée au schema v2.

## Incident utile découvert par les tests navigateur

Les tests Chromium ont détecté une régression invisible aux tests de syntaxe : certaines collections DOM utilisaient `$()` au lieu de `$$()`, ce qui provoquait `$(...).forEach is not a function`.

Le diagnostic a ensuite révélé une subtilité lors du patch automatique : `$$` dans une chaîne de remplacement JavaScript était interprété comme un seul `$`. La correction définitive utilise un remplacement fonctionnel et la CI navigateur confirme le comportement attendu.

## Tesseract

Le bridge Tesseract reste couvert par les tests avec un faux CLI contrôlé. Le premier essai de bout en bout avec le **CLI Tesseract réel et les vrais rushes PISTE 0** reste à effectuer sur la machine de l’utilisateur.

## Limites connues

- Favorite/Reject n’est pas encore persisté côté backend ;
- le point de connexion reste un offset temporel, pas encore un marqueur graphique manipulable ;
- les fades audio ne sont pas encore matérialisés en enveloppes natives Tesseract ;
- le refactor vers un state/actions centralisé est seulement amorcé ;
- les tests Chromium couvrent pour l’instant navigation/workspaces, pas encore le drag/trim/ripple complet.

## Conclusion

V0.14 constitue une base plus fiable que V0.13 : le projet dispose désormais d’une protection avant édition destructive, d’un Undo persistant et d’un test navigateur réel capable de détecter des régressions d’interaction que les tests structurels et syntaxiques ne voient pas.
