# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH, historique de sécurité, décisions éditoriales, intelligence média, continuité visuelle et mixage audio non destructif**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.22 — Editorial Vision Refinement

La première brique V0.22 aide à repérer des **fenêtres SOURCE candidates** à l’intérieur d’un rush.

### Fenêtres IN/OUT par ruptures visuelles

Depuis l’Inspector **MEDIA INTELLIGENCE** ou `Ctrl/Cmd+K` → **Vision · Fenêtres IN/OUT**, PISTE Studio :

- analyse localement le rush avec ffmpeg ;
- détecte les changements de scène selon un seuil configurable ;
- transforme ces ruptures en segments chronologiques ;
- affiche chaque segment avec son IN, son OUT, sa durée et la raison de la proposition ;
- permet de **Prévisualiser** ou **Charger IN/OUT**.

Trois sensibilités sont proposées :

- **Faible** : moins de ruptures, changements plus francs ;
- **Normale** : réglage par défaut ;
- **Forte** : davantage de ruptures potentielles.

La fonction ne coupe jamais automatiquement la Storyline. **Charger IN/OUT** ne fait que préparer la plage SOURCE, exactement comme le Source Selector existant.

Le moteur reste local et déterministe : aucune vidéo n’est envoyée vers un service externe pour cette analyse.


### Références visuelles ciblées

V0.22.2 affine la continuité : une référence n’a plus besoin de représenter un rush entier.

Depuis **SEMANTIC VISION → Référence ciblée** ou `Ctrl/Cmd+K` → **Vision · Référence ciblée**, l’utilisateur peut définir :

- un facet : `character`, `prop`, `decor` ou `look` ;
- une valeur, par exemple `fisher` ;
- un timecode précis ;
- soit le frame entier ;
- soit une zone ROI de l’image.

Exemple : une zone autour du magnétophone peut devenir `prop:fisher` sans transformer tout le rush en référence globale Fisher.

PISTE Studio extrait localement le frame ou le crop avec ffmpeg, calcule son embedding local puis conserve cette référence séparément dans SQLite.

Les futures propositions de continuité peuvent combiner :

- les références ciblées frame/ROI ;
- les anciennes références basées sur le profil moyen d’un rush entier.

L’interface indique combien de références ciblées participent à une proposition et peut identifier la meilleure référence ciblée.

Une référence créée sur un rush n’est jamais utilisée pour lui proposer son propre tag. Aucun tag global n’est écrit lors de la création d’une référence.


### Groupes et qualité de référence

V0.22.3 permet de réunir plusieurs références ciblées sous un même groupe, par exemple :

- `prop:fisher` → **Fisher principal** ;
- `character:malo` → **Malo visage enfance** ;
- `decor:salon` → **Salon cheminée**.

Chaque référence reçoit une qualité explicite :

- **Primaire** : poids 1,5 ;
- **Secondaire** : poids 1,0 ;
- **Faible** : poids 0,5.

Le poids agit **à l’intérieur du groupe**. PISTE Studio calcule d’abord un centroïde pondéré pour chaque groupe, puis les groupes contribuent chacun à poids égal au calcul final. Ajouter dix images moyennes dans un groupe ne lui donne donc pas dix fois plus d’influence qu’un autre groupe.

Une référence sans groupe reste une preuve indépendante.

Les noms de groupes existants sont proposés dans le gestionnaire pour favoriser leur réutilisation entre plusieurs rushes. Groupe et qualité peuvent être modifiés après création sans toucher au tag du média ni à la Storyline.

Les propositions de continuité rendent cette logique visible : nombre de références, nombre de groupes, répartition Primaire/Secondaire/Faible et meilleure référence ciblée éventuelle.


### Conflits Canon et HARD LOCKS

V0.22.4 compare chaque proposition sémantique au Canon courant.

Statuts possibles :

