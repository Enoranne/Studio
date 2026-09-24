# PISTE Studio v0.22 — Rapport de validation Editorial Vision

Date : 24 septembre 2026

## Périmètre validé

Ce rapport couvre deux briques de V0.22 :

1. **V0.22.1 — Fenêtres SOURCE IN/OUT issues de ruptures visuelles** ;
2. **V0.22.2 — Références visuelles ciblées sur un frame ou une zone ROI**.

Restent ouverts dans V0.22 :

- groupes de références et qualité de référence ;
- détection de conflit entre tags sémantiques et Canon ;
- comparaison de continuité plan précédent / plan suivant.

## Résultat global

- Python/API/UI : **91 tests passés / 91** sur le run fonctionnel V0.22.2.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium / Playwright : succès.
- ffmpeg système installé explicitement dans la CI.
- Tests réels de détection de ruptures et d’extraction ROI exécutés.
- Aucun tag ni montage modifié automatiquement par ces fonctions.

# V0.22.1 — Fenêtres IN/OUT

## Détection de ruptures

Le moteur utilise ffmpeg avec le signal `scene`.

Valeurs UI :

- Faible : 0,45 ;
- Normale : 0,32 ;
- Forte : 0,22.

Les timestamps sélectionnés par ffmpeg sont parsés et dédupliqués.

## Construction des fenêtres

À partir de :

    début rush → rupture 1 → rupture 2 → ... → fin rush

PISTE Studio construit des segments chronologiques contenant :

- Source IN ;
- Source OUT ;
- durée ;
- rupture précédente ;
- rupture suivante ;
- méthode `ffmpeg_scene_change` ;
- seuil utilisé ;
- raison textuelle.

Les micro-segments sous la durée minimale sont écartés. Si aucun intervalle n’est suffisamment long, le rush entier est présenté explicitement comme fallback pour validation humaine.

## Test ffmpeg réel

La CI génère :

**rouge 1 s → bleu 1 s → vert 1 s**

Puis valide :

- rupture proche de 1,00 s ;
- rupture proche de 2,00 s ;
- au moins trois fenêtres candidates ;
- aucune édition automatique de Storyline.

## Chromium

Le navigateur valide :

1. ouverture **Fenêtres IN/OUT** ;
2. affichage de la politique de suggestion ;
3. choix de sensibilité ;
4. affichage des fenêtres ;
5. **Charger IN/OUT** ;
6. mise à jour réelle de Source IN/OUT dans l’Inspector ;
7. aucune erreur JavaScript.

# V0.22.2 — Références ciblées

## Modèle de données

Nouvelle table SQLite :

`semantic_references`

Chaque référence contient :

- média source ;
- tag structuré ;
- facet ;
- timecode source ;
- ROI normalisé ;
- provider ;
- modèle ;
- embedding ;
- image JPEG extraite ;
- statut.

Les facets supportés restent :

- `character` ;
- `prop` ;
- `decor` ;
- `look`.

## Indépendance par rapport au tag global

Une référence ciblée est une preuve visuelle locale.

Exemple :

`prop:fisher` à 3,40 s sur une zone de 50 % × 40 %.

Cette action n’ajoute **pas** `prop:fisher` aux tags du rush source.

Cette séparation est testée au niveau moteur et Chromium.

## Extraction frame / ROI

Le moteur :

1. borne le timecode dans la durée du média ;
2. normalise X / Y / largeur / hauteur entre 0 et 1 ;
3. garantit une zone minimale exploitable ;
4. extrait le frame avec ffmpeg ;
5. applique le crop avant l’embedding ;
6. redimensionne la référence ;
7. conserve le JPEG dans le cache local.

Le cache reste sous :

`cache/vision/references/`

## Test ffmpeg réel ROI

La CI crée une vraie vidéo `testsrc`, puis extrait une ROI :

- X = 25 % ;
- Y = 20 % ;
- largeur = 50 % ;
- hauteur = 50 %.

Validé :

- fichier JPEG réellement produit ;
- timecode conservé ;
- ROI normalisée conservée ;
- sortie vérifiée avec ffprobe ;
- largeur de référence conforme au rendu demandé.

