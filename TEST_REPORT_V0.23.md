# PISTE Studio v0.23 — Rapport de validation Motion & Delivery

Date : 24 septembre 2026

## Périmètre actuel

Ce rapport couvre :

1. **V0.23.1 — Titres et overlays éditables** ;
2. **V0.23.2 — Carton final spécialisé** ;
3. **V0.23.3 — Point de connexion graphique déplaçable**.

Les autres briques V0.23 restent à venir :

- exports festival / social ;
- presets de delivery.

## Résultat V0.23.1

- Timeline : modèle de titre introduit en **schema v5** ; schema courant **v6** avec point de connexion graphique.
- Authoring plan : **schema v4** avec `title_cuts`.
- App/UI : **v0.23**.
- Python/API/UI/Chromium : **127 tests passés / 127** sur le run fonctionnel V0.23.3.
- JavaScript : `node --check` réussi.
- Chromium / Playwright : réussi.
- Aucune dépendance à une police propriétaire ou à un fichier de fonte local.
- Aucun champ Tesseract Text inventé.

# Modèle de titre

Un clip de piste `titles` possède les champs visuels suivants :

- `text` ;
- `titlePreset` ;
- `fontFamily` ;
- `fontSize` ;
- `fontWeight` ;
- `textAlign` ;
- `positionX` ;
- `positionY` ;
- `boxWidth` ;
- `color` ;
- `backgroundColor` ;
- `backgroundOpacity` ;
- `opacity` ;
- `padding` ;
- `cornerRadius`.

## Presets

Quatre valeurs :

- `center` ;
- `lower_third` ;
- `top` ;
- `custom`.

Les presets définissent une position canonique mais restent convertis en coordonnées normalisées lors de l’application.

## Portabilité typographique

Les familles autorisées sont :

- `sans` ;
- `serif` ;
- `mono`.

Le Viewer utilise des stacks système correspondant à ces familles.

Cette stratégie évite qu’un titre dépende implicitement d’une police présente sur une machine mais absente lors du delivery.

# Validation backend

Le serveur refuse :

- titre vide ;
- texte de plus de 500 caractères ;
- preset inconnu ;
- famille inconnue ;
- alignement inconnu ;
- X/Y hors 0..1 ;
- largeur hors 0.1..1 ;
- taille hors 12..240 ;
- graisse hors 100..900 ou non multiple de 100 ;
- couleur invalide ;
- opacité hors 0..1 ;
- padding / arrondi hors limites.

Les couleurs sont normalisées en majuscules `#RRGGBB`.

# Interface

Le clip title sélectionné affiche une section unique :

**TITRE / OVERLAY**

L’ancien éditeur texte minimal a été supprimé afin d’éviter deux sources de vérité.

Réglages disponibles :

- texte multiligne ;
- preset ;
- famille ;
- taille ;
- graisse ;
- alignement ;
- largeur ;
- X / Y ;
- couleur ;
- opacité ;
- fond ;
- opacité du fond ;
- marge ;
- arrondi.

# Preview PROGRAM

Les modifications sont prévisualisées en direct.

Le rendu adapte :

- taille de texte à la hauteur du Viewer ;
- padding / rayon à la largeur du Viewer ;
- position et largeur aux coordonnées normalisées.

Le Viewer conserve donc les proportions du canvas même lorsque sa taille change.

Un resize de fenêtre recalcule le titre.

# Création

Le bouton **+ Titre** crée désormais un titre v5 :

- à la position du playhead ;
- durée 2 s ;
- preset centre ;
- Sans ;
- 64 px de référence ;
- 700 ;
- blanc ;
- fond transparent.

La logique existante de collision de piste reste appliquée.

# Persistance

Le test API enregistre un lower-third avec :

- texte multiligne ;
- Serif ;
- taille 72 ;
- graisse 600 ;
- alignement gauche ;
- coordonnées personnalisées ;
- couleur ;
- fond ;
- opacité ;
- padding ;
- rayon.

La timeline relue restitue les valeurs normalisées.

# Chromium

Le scénario navigateur valide :