- **CANON ALIGNÉ** : le tag correspond à une règle ou une entrée canonique explicite ;
- **NON VÉRIFIÉ** : le Canon ne confirme ni n’interdit ce tag ;
- **CONFLIT CANON** : le tag est explicitement interdit ou sort d’un facet fermé ;
- **HARD LOCK** : le média est utilisé dans une zone verrouillée qui couvre explicitement les opérations sémantiques ;
- **À REVOIR** : contexte SOFT LOCK.

La règle essentielle est : **absence ≠ contradiction**. Un tag absent du Canon n’est conflictuel que si le facet correspondant est déclaré fermé.

Le Canon peut désormais contenir :

```yaml
semantic:
  allowed_tags:
    - character:malo
    - prop:fisher
  forbidden_tags:
    - prop:smartphone
    - look:modern-glossy
  closed_facets:
    - character
```

Les entrées `characters`, `props`, `decors` et `visual.look` participent aussi aux alignements. `visual.avoid` participe aux interdictions de look.

En cas de conflit bloquant, PISTE Studio ne rejette pas la proposition automatiquement. Il empêche uniquement une acceptation silencieuse : l’utilisateur doit lire la raison puis choisir explicitement **Accepter malgré conflit**. Le Canon, les locks et la Storyline restent inchangés.


### Continuité plan précédent / suivant

V0.22.5 replace l’analyse visuelle dans le montage réel.

Sélectionne un clip vidéo de la STORYLINE puis utilise **Continuité de voisinage → Analyser voisins**. PISTE Studio examine :

**plan précédent → plan sélectionné → plan suivant**

pour les facets structurés :

- `character` ;
- `prop` ;
- `decor` ;
- `look`.

Une **RUPTURE POTENTIELLE** n’est signalée que lorsque les deux plans comparés possèdent des tags explicites du même facet mais sans valeur commune.

Si un voisin porte par exemple `prop:fisher` et que le plan évalué n’a aucun tag `prop`, PISTE Studio affiche **À VÉRIFIER** : l’absence de tag n’est jamais interprétée comme preuve que l’objet est absent de l’image.

Le moteur reconnaît aussi les ponts de continuité : si le plan précédent et le suivant partagent `character:malo`, il vérifie si le plan central documente lui aussi cette preuve.

Il est possible de choisir **un autre rush candidat** dans le drawer. PISTE Studio le simule à la position du plan courant et recalcule immédiatement la continuité avec les mêmes voisins, **sans modifier le montage**.

Cela permet de comparer plusieurs prises avant une éventuelle décision de remplacement.

## V0.21 — Audio Delivery & Master Check

La V0.21 ferme le principal écart audio restant : PISTE Studio peut désormais contrôler **le mix réellement rendu**, après sommation des sources audibles de la timeline.

### Master Check

Depuis la Command Palette (`Ctrl/Cmd+K` → **Audio · Master Check**), l’application :

- rend localement un master audio temporaire via ffmpeg ;
- respecte Mute/Solo, gain dB, automation, fades, pan et crossfades ;
- mesure ensuite le LUFS intégré et le true peak du master ;
- compare séparément loudness et plafond true peak ;
- retourne un statut **PASS** ou **WARN** avec les raisons ;
- génère un rapport JSON exportable dans `reports/audio/`.

Le rendu de contrôle est stéréo 48 kHz / 24 bits et reste dans le cache du projet. Les médias source ne sont jamais modifiés.

### Presets de livraison

PISTE Studio propose des presets de référence configurables. Ils ne sont pas présentés comme des normes universelles : la cible LUFS, le ceiling true peak et la tolérance restent modifiables selon le diffuseur, le festival ou le contexte de livraison.

### Limiteur explicite

Le limiteur master est **désactivé par défaut**. Il n’est ajouté au rendu que si l’utilisateur l’active volontairement. Il n’existe ni normalisation master automatique, ni correction silencieuse.

### Préflight avant export

Le rapport Master Check porte une empreinte du mix audio. Avant un export Tesseract, PISTE Studio distingue :

- **PASS** : contrôle à jour et conforme aux valeurs choisies ;
- **WARN** : contrôle à jour avec écarts ;
- **STALE** : le mix audio a changé depuis le contrôle ;
- **MISSING** : aucun contrôle exploitable.

