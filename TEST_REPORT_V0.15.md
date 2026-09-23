# PISTE Studio v0.15 — Rapport de validation UX

Date : 23 septembre 2026

## Résultat automatisé

- Python/API/UI : **42 tests passés / 42**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Aucune `pageerror` pendant le scénario utilisateur testé.

## Interactions Chromium couvertes

- Montage → Canon & Locks → Versions → Montage ;
- ASSEMBLE → REVIEW → EDIT ;
- Focus Mode du Viewer ;
- vérification que le Viewer devient effectivement plus grand en Focus ;
- sortie du Focus via Échap ;
- ouverture du menu Overlays ;
- masquage/réaffichage du HUD Viewer ;
- fermeture du popover via Échap ;
- ouverture de la Command Palette avec `Ctrl+K` ;
- recherche d’une commande ;
- exécution de la commande Review ;
- retour vers EDIT ;
- présence de l’Undo.

## Raffinements V0.15

- Viewer plus dominant ;
- Browser à filmstrips agrandis ;
- chrome visuel réduit ;
- badges et métadonnées plus discrets ;
- Inspector plus sobre ;
- Storyline plus contrastée ;
- workspaces davantage différenciés ;
- Focus Mode Browser / Viewer / Timeline / Inspector ;
- Viewer Overlays configurables ;
- Command Palette ;
- charte UX `UX_GUIDE.md`.

## Ce qui n’est pas encore certifié visuellement

Les tests Chromium vérifient le comportement et certaines dimensions, mais ne remplacent pas une revue perceptive humaine sur l’écran de travail réel. Restent notamment à juger :

- confort après une longue session ;
- taille idéale des textes et poignées de trim ;
- densité avec 50–200 rushes ;
- équilibre Browser / Viewer / Timeline selon la résolution ;
- rendu réel avec les médias PISTE 0 ;
- qualité du skimming sur fichiers vidéo lourds.

## Conclusion

V0.15 est une évolution de qualité d’usage, pas une extension du moteur. Elle réduit la sensation de dashboard technique et rapproche PISTE Studio d’une workstation de montage sobre, tout en gardant Canon, Locks, Storyline magnétique, Undo et Tesseract au même niveau fonctionnel.