1. sélection du clip `t1` ;
2. ouverture de **TITRE / OVERLAY** ;
3. titre visible dans PROGRAM ;
4. texte `PISTE 0 / BONUS TRACK` ;
5. preset **Lower third** ;
6. Serif ;
7. taille 90 ;
8. alignement gauche ;
9. couleur personnalisée ;
10. fond à 50 % ;
11. padding et arrondi ;
12. **Appliquer PATCH** ;
13. position Viewer à 82 % ;
14. sauvegarde backend ;
15. relecture du fichier timeline ;
16. présence de toutes les propriétés v5 ;
17. aucune erreur JavaScript.

# Authoring Tesseract

V0.23.1 ne perd plus les titres pendant la préparation Tesseract.

Chaque titre devient une entrée `title_cuts` du plan d’authoring.

Le manifest contient :

- `title_layers` ;
- `unmaterialized_titles`.

## Politique de compatibilité

PISTE Studio inspecte le schéma document fourni par le Tesseract installé.

Si aucun type Text compatible n’est confirmé :

- aucune couche native n’est inventée ;
- le titre reste dans `unmaterialized_titles` ;
- un warning explicite est produit.

Même si un token `Text` apparaît dans le schéma, V0.23.1 ne suppose pas encore la forme exacte de ses champs de style.

Cette prudence évite de produire un fichier Tesseract techniquement invalide.

La matérialisation finale des overlays sera traitée avec la chaîne de delivery V0.23 dès que la forme de sortie est maîtrisée.

# V0.23.2 — Carton final

## Objectif

Le carton final réutilise le modèle de titre v5 tout en ajoutant un comportement de fin explicite.

Il doit pouvoir :

- recouvrir intégralement l’image ;
- afficher un texte/crédit final ;
- conserver un fond plein ;
- réserver une queue finale sans texte ;
- terminer exactement au dernier timecode du montage lors de sa création automatique.

## Modèle

Champs supplémentaires :

- `titleRole = final_card` ;
- `canvasBackgroundColor` ;
- `canvasBackgroundOpacity` ;
- `blackTailSeconds`.

Le fond canvas est indépendant du fond de la boîte texte.

## Validation serveur

Le backend vérifie :

- rôle de titre connu ;
- couleur canvas au format `#RRGGBB` ;
- opacité canvas dans 0..1 ;
- `blackTailSeconds >= 0` ;
- `blackTailSeconds < duration`.

Le test API valide la persistance d’un carton se terminant exactement à 30,0 s et le rejet d’un noir final égal à la durée du carton.

## Création UI

Le bouton :

**+ Carton final**

crée par défaut :

- durée : 3,5 s ;
- position : fin exacte de timeline moins 3,5 s ;
- fond canvas : noir 100 % ;
- texte : `Carton final` à remplacer ;
- famille : Sans ;
- taille : 56 ;
- graisse : 600 ;
- queue fond seul : 0,75 s.

Le positionnement final n’utilise pas le snap afin de ne pas décaler silencieusement la borne finale.

Les collisions existantes de la piste TITLES restent bloquantes.

## Viewer PROGRAM

Un calque plein écran `viewerTitleBackdrop` est affiché derrière le texte mais devant l’image du programme.

Pendant la partie texte :

- backdrop visible ;
- texte visible.

Pendant les dernières `blackTailSeconds` :

- backdrop visible ;
- texte masqué.

Le clip lui-même reste présent et actif.

## Inspector

Un carton sélectionné affiche :

**CARTON FINAL · FIN DE TIMELINE**

avec les contrôles :

- style title v5 complet ;
- fond canvas ;
- opacité du fond canvas ;
- durée du noir / fond seul final.

## Command Palette

Commande :

**Titre · Ajouter un carton final**

## Authoring

Le plan conserve :

- `title_role` ;
- `canvas_background_color` ;
- `canvas_background_opacity` ;
- `black_tail_seconds`.

Ces valeurs sont donc disponibles pour la future chaîne de rendu delivery même si Tesseract ne confirme pas encore une couche Text native compatible.

## Chromium

