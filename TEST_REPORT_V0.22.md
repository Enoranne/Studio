# PISTE Studio v0.22 — Rapport de validation Editorial Vision

Date : 24 septembre 2026

## Périmètre validé

Ce rapport couvre quatre briques de V0.22 :

1. **V0.22.1 — Fenêtres SOURCE IN/OUT issues de ruptures visuelles** ;
2. **V0.22.2 — Références visuelles ciblées sur un frame ou une zone ROI** ;
3. **V0.22.3 — Groupes de références et qualité de preuve** ;
4. **V0.22.4 — Détection de conflits Canon / HARD-SOFT LOCKS**.

Reste ouvert dans V0.22 :

- comparaison de continuité plan précédent / plan suivant.

## Résultat global

- Python/API/UI : **103 tests passés / 103** avec la couverture V0.22.4.
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

# V0.22.3 — Groupes et qualité

## Modèle de données et migration

La table `semantic_references` porte désormais :

- `group_name` ;
- `quality`.

La migration est exécutée à l’ouverture d’une base existante.

Une base V0.22.2 sans ces colonnes est migrée automatiquement et les anciennes références reçoivent la qualité `secondary`.

Cette migration est couverte par un test construit à partir d’un schéma V0.22.2 simulé.

## Niveaux de qualité

Trois niveaux sont définis :

- **Primaire / primary** : poids 1,5 ;
- **Secondaire / secondary** : poids 1,0 ;
- **Faible / low** : poids 0,5.

Ces valeurs sont des poids de calcul, pas des probabilités ni des scores de vérité.

## Pondération à deux niveaux

Le calcul de continuité évite qu’un grand nombre d’images proches domine artificiellement.

Pour chaque tag :

1. les références portant le même `group_name` sont réunies ;
2. leur centroïde est calculé avec leur poids de qualité ;
3. chaque référence ciblée sans groupe reste une preuve indépendante ;
4. chaque ancienne référence legacy de rush entier reste une preuve indépendante ;
5. les centroïdes de groupes/preuves sont ensuite moyennés à poids égal.

Un groupe de dix références n’a donc pas automatiquement dix fois plus d’influence qu’un groupe d’une seule référence.

## Test de pondération

Le test principal construit un groupe `prop:radio` avec :

- une référence primaire alignée avec la cible ;
- une référence faible orthogonale.

Le poids 1,5 / 0,5 maintient une similarité supérieure à 0,94 et permet la proposition au-dessus du seuil `prop`.

Le rapport de preuve confirme :

- méthode `grouped_weighted_reference_centroid` ;
- 1 groupe ;
- 2 références ciblées ;
- distribution qualité 1 / 0 / 1 ;
- poids total du groupe = 2,0.

## Test d’équilibrage des groupes

Un second test utilise quatre références :

- trois dans `Ambre principal` ;
- une dans `Ambre alternatif`.

Le résultat doit indiquer :

- 4 références ;
- seulement 2 groupes de preuve.

Cela valide que les trois images du premier groupe ne sont pas comptées comme trois groupes indépendants.

## Résumé de groupes

PISTE Studio peut produire pour chaque groupe :

- tag ;
- facet ;
- nom du groupe ;
- ids de références ;
- médias sources ;
- nombre de références ;
- distribution Primaire / Secondaire / Faible ;
- poids qualité total.

L’interface réutilise les noms de groupes déjà présents dans le projet.

## Modification après création

`PATCH /api/vision/references/{id}` permet de modifier :

- groupe ;
- qualité.

Cette action ne modifie ni crop, ni embedding, ni tag global du média, ni Storyline.

## Chromium V0.22.3

Le scénario navigateur valide :

1. création de `prop:fisher` ;
2. groupe **Fisher principal** ;
3. qualité **Primaire** ;
4. affichage du groupe et du poids ;
5. affichage du groupe dans le résumé projet ;
6. changement vers **Fisher secondaire** ;
7. reclassement **Faible** ;
8. persistance après PATCH ;
9. absence de tag global automatique.

## Preuves de continuité enrichies

Les propositions peuvent maintenant exposer :

- nombre total de références ;
- nombre de groupes ;
- nombre de références ciblées ;
- distribution Primaire / Secondaire / Faible ;
- groupes impliqués ;
- poids qualité par groupe ;
- meilleure référence ciblée éventuelle.

L’UI affiche notamment le nombre de groupes et la distribution **P/S/F**.

# V0.22.4 — Conflits Canon et locks

## Objectif

Une proposition de continuité visuelle n’est plus évaluée uniquement par similarité.

Elle est également confrontée :

- au Canon courant ;
- aux règles sémantiques explicites ;
- aux `visual.look` / `visual.avoid` ;
- aux personnages, accessoires et décors déclarés ;
- au contexte HARD/SOFT LOCK de la timeline active.

## Classification

Le moteur produit cinq statuts :

- **ALIGNED** : preuve canonique explicite compatible ;
- **UNVERIFIED** : le Canon ne confirme ni n’interdit ;
- **CONFLICT** : contradiction explicite ;
- **HARD_LOCK** : média utilisé dans une zone HARD applicable aux opérations sémantiques ;
- **REVIEW** : contexte SOFT LOCK.