## Continuité sémantique

Les propositions peuvent désormais utiliser deux familles de preuves :

1. **legacy** : profil moyen d’un rush entier déjà tagué ;
2. **targeted** : frame ou ROI explicitement défini comme référence.

Les centroïdes peuvent combiner les deux.

Les preuves enregistrent notamment :

- `reference_media_ids` ;
- `targeted_reference_ids` ;
- `targeted_reference_count` ;
- `legacy_reference_count` ;
- meilleure référence média ;
- meilleure référence ciblée éventuelle ;
- similarité correspondante.

## Cas critique validé

Un rush source sans tag global `prop:fisher` reçoit une référence ROI explicitement nommée `prop:fisher`.

Un autre rush visuellement proche peut recevoir une **proposition** `prop:fisher`.

Validé :

- proposition créée ;
- preuve ciblée présente ;
- référence targeted comptée ;
- aucune dépendance à un tag global du rush source ;
- validation humaine toujours requise.

## Protection contre l’auto-référence

Une référence extraite d’un rush est exclue lorsque ce même rush est la cible de la proposition.

Cela évite une similarité circulaire qui donnerait artificiellement un score élevé.

## Déduplication

Une référence strictement identique selon :

- média ;
- tag ;
- facet ;
- timecode ;
- ROI ;
- provider ;
- modèle

est mise à jour plutôt que dupliquée.

Cela évite qu’un double clic ou une recréation accidentelle ne pondère artificiellement le centroïde.

## API

Routes ajoutées :

- `GET /api/vision/references` ;
- `POST /api/vision/references` ;
- `GET /api/vision/references/{id}/image` ;
- `DELETE /api/vision/references/{id}`.

L’API destinée à l’UI n’expose pas l’embedding brut.

`/api/state` expose seulement `semantic_reference_count` par média.

## Interface

Accès :

- Inspector **SEMANTIC VISION → Référence ciblée** ;
- Command Palette **Vision · Référence ciblée**.

Le gestionnaire permet :

- choisir le facet ;
- saisir la valeur ;
- reprendre le frame affiché ;
- saisir le timecode ;
- choisir frame entier ou zone ;
- saisir X / Y / largeur / hauteur ;
- créer la référence ;
- voir le crop extrait ;
- supprimer une référence.

Le nombre de références ciblées apparaît dans l’Inspector.

## Chromium V0.22.2

Le scénario réel valide :

1. sélection d’un rush ;
2. ouverture **Référence ciblée** ;
3. facet `prop` ;
4. valeur `fisher` ;
5. mode **Zone de l’image** ;
6. ROI 15 / 20 / 50 / 40 % ;
7. création ;
8. apparition d’une carte `prop:fisher` ;
9. affichage de la zone ;
10. absence de `prop:fisher` dans les tags globaux de l’Inspector.

## Politique de sécurité éditoriale

V0.22.1 et V0.22.2 respectent les mêmes principes :

- traitement local ;
- suggestion explicable ;
- aucune décision automatique ;
- aucune modification automatique de Storyline ;
- aucune écriture de tag lors de la création d’une référence ;
- validation humaine obligatoire avant acceptation d’une proposition sémantique.

## Limites connues

- la référence ciblée utilise encore un rectangle ROI renseigné par coordonnées ; un geste direct de sélection dans le Viewer pourra améliorer l’ergonomie ;
- les références n’ont pas encore de groupe ni de niveau de qualité ;
- aucune règle Canon n’est encore comparée automatiquement aux tags proposés ;
- la continuité n’est pas encore évaluée explicitement entre plan précédent et plan suivant ;
- le modèle CLIP local reste optionnel et son téléchargement nécessite une action explicite.

## Conclusion

V0.22 transforme progressivement la vision de PISTE Studio d’une analyse « par fichier » vers une analyse **éditorialement située**.

La chaîne validée devient :

**repérer une rupture → choisir une plage SOURCE → choisir un frame → isoler une zone → nommer explicitement la référence → comparer → expliquer la preuve → laisser l’utilisateur décider.**