Le scénario navigateur valide :

1. création par **+ Carton final** ;
2. Inspector spécialisé visible ;
3. backdrop plein écran actif ;
4. texte initial visible ;
5. modification du texte en `FIN` ;
6. fond canvas personnalisé ;
7. opacité canvas 100 % ;
8. noir final à 0,8 s ;
9. application du PATCH ;
10. vérification que `start + duration = duration_timeline` ;
11. déplacement du playhead dans la queue finale ;
12. backdrop toujours visible ;
13. texte masqué ;
14. sauvegarde backend ;
15. relecture des propriétés spécialisées ;
16. aucune erreur JavaScript.

## Validation

Run fonctionnel de référence :

**119 tests passés / 119**

# V0.23.3 — Point de connexion graphique

## Objectif

Les éléments connectés de la timeline doivent rendre leur dépendance à la Storyline visible et modifiable sans imposer un déplacement du clip enfant.

V0.23.3 sépare donc la position temporelle de l’enfant de la position graphique de son attache.

## Timeline schema v6

Nouvelle propriété :

`connectionPointOffset`

Pour une connexion :

- `parentClipId` identifie le plan STORY parent ;
- `anchorOffset` conserve la relation temporelle enfant/parent ;
- `connectionPointOffset` indique où la ligne graphique touche le parent ;
- `connectionMode = follow`.

Relation temporelle :

`child.start = parent.start + anchorOffset`

Point graphique :

`connection_time = parent.start + connectionPointOffset`

Le backend impose :

`0 <= connectionPointOffset <= parent.duration`.

## Compatibilité des anciennes timelines

Un clip connecté provenant d’un schema antérieur peut ne pas disposer de `connectionPointOffset`.

Le validateur dérive alors le point depuis :

`clamp(anchorOffset, 0, parent.duration)`.

La connexion peut donc être migrée sans déplacement du clip.

## Déplacement dans le même parent

Exemple :

- parent Plan A : 0–5 s ;
- titre : start 2 s ;
- `anchorOffset = 2` ;
- point initial : +2 s.

Si l’utilisateur déplace uniquement le point vers +3,5 s :

- le titre reste à 2 s ;
- le parent reste Plan A ;
- `anchorOffset` reste 2 ;
- `connectionPointOffset` devient 3,5.

## Changement de parent par drag

Exemple validé :

Avant :

- Plan A : 0–5 s ;
- Plan B : 5–10 s ;
- titre : 2 s ;
- parent : Plan A ;
- `anchorOffset = 2` ;
- point : +2 s.

Le point est glissé à 6 s.

Après :

- titre : toujours 2 s ;
- parent : Plan B ;
- `anchorOffset = -3` ;
- `connectionPointOffset = 1`.

La position absolue du titre n’a donc pas changé.

Si Plan B est déplacé ultérieurement par la Storyline magnétique, le titre le suivra selon son nouvel `anchorOffset`.

## Interface graphique

Les connexions sont dessinées par un SVG superposé à la timeline.

Pour chaque élément connecté :

- une ligne relie le clip au plan STORY ;
- un point marque l’attache sur le parent.

Pour la sélection courante :

- ligne renforcée ;
- point plus grand ;
- Pointer Events actifs ;
- curseur horizontal.

Les autres points restent informatifs et non manipulables.

L’ancien petit trait vertical de connexion a été supprimé pour éviter une double représentation.

## Inspector

La section **CONNEXION STORY** conserve le choix du parent et ajoute :

**Point sur parent (s)**

avec :

**Appliquer le point**

Cette voie offre un réglage précis sans drag.

Le texte d’aide distingue explicitement :

- timecode du clip ;
- offset temporel de suivi ;
- point graphique sur le parent.

## Reflow magnétique

Les opérations de reorder et ripple conservent `connectionPointOffset`.

Si la durée du parent devient plus courte, le point est borné dans la nouvelle durée du parent.

Le timing du clip enfant continue d’être dérivé exclusivement de `anchorOffset`.

## Locks

Un déplacement du point est une mutation éditoriale, même si le clip ne bouge pas.