WARN, STALE et MISSING ouvrent un avertissement avec **Lancer Master Check** ou **Exporter quand même**. L’export reste donc sous contrôle de l’utilisateur et n’est pas arbitrairement bloqué.

## V0.20 — Audio Intelligence & Loudness

La V0.20 ajoute une couche de contrôle et d’assistance audio au mixage V0.19.

### Analyse loudness locale

PISTE Studio utilise ffmpeg pour mesurer les sources audio :

- LUFS intégré ;
- true peak source ;
- loudness range (LRA) ;
- seuil loudness ;
- plages de silence détectées.

Les résultats sont persistés dans SQLite et restent associés au média source.

### Normalisation non destructive

L’utilisateur choisit une cible LUFS et un ceiling true peak.

PISTE Studio calcule alors un **ajustement de gain proposé**.

Si le gain nécessaire pour atteindre la cible ferait dépasser le ceiling true peak, la proposition est limitée et l’interface l’indique explicitement.

Exemple :

    source          -20.0 LUFS
    true peak        -4.0 dBTP
    cible           -16.0 LUFS
    ceiling          -1.5 dBTP

    gain théorique    +4.0 dB
    gain proposé      +2.5 dB
    résultat estimé  -17.5 LUFS
    TP estimé         -1.5 dBTP

La normalisation ne réécrit jamais le fichier source. Elle modifie le gain du clip et décale de la même valeur ses keyframes éventuels.

### Contrôle clipping

PISTE Studio peut produire un rapport de **risque de clipping par clip**.

Il combine :

- true peak mesuré sur la source ;
- gain maximal du clip ou de son automation.

Il ne s’agit pas d’une mesure true peak du master final. Plusieurs sources simultanées peuvent s’additionner : un rendu/mix final devra être mesuré séparément avant une livraison critique.

### Ducking VO / Dialogue

Sur un clip MUSIC, PISTE Studio peut analyser les chevauchements temporels avec :

- VO ;
- DIALOGUE.

Il propose alors une enveloppe de volume avec :

- niveau de base ;
- réduction configurable ;
- attack ;
- release.

La proposition est visible avant application.

Politique :

- validation humaine obligatoire ;
- aucun changement automatique ;
- aucun déplacement de Storyline ;
- automation totalement éditable après acceptation.

### Crossfade audio

Deux clips audio adjacents d’une même piste peuvent recevoir un crossfade contrôlé.

PISTE Studio :

- avance légèrement le second clip pour créer l’overlap ;
- ajoute fade out / fade in ;
- enregistre une relation réciproque `crossfadeWith` ;
- conserve la durée `crossfadeDuration`.

Un overlap audio arbitraire sur une même piste reste interdit. Seul un crossfade explicitement déclaré contourne la règle de collision.

### Silence

L’analyse locale peut également repérer des plages silencieuses via ffmpeg.

V0.20 ne prétend pas encore détecter automatiquement une « bonne respiration » ou une intention vocale : elle identifie des zones de silence mesurables qui pourront alimenter de futures suggestions éditoriales.

## Timeline schema v4 — étape V0.20

La timeline conserve désormais explicitement les crossfades en plus du modèle audio V0.19 :

- rôle ;
- gain dB ;
- pan ;
- fades ;
- automation ;
- Mute / Solo ;
- crossfade réciproque.

## Tesseract

Le modèle audio enrichi reste auditable dans le plan d’authoring.

Le gain statique est matérialisé dans Tesseract.

PISTE Studio ne génère toujours pas de propriétés non documentées pour automation/pan/fades : les informations restent conservées tant que le schéma Tesseract installé ne confirme pas un mécanisme natif compatible.

## Ce que V0.20 ne prétend pas encore faire

- mesure true peak du master final rendu ;
- limiteur/mastering automatique ;
- détection sémantique des respirations ;
- correction audio destructive ;
- choix automatique d’une norme de loudness universelle.

La cible LUFS est configurable car elle dépend du contexte de diffusion.

