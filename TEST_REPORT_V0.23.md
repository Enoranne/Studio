# PISTE Studio v0.23 — Rapport de validation Motion & Delivery

Date : 24 septembre 2026

## Périmètre actuel

Ce rapport couvre :

1. **V0.23.1 — Titres et overlays éditables**.

Les autres briques V0.23 restent à venir :

- carton final ;
- point de connexion graphique déplaçable ;
- exports festival / social ;
- presets de delivery.

## Résultat V0.23.1

- Timeline : **schema v5**.
- Authoring plan : **schema v4** avec `title_cuts`.
- App/UI : **v0.23**.
- Python/API/UI/Chromium : **116 tests passés / 116** sur le run fonctionnel.
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

# Limites connues

- pas encore de drag direct du titre dans le Viewer ;
- pas encore d’animation entrée/sortie ;
- pas encore de font picker avec ressources embarquées ;
- pas encore de carton final spécialisé ;
- pas encore de rendu final festival/social des titres ;
- prise en charge Text native Tesseract dépendante du schéma réel installé.

# Conclusion

V0.23.1 transforme la piste TITLES d’un simple champ texte en un vrai système d’overlay non destructif et portable.

La chaîne validée est :

**créer le titre → régler son style → prévisualiser en PROGRAM → appliquer → sauvegarder en timeline v5 → publier → préserver intégralement dans l’authoring plan → signaler explicitement ce qui reste à matérialiser au delivery.**