`validate_locked_change` compare donc les anciennes et nouvelles positions absolues de connexion.

Le déplacement est contrôlé avec :

- `connection_point` ;
- `graphics` pour un titre ;
- `audio_change` pour un clip audio.

Les HARD LOCKS peuvent bloquer l’opération.

Les changements via le sélecteur de parent utilisent la même chaîne.

## Checkpoints et Undo

Un drag validé utilise `commitMagneticCandidate`.

La séquence est :

1. construire un candidat ;
2. valider localement ;
3. valider côté backend ;
4. vérifier les locks ;
5. créer un checkpoint ;
6. appliquer la mutation.

`Ctrl/Cmd+Z` restaure ensuite le parent et le point de connexion précédents.

## Tests moteur

Validé :

- déplacement du point dans le même parent sans déplacement de l’enfant ;
- changement de parent sans déplacement de l’enfant ;
- migration d’une ancienne connexion ;
- rejet d’un point hors parent ;
- blocage d’un déplacement par HARD LOCK graphique.

## Test API

`/api/storyline/validate` accepte un changement :

- parent v1 → v2 ;
- enfant inchangé à 5 s ;
- `anchorOffset 2 → -3` ;
- `connectionPointOffset 2 → 1`.

## Chromium

Le scénario navigateur valide :

1. sélection d’un titre connecté ;
2. ligne de connexion visible ;
3. une seule poignée active ;
4. Inspector à +2,00 s ;
5. badge **Plan A · +2,0 s** ;
6. drag graphique du point de 2 s vers 6 s ;
7. passage au parent Plan B ;
8. titre toujours à 2 s ;
9. `anchorOffset = -3` ;
10. point = +1 s ;
11. badge et Inspector actualisés ;
12. sauvegarde backend en schema v6 ;
13. persistance des nouvelles valeurs ;
14. Undo ;
15. retour à Plan A / +2 s ;
16. aucune erreur JavaScript.

## Incident de validation détecté par la CI

La première intégration graphique a introduit une erreur UI :

`$('.clip').forEach(...)`

alors que le helper de collection est :

`$('.clip')`.

Cette faute provoquait une erreur JavaScript globale et plusieurs échecs Chromium en cascade.

Le premier correctif textuel a lui-même révélé une subtilité de `String.replace` : `$` dans une chaîne de remplacement est interprété comme un seul `# PISTE Studio v0.23 — Rapport de validation Motion & Delivery

Date : 24 septembre 2026

## Périmètre actuel

Ce rapport couvre :

1. **V0.23.1 — Titres et overlays éditables** ;
2. **V0.23.2 — Carton final spécialisé** ;
3. **V0.23.3 — Point de connexion graphique déplaçable**.

Les autres briques V0.23 restent à venir :

- exports festival / social ;
- presets de delivery.

## Résultat V0.23.1

- Timeline : modèle de titre introduit en **schema v5** ; schema courant **v6** avec point de connexion graphique.
- Authoring plan : **schema v4** avec `title_cuts`.
- App/UI : **v0.23**.
- Python/API/UI/Chromium : **127 tests passés / 127** sur le run fonctionnel V0.23.3.
- JavaScript : `node --check` réussi.
- Chromium / Playwright : réussi.
- Aucune dépendance à une police propriétaire ou à un fichier de fonte local.
- Aucun champ Tesseract Text inventé.

# Modèle de titre

Un clip de piste `titles` possède les champs visuels suivants :

- `text` ;
- `titlePreset` ;
- `fontFamily` ;
- `fontSize` ;
- `fontWeight` ;
- `textAlign` ;
- `positionX` ;
- `positionY` ;
- `boxWidth` ;
- `color` ;
- `backgroundColor` ;
- `backgroundOpacity` ;
- `opacity` ;
- `padding` ;
- `cornerRadius`.

## Presets

Quatre valeurs :

- `center` ;
- `lower_third` ;
- `top` ;
- `custom`.

Les presets définissent une position canonique mais restent convertis en coordonnées normalisées lors de l’application.

## Portabilité typographique

Les familles autorisées sont :

- `sans` ;
- `serif` ;
- `mono`.

Le Viewer utilise des stacks système correspondant à ces familles.

Cette stratégie évite qu’un titre dépende implicitement d’une police présente sur une machine mais absente lors du delivery.

# Validation backend

Le serveur refuse :

- titre vide ;
- texte de plus de 500 caractères ;
- preset inconnu ;
- famille inconnue ;
- alignement inconnu ;
- X/Y hors 0..1 ;
- largeur hors 0.1..1 ;
- taille hors 12..240 ;
- graisse hors 100..900 ou non multiple de 100 ;
- couleur invalide ;
- opacité hors 0..1 ;
- padding / arrondi hors limites.

Les couleurs sont normalisées en majuscules `#RRGGBB`.