## Installation

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

L’analyse loudness nécessite ffmpeg disponible sur la machine.

Lancer :

    piste-studio-app --project /chemin/vers/PISTE_0

## Workflow audio conseillé

1. Catalogue les sources audio.
2. Sélectionne un clip et lance **Analyser loudness**.
3. Vérifie LUFS / true peak / LRA / silences.
4. Choisis ta cible et utilise **Normaliser** si nécessaire.
5. Lance **Clipping** pour repérer les clips à risque.
6. Sur MUSIC, utilise **Ducking VO** puis examine l’enveloppe proposée.
7. Entre deux clips adjacents, utilise **Crossfade suivant**.
8. Ajuste manuellement les keyframes/fades.
9. Ouvre **Audio · Master Check**, mesure le master rendu et vérifie LUFS-I / true peak.
10. Télécharge le rapport JSON si tu dois conserver une trace de conformité.
11. N’active le limiteur que volontairement si le contexte de livraison le justifie.
12. À l’export, lis le préflight audio ; si le contrôle est STALE/WARN/MISSING, tu peux relancer le Master Check ou exporter volontairement malgré l’avertissement.

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `UX_GUIDE.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.


### Titres et overlays éditables — V0.23.1

Les clips de la piste **TITLES** disposent maintenant d’un modèle visuel complet.

Dans l’Inspector, **TITRE / OVERLAY** permet de régler :

- texte ;
- preset **Centre / Lower third / Haut / Personnalisé** ;
- famille générique **Sans / Serif / Mono** ;
- taille et graisse ;
- alignement ;
- position X/Y ;
- largeur de boîte ;
- couleur et opacité ;
- couleur/opacité du fond ;
- padding ;
- arrondi.

Les positions et dimensions sont normalisées par rapport au canvas, afin de rester cohérentes entre le Viewer et les futurs formats de delivery.

Le Viewer PROGRAM affiche les changements en direct.

Le modèle de titre a été introduit avec la timeline schema v5. Le schema courant est **v6**, qui ajoute les points de connexion graphiques, et les titres restent conservés intégralement dans les `title_cuts` de l’authoring plan.

PISTE Studio ne fabrique pas une couche texte Tesseract à partir d’hypothèses. Si le schéma Tesseract installé ne documente pas précisément une couche Text compatible, le titre reste explicitement listé dans `unmaterialized_titles` pour la phase de delivery au lieu d’être perdu silencieusement.


### Carton final — V0.23.2

Le bouton **+ Carton final** crée un clip spécialisé sur la piste TITLES.

Par défaut, il est aligné exactement sur la fin du montage et possède :

- un fond canvas noir plein ;
- un texte éditable ;
- une durée de 3,5 s ;
- une queue finale de 0,75 s pendant laquelle le texte disparaît et seul le fond reste visible.

Dans l’Inspector **CARTON FINAL**, les réglages de titre restent disponibles, avec en plus :

- couleur du fond canvas ;
- opacité du fond canvas ;
- durée du **Noir / fond seul final**.

Le fond canvas est distinct du fond de la boîte de texte : il recouvre toute l’image PROGRAM sans modifier le plan vidéo sous-jacent.

Le noir final est intégré au même clip. Il ne crée pas de média noir artificiel ni de clip supplémentaire.

Le backend refuse une durée de noir final supérieure ou égale à la durée du carton.

Comme les autres titres, le carton final est conservé intégralement dans `title_cuts` pour l’authoring et n’est jamais perdu silencieusement si le moteur cible ne peut pas encore le matérialiser.


### Point de connexion graphique — V0.23.3

Les éléments connectés — titres, VO, musique et SFX — possèdent maintenant une connexion visible avec la Storyline.

PISTE Studio distingue deux notions :

- `anchorOffset` : la position temporelle de l’élément connecté relativement au début de son parent ;
- `connectionPointOffset` : l’endroit graphique où la ligne de connexion touche le plan parent.

Cette séparation permet de **déplacer le point de connexion sans déplacer l’élément connecté**.

Quand un élément connecté est sélectionné :

- sa ligne d’attache est mise en évidence ;
- une poignée apparaît sur la Storyline ;
- la poignée peut être déplacée horizontalement ;
- le snap courant reste appliqué.

Si la poignée reste dans le même plan parent, seul `connectionPointOffset` change.

Si elle franchit une coupe, PISTE Studio peut rattacher l’élément au nouveau plan parent. La position absolue du titre ou du son reste identique ; `anchorOffset` est recalculé pour que le futur déplacement du nouveau parent entraîne correctement son enfant.

L’Inspector **CONNEXION STORY** propose également **Point sur parent (s)** pour un réglage numérique précis sans drag.

Tous les changements passent par les checkpoints, la validation backend et les HARD/SOFT LOCKS. Un Undo restaure le parent et le point de connexion précédents.


### Exports festival / social — V0.23.4

Le bouton **Export** ouvre désormais un **Delivery Center** au lieu de lancer directement un MP4 1080p générique.

PISTE Studio fournit cinq cibles techniques intégrées :

- **Festival · ProRes 422 HQ · 1080p** ;
- **Festival · H.264 haute qualité · 1080p** ;
- **Online · H.264 · 1080p** ;
- **Social · Vertical · 9:16** ;
- **Social · Carré · 1:1**.

Ces cibles sont des **repères de travail**, pas des normes universelles. Lorsqu’un festival, diffuseur ou réseau fournit une fiche technique, celle-ci prime.

#### Chaîne de rendu

Le delivery est séparé du montage :

1. la version publiée est rendue par Tesseract ;
2. PISTE Studio utilise ffmpeg pour fabriquer le livrable final ;
3. ffprobe inspecte le fichier obtenu ;
4. un rapport JSON est enregistré.

Le MASTER et les médias source ne sont jamais modifiés.

#### Préflight

Avant chaque export, PISTE vérifie :

- si la version publiée correspond encore au montage de travail ;
- l’état du dernier Audio Master Check ;
- la matérialisation des titres/overlays ;
- le cadrage demandé ;
- le risque de crop.

Un montage modifié après publication apparaît comme **STALE**.

Si des titres restent dans `unmaterialized_titles`, le Delivery Center signale explicitement que le rendu Tesseract peut ne pas les contenir.

#### Social : FIT vs FILL

Pour les formats 9:16 et 1:1 :

**FIT** conserve toute l’image et complète le canvas si nécessaire.

**FILL** remplit le canvas mais recadre l’image au centre.

FILL n’est jamais appliqué automatiquement. Il faut cocher explicitement :

**Autoriser le crop centré**

Le préflight affiche une estimation du cadre sacrifié. Pour une source 16:9 vers un 9:16, le recadrage centré retire environ **68,4 % de la largeur totale**.

Aucun « auto-reframe IA » n’est déclenché en V0.23.4.

#### Sorties et rapports

Les livrables sont écrits dans :

`exports/<edit>/<version>/`

Les rapports sont écrits dans :

`reports/delivery/`

Le rapport contient notamment la cible, le cadrage, le préflight, le fichier source de rendu, le fichier final et les mesures ffprobe.


### Conformité finale du fichier

Après le transcodage V0.23.4, PISTE ne se contente pas de vérifier que ffmpeg a créé un fichier.

ffprobe relit le livrable et le compare à sa cible :

- codec vidéo ;
- dimensions ;
- pixel format ;
- frame rate ;
- présence et codec audio ;
- sample rate ;
- nombre de canaux.

Le Delivery Center affiche ensuite :

**CONFORMITÉ · PASS**

ou :

**CONFORMITÉ · WARN**

avec les écarts constatés.

Pour un export d’une version publiée `Vxxx`, le Master Check audio est lui aussi évalué contre le snapshot `Vxxx/timeline.json`. Si le working cut a changé depuis, le préflight peut donc simultanément indiquer **Version publiée · STALE** tout en contrôlant correctement l’audio de la version réellement livrée.
