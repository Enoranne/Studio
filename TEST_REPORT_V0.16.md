# PISTE Studio v0.16 — Rapport de validation

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **46 tests passés / 46**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Aucune `pageerror` dans les scénarios utilisateur couverts.

## Fonctions éditoriales validées

- persistance SQLite des plages Favorite / Reject ;
- suppression d’une plage éditoriale ;
- résolution d’un conflit de plages opposées qui se chevauchent ;
- réhydratation des plages dans le Browser ;
- marqueurs persistants par edit ;
- création d’un marqueur depuis l’interface Chromium ;
- affichage du marqueur sur la règle de timeline ;
- Editorial Source Selector ;
- classement déterministe et explicable ;
- priorité donnée à une plage Favorite persistée lorsqu’elle existe ;
- politique `human_validation_required=true` ;
- politique `automatic_replacement=false` ;
- affichage d’une suggestion dans le tiroir Editorial ;
- prévisualisation d’une suggestion en SOURCE sans remplacement de Storyline ;
- commandes Editorial accessibles via Command Palette ;
- fermeture du tiroir via Échap.

## Signaux actuels du Source Selector

- tags communs ;
- canonical ;
- trailer-safe ;
- rating ;
- plages Favorite ;
- plages Reject ;
- niveau de spoiler ;
- statut média.

Le score sert uniquement au classement interne et chaque résultat expose ses raisons.

## Tests Chromium couverts

- navigation Montage / Canon / Versions ;
- workspaces Assemble / Edit / Review ;
- Focus Mode Viewer ;
- Viewer Overlays ;
- Command Palette ;
- création d’un Marker ;
- sélection explicite d’un rush ;
- ouverture de l’Editorial Source Selector ;
- présence d’une suggestion ;
- mention de la validation humaine ;
- prévisualisation de la suggestion ;
- fermeture du tiroir.

## Limites connues

- le Source Selector dépend encore des métadonnées humaines/cataloguées et n’analyse pas directement le contenu visuel ;
- les filmstrips ne sont pas encore pré-calculés côté backend ;
- Favorite/Reject est persistant, mais il n’existe pas encore d’outil de fusion/édition graphique avancée de plusieurs plages ;
- le point de connexion parent/enfant n’est pas encore manipulable graphiquement ;
- le test réel PISTE 0 → vrai CLI Tesseract → export final reste à réaliser sur la machine de l’utilisateur.

## Avertissements de dépendances

La CI remonte un avertissement Starlette/TestClient autour de `httpx`, ainsi qu’un avertissement de dépréciation Node provenant de dépendances/actions externes. Ils ne font pas échouer la suite et ne correspondent pas à une régression fonctionnelle PISTE Studio.

## Conclusion

V0.16 ajoute une intelligence éditoriale utile sans déléguer la décision de montage : les préférences utilisateur sont persistées, les choix peuvent être marqués dans le temps, et les alternatives sont proposées avec leurs raisons puis validées humainement.