# Interface

Le clip title sélectionné affiche une section unique :

**TITRE / OVERLAY**

L’ancien éditeur texte minimal a été supprimé afin d’éviter deux sources de vérité.

Réglages disponibles :

- texte multiligne ;
- preset ;
- famille ;
- taille ;
- graisse ;
- alignement ;
- largeur ;
- X / Y ;
- couleur ;
- opacité ;
- fond ;
- opacité du fond ;
- marge ;
- arrondi.

# Preview PROGRAM

Les modifications sont prévisualisées en direct.

Le rendu adapte :

- taille de texte à la hauteur du Viewer ;
- padding / rayon à la largeur du Viewer ;
- position et largeur aux coordonnées normalisées.

Le Viewer conserve donc les proportions du canvas même lorsque sa taille change.

Un resize de fenêtre recalcule le titre.

# Création

Le bouton **+ Titre** crée désormais un titre v5 :

- à la position du playhead ;
- durée 2 s ;
- preset centre ;
- Sans ;
- 64 px de référence ;
- 700 ;
- blanc ;
- fond transparent.

La logique existante de collision de piste reste appliquée.

# Persistance

Le test API enregistre un lower-third avec :

- texte multiligne ;
- Serif ;
- taille 72 ;
- graisse 600 ;
- alignement gauche ;
- coordonnées personnalisées ;
- couleur ;
- fond ;
- opacité ;
- padding ;
- rayon.

La timeline relue restitue les valeurs normalisées.

# Chromium

Le scénario navigateur valide :

1. sélection du clip `t1` ;
2. ouverture de **TITRE / OVERLAY** ;
3. titre visible dans PROGRAM ;
4. texte `PISTE 0 / BONUS TRACK` ;
5. preset **Lower third** ;
6. Serif ;
7. taille 90 ;
8. alignement gauche ;
9. couleur personnalisée ;
10. fond à 50 % ;
11. padding et arrondi ;
12. **Appliquer PATCH** ;
13. position Viewer à 82 % ;
14. sauvegarde backend ;
15. relecture du fichier timeline ;
16. présence de toutes les propriétés v5 ;
17. aucune erreur JavaScript.

# Authoring Tesseract

V0.23.1 ne perd plus les titres pendant la préparation Tesseract.

Chaque titre devient une entrée `title_cuts` du plan d’authoring.

Le manifest contient :

- `title_layers` ;
- `unmaterialized_titles`.

## Politique de compatibilité

PISTE Studio inspecte le schéma document fourni par le Tesseract installé.

Si aucun type Text compatible n’est confirmé :

- aucune couche native n’est inventée ;
- le titre reste dans `unmaterialized_titles` ;
- un warning explicite est produit.

Même si un token `Text` apparaît dans le schéma, V0.23.1 ne suppose pas encore la forme exacte de ses champs de style.

Cette prudence évite de produire un fichier Tesseract techniquement invalide.

La matérialisation finale des overlays sera traitée avec la chaîne de delivery V0.23 dès que la forme de sortie est maîtrisée.

# V0.23.2 — Carton final

## Objectif

Le carton final réutilise le modèle de titre v5 tout en ajoutant un comportement de fin explicite.

Il doit pouvoir :