Principe fondamental :

**absence de règle ≠ contradiction.**

Un tag absent du Canon devient conflictuel par absence uniquement si son facet est déclaré fermé.

## Canon semantic schema

Les nouveaux projets utilisent un Canon schema v2 avec :

```yaml
semantic:
  allowed_tags: []
  forbidden_tags: []
  closed_facets: []
```

La section reste optionnelle pour les anciens projets.

Sources positives supplémentaires :

- clés de `characters` ;
- clés de `props` ;
- clés de `decors` ;
- valeurs de `visual.look`.

Sources négatives supplémentaires :

- `visual.avoid` ;
- `semantic.forbidden_tags`.

## Facets fermés

Un facet fermé signifie que le vocabulaire Canon correspondant est exhaustif.

Exemple :

- Canon : `characters: {malo: ...}` ;
- `closed_facets: [character]` ;
- proposition `character:malo` → **ALIGNED** ;
- proposition `character:jasper` → **CONFLICT**.

Sans `closed_facets: [character]`, `character:jasper` serait **UNVERIFIED**.

## Locks sémantiques

PISTE Studio recherche si le média proposé est réellement présent dans un clip chevauchant le lock.

Le lock ne s’applique à cette décision que si ses opérations interdites couvrent :

- toutes les opérations ;
- `semantic` ;
- `semantic_tag` ;
- `semantic_tag_accept` ;
- `tag` ;
- `semantic:<facet>` ;
- `tag:<tag exact>`.

Un HARD LOCK limité à `trim` ou `reorder` ne devient donc pas artificiellement un conflit de métadonnées.

## Validation humaine explicite

Pour ALIGNED, UNVERIFIED ou REVIEW, le comportement de décision reste humain et direct.

Pour CONFLICT ou HARD_LOCK :

1. le tag reste **PENDING** ;
2. un premier passage d’acceptation renvoie `REQUIRES_ACKNOWLEDGEMENT` ;
3. aucun tag n’est écrit ;
4. l’interface affiche toutes les raisons et sources ;
5. seul **Accepter malgré conflit** permet ensuite l’acceptation explicite.

L’override :

- ajoute le tag au média ;
- ne modifie pas le Canon ;
- ne modifie pas le lock ;
- ne modifie pas la Storyline ;
- conserve l’évaluation de conflit dans la proposition retournée.

## Tests moteur

Validé :

- normalisation accents / espaces / tirets ;
- index personnages, props, décors et looks ;
- `visual.avoid` ;
- `allowed_tags` ;
- `forbidden_tags` ;
- facets fermés ;
- distinction ALIGNED / CONFLICT / UNVERIFIED ;
- HARD LOCK sémantique ;
- HARD LOCK de trim ignoré pour la sémantique ;
- SOFT LOCK → REVIEW ;
- acceptation conflictuelle sans acquittement → aucune mutation ;
- acceptation avec acquittement explicite → tag ajouté.

## Chromium V0.22.4

Le scénario navigateur valide :

1. proposition `prop:fisher` classée **CONFLIT CANON** ;
2. présence du bouton **Examiner conflit** ;
3. ouverture de l’écran **Conflit Canon** ;
4. affichage de la raison « explicitement interdit » ;
5. vérification que `prop:fisher` n’est pas encore dans l’Inspector ;
6. clic **Accepter malgré conflit** ;
7. apparition de `prop:fisher` dans les tags du média ;
8. proposition `character:malo` affichée **CANON ALIGNÉ** ;
9. acceptation normale de cette proposition ;
10. aucune erreur JavaScript.

## Interface

Chaque carte de proposition peut afficher :

- état Canon ;
- besoin ou non d’acquittement ;
- raison(s) ;
- source(s).

Pour un conflit bloquant, le bouton standard **Accepter** est remplacé par **Examiner conflit**.

L’écran de confirmation précise qu’aucune modification n’a encore eu lieu et expose **Accepter malgré conflit**.

La vue **Canon & Locks** affiche aussi les règles sémantiques explicites.

## Politique de sécurité éditoriale

V0.22.1 à V0.22.4 respectent les mêmes principes :

- traitement local ;
- suggestion explicable ;
- aucune décision automatique ;
- aucune modification automatique de Storyline ;
- aucune écriture de tag lors de la création d’une référence ;
- validation humaine obligatoire avant acceptation d’une proposition sémantique.

## Limites connues

- la référence ciblée utilise encore un rectangle ROI renseigné par coordonnées ; un geste direct de sélection dans le Viewer pourra améliorer l’ergonomie ;
- la continuité n’est pas encore évaluée explicitement entre plan précédent et plan suivant ;
- le modèle CLIP local reste optionnel et son téléchargement nécessite une action explicite.

## Conclusion

V0.22 transforme progressivement la vision de PISTE Studio d’une analyse « par fichier » vers une analyse **éditorialement située**.

La chaîne validée devient :

**repérer une rupture → choisir une plage SOURCE → choisir un frame → isoler une zone → nommer la référence → l’associer à un groupe → qualifier sa force → comparer des groupes équilibrés → confronter la proposition au Canon et aux locks → expliquer la preuve et les contradictions → laisser l’utilisateur décider.**