- recouvrir intégralement l’image ;
- afficher un texte/crédit final ;
- conserver un fond plein ;
- réserver une queue finale sans texte ;
- terminer exactement au dernier timecode du montage lors de sa création automatique.

## Modèle

Champs supplémentaires :

- `titleRole = final_card` ;
- `canvasBackgroundColor` ;
- `canvasBackgroundOpacity` ;
- `blackTailSeconds`.

Le fond canvas est indépendant du fond de la boîte texte.

## Validation serveur

Le backend vérifie :

- rôle de titre connu ;
- couleur canvas au format `#RRGGBB` ;
- opacité canvas dans 0..1 ;
- `blackTailSeconds >= 0` ;
- `blackTailSeconds < duration`.

Le test API valide la persistance d’un carton se terminant exactement à 30,0 s et le rejet d’un noir final égal à la durée du carton.

## Création UI

Le bouton :

**+ Carton final**

crée par défaut :

- durée : 3,5 s ;
- position : fin exacte de timeline moins 3,5 s ;
- fond canvas : noir 100 % ;
- texte : `Carton final` à remplacer ;
- famille : Sans ;
- taille : 56 ;
- graisse : 600 ;
- queue fond seul : 0,75 s.

Le positionnement final n’utilise pas le snap afin de ne pas décaler silencieusement la borne finale.

Les collisions existantes de la piste TITLES restent bloquantes.

## Viewer PROGRAM

Un calque plein écran `viewerTitleBackdrop` est affiché derrière le texte mais devant l’image du programme.

Pendant la partie texte :

- backdrop visible ;
- texte visible.

Pendant les dernières `blackTailSeconds` :

- backdrop visible ;
- texte masqué.

Le clip lui-même reste présent et actif.

## Inspector

Un carton sélectionné affiche :

**CARTON FINAL · FIN DE TIMELINE**

avec les contrôles :

- style title v5 complet ;
- fond canvas ;
- opacité du fond canvas ;
- durée du noir / fond seul final.

## Command Palette

Commande :

**Titre · Ajouter un carton final**

## Authoring

Le plan conserve :

- `title_role` ;
- `canvas_background_color` ;
- `canvas_background_opacity` ;
- `black_tail_seconds`.

Ces valeurs sont donc disponibles pour la future chaîne de rendu delivery même si Tesseract ne confirme pas encore une couche Text native compatible.

## Chromium

Le scénario navigateur valide :

1. création par **+ Carton final** ;
2. Inspector spécialisé visible ;
3. backdrop plein écran actif ;
4. texte initial visible ;
5. modification du texte en `FIN` ;
6. fond canvas personnalisé ;
7. opacité canvas 100 % ;
8. noir final à 0,8 s ;
9. application du PATCH ;
10. vérification que `start + duration = duration_timeline` ;
11. déplacement du playhead dans la queue finale ;
12. backdrop toujours visible ;
13. texte masqué ;
14. sauvegarde backend ;
15. relecture des propriétés spécialisées ;
16. aucune erreur JavaScript.

## Validation

Run fonctionnel de référence :

**119 tests passés / 119**

.

Le correctif final utilise une fonction de remplacement et le fichier contient effectivement :

`$('.clip').forEach(...)`.

La CI finale confirme la disparition de la régression.

## Validation

Run fonctionnel de référence :

**127 tests passés / 127**

# Limites connues

- pas encore de drag direct du titre dans le Viewer ;
- pas encore d’animation entrée/sortie ;
- pas encore de font picker avec ressources embarquées ;
- pas encore de rendu final festival/social des titres ;
- prise en charge Text native Tesseract dépendante du schéma réel installé.

# Conclusion

V0.23.1–V0.23.3 transforment les overlays et connexions en objets de montage non destructifs, portables, avec une fin pleine image et des dépendances Storyline désormais lisibles et manipulables.

La chaîne validée est :

**créer le titre ou carton final → régler son style et son fond → définir son ancrage Storyline → prévisualiser en PROGRAM → vérifier la queue finale → appliquer → sauvegarder en timeline v6 → publier → préserver intégralement dans l’authoring plan → signaler explicitement ce qui reste à matérialiser au delivery.**
