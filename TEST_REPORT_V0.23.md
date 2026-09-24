# PISTE Studio v0.23 — Rapport de validation Motion & Delivery

Date : 24 septembre 2026

## Périmètre actuel

Ce rapport couvre :

1. **V0.23.1 — Titres et overlays éditables** ;
2. **V0.23.2 — Carton final spécialisé** ;
3. **V0.23.3 — Point de connexion graphique déplaçable** ;
4. **V0.23.4 — Exports festival / social** ;
5. **V0.23.5 — Presets de delivery**.

**V0.23 — Motion & Delivery est terminée.**

## Validation globale

Run fonctionnel de référence V0.23.5 :

- Python/API/UI/Chromium : **144 tests passés / 144** ;
- JavaScript : `node --check` réussi ;
- Chromium / Playwright : réussi ;
- ffmpeg réel : réussi ;
- ffprobe réel : réussi ;
- timeline courante : **schema v6** ;
- authoring plan : **schema v4** avec `title_cuts` ;
- App/API : **v0.23**.

L’unique warning CI connu reste une dépréciation Starlette/TestClient/httpx déjà présente avant V0.23.4 ; aucune régression PISTE n’est associée à ce warning.

---

# V0.23.1 — Titres et overlays éditables

## Objectif

Transformer la piste TITLES en système d’overlay non destructif, persisté et transportable.

## Timeline schema v5

Un clip `titles` peut contenir :

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

Les coordonnées sont normalisées.

## Presets visuels

Valeurs disponibles :

- `center` ;
- `lower_third` ;
- `top` ;
- `custom`.

## Typographie

Familles génériques :

- `sans` ;
- `serif` ;
- `mono`.

PISTE n’introduit aucune dépendance silencieuse à une fonte locale propriétaire ou absente de la machine de delivery.

## Validation backend

Le validateur refuse notamment :

- texte vide ;
- texte supérieur à 500 caractères ;
- position hors 0..1 ;
- largeur de boîte hors plage ;
- taille de caractère hors 12..240 ;
- graisse hors 100..900 par pas de 100 ;
- couleur hors `#RRGGBB` ;
- opacité hors 0..1.

## Viewer

Le Viewer PROGRAM matérialise le titre en direct avec :

- position ;
- alignement ;
- taille ;
- largeur ;
- fond ;
- opacité ;
- marge ;
- arrondi.

## Authoring

L’authoring plan V0.23 conserve les titres dans `title_cuts`.

PISTE ne fabrique pas une structure Tesseract Text supposée.

Si le runtime Tesseract installé ne confirme pas une couche Text compatible :

- `title_layers` reste vide ;
- le titre est conservé dans `unmaterialized_titles` ;
- un warning explicite est ajouté.

Aucun titre n’est perdu silencieusement.

---

# V0.23.2 — Carton final spécialisé

## Modèle

Le carton final réutilise le modèle de titre avec :

- `titleRole: final_card` ;
- `canvasBackgroundColor` ;
- `canvasBackgroundOpacity` ;
- `blackTailSeconds`.

## Placement

`addFinalCard()` place le carton pour que :

`start + duration = duration_timeline`

Le placement final exact ne dépend pas du snap.

## Viewer

Pour un carton final :

1. le fond couvre le Viewer ;
2. le texte reste éditable ;
3. la queue noire masque le texte à la fin ;
4. le fond reste présent jusqu’au timecode final.

Aucun faux clip noir n’est ajouté à la timeline.

## Validation

Le backend impose :

`0 <= blackTailSeconds < duration`

## Authoring

Les propriétés du carton final sont préservées dans `title_cuts` et restent auditables même si la couche Text n’est pas encore matérialisable par Tesseract.

---

# V0.23.3 — Point de connexion graphique déplaçable

## Objectif

Rendre la dépendance d’un titre, d’une VO, d’une musique ou d’un SFX à la Storyline visible et manipulable, sans déplacer automatiquement l’élément connecté.

## Timeline schema v6

La connexion distingue désormais deux informations.

### `anchorOffset`

Relation temporelle :

`child.start = parent.start + anchorOffset`

Cet offset sert au suivi magnétique lorsque le parent se déplace.

### `connectionPointOffset`

Point graphique :

`connection_time = parent.start + connectionPointOffset`

Le backend impose :

`0 <= connectionPointOffset <= parent.duration`

Déplacer ce point ne déplace pas le clip enfant.

## Migration

Une ancienne connexion sans `connectionPointOffset` reste valide.

PISTE dérive :

`clamp(anchorOffset, 0, parent.duration)`

puis persiste le point dans le schema v6 à la prochaine validation.

## Changement de parent

Exemple réellement testé :

Avant :

- Plan A : 0–5 s ;
- Plan B : 5–10 s ;
- titre : 2 s ;
- parent : Plan A ;
- `anchorOffset = 2` ;
- point : +2 s.

Le point est déplacé à 6 s.

Après :

- titre : toujours 2 s ;
- parent : Plan B ;
- `anchorOffset = -3` ;
- `connectionPointOffset = 1`.

Le média connecté n’a pas changé de timecode.

## UI

`ux-magnetic.js` dessine un SVG au-dessus de la timeline :

- ligne discrète pour chaque connexion ;
- ligne renforcée pour la sélection ;
- poignée active uniquement sur l’élément sélectionné.

L’Inspector **CONNEXION STORY** propose également :

**Point sur parent (s)**

pour un réglage numérique précis.

## Reflow magnétique

Reorder et ripple conservent le point graphique.

Si le parent est raccourci, le point est borné à la nouvelle durée du parent.

Le timing de l’enfant continue d’être déterminé uniquement par `anchorOffset`.

## Locks et Undo

Le changement passe par :

1. candidat local ;
2. validation ;
3. validation backend ;
4. HARD/SOFT LOCKS ;
5. checkpoint ;
6. mutation ;
7. Undo possible.

Le déplacement du point est contrôlé comme :

- `connection_point` ;
- `graphics` pour les titres ;
- `audio_change` pour l’audio.

## Incident CI corrigé

Une première intégration avait utilisé :

`$('.clip').forEach(...)`

alors que `$()` retourne un seul élément.

Le helper de collection correct est :

`$$('.clip').forEach(...)`

Un premier remplacement textuel avait lui-même été trompé par la sémantique de `String.replace` autour de `$$`.

Le correctif final a été appliqué avec une fonction de remplacement et validé dans Chromium.

---

# V0.23.4 — Exports festival / social

## Objectif

Passer d’un bouton Export générique à une chaîne de delivery explicite, contrôlable et auditable.

Le montage, le rendu moteur et le fichier livré deviennent trois étapes distinctes.

## Delivery Center

Le bouton **Export** ouvre désormais un drawer **Delivery Center**.

Cibles intégrées :

1. **Festival · ProRes 422 HQ · 1080p** ;
2. **Festival · H.264 haute qualité · 1080p** ;
3. **Online · H.264 · 1080p** ;
4. **Social · Vertical · 9:16** ;
5. **Social · Carré · 1:1**.

Ces cibles sont des repères techniques intégrés.

Elles ne sont jamais présentées comme des normes universelles.

Une fiche de delivery fournie par un festival, diffuseur ou plateforme reste prioritaire.

## Architecture de rendu

La chaîne est volontairement en deux étages.

### Étape 1 — rendu moteur

Tesseract produit un rendu source de la version publiée.

Le format source dépend de la cible :

- ProRes pour la cible Festival ProRes ;
- MP4 pour les cibles H.264.

### Étape 2 — delivery ffmpeg

PISTE Studio transcode ce rendu vers le livrable final.

Cela permet de contrôler sans hypothèse sur le CLI Tesseract :

- conteneur ;
- codec ;
- dimensions ;
- pixel format ;
- audio ;
- framing ;
- Fast Start ;
- rapport final.

## Préflight

Le préflight contient quatre blocs.

### 1. Version publiée

PISTE calcule une empreinte SHA-256 de l’état éditorial pertinent :

- durée ;
- Storyline ;
- pistes ;
- clips.

`updated_at` est volontairement ignoré.

Statuts :

- `PASS` : le montage de travail correspond au snapshot publié ;
- `STALE` : la timeline de travail a changé depuis la publication ;
- `MISSING` : snapshot de version absent.

## 2. Audio master

Le statut V0.21 est évalué contre la timeline de la **version publiée Vxxx** lorsque ce snapshot est disponible.

Cela évite un faux diagnostic si le working cut a changé après publication.

Test dédié :

1. publication V001 ;
2. modification du working cut ;
3. préflight V001 ;
4. statut version = STALE ;
5. Master Check appelé avec les clips de V001, pas ceux du working cut.

## 3. Titres / overlays

Si la timeline ne contient aucun titre :

`PASS`.

Si l’authoring manifest est absent :

`MISSING`.

Si `unmaterialized_titles` n’est pas vide :

`WARN`.

Le message précise que le rendu Tesseract peut ne pas contenir les titres concernés.

## 4. Cadrage

Pour les sorties social :

- `FIT` ;
- `FILL`.

### FIT

FIT conserve toute l’image.

Chaîne :

- scale avec respect de l’aspect ;
- padding du canvas ;
- square pixels.

Aucun contenu source n’est retiré.

### FILL

FILL remplit le canvas en recadrant au centre.

Il exige :

`allow_crop = true`

Sans consentement :

`BLOCKED`

Le serveur refuse le transcodage.

## Estimation de crop

Quand le canvas de version est connu, PISTE calcule la fraction du cadre qui sortira de l’image.

Exemple validé :

source 16:9 → cible 9:16.

Le crop centré enlève environ :

**68,4 % de la largeur totale du cadre source.**

Cette valeur est géométrique.

PISTE ne prétend pas savoir si le sujet important se trouve dans la zone retirée.

Aucun auto-reframe IA n’est exécuté.

## H.264

Les cibles MP4 utilisent :

- `libx264` ;
- High Profile ;
- `yuv420p` ;
- débit cible propre au livrable ;
- GOP court ;
- AAC ;
- 48 kHz ;
- stéréo ;
- `+faststart`.

Cible Online 1080p de référence :

- 1920×1080 ;
- 24 fps dans le projet PISTE courant ;
- 8 Mb/s vidéo ;
- AAC 384 kb/s.

## Festival H.264

Repère :

- 1920×1080 ;
- 24 fps ;
- H.264 20 Mb/s ;
- AAC 320 kb/s ;
- 48 kHz stéréo.

Il s’agit d’un fichier de visionnage/inscription, pas d’un substitut universel à une fiche technique de festival.

## Festival ProRes

Cible :

- conteneur MOV ;
- ProRes 422 HQ via `prores_ks` profile 3 ;
- `yuv422p10le` ;
- PCM 24-bit ;
- 48 kHz ;
- stéréo.

Cette cible n’est **pas un DCP**.

## Inspection ffprobe

Après encodage, PISTE relève :

- codec vidéo ;
- largeur ;
- hauteur ;
- pixel format ;
- fps ;
- color space si présent ;
- transfer si présent ;
- primaries si présentes ;
- codec audio ;
- sample rate ;
- canaux ;
- durée ;
- taille du fichier.

## Conformité post-encode

Après ffprobe, `evaluate_delivery_probe(...)` compare le fichier réel avec la cible déclarée.

Contrôles :

- codec vidéo ;
- largeur / hauteur ;
- pixel format ;
- fps ;
- présence de la piste audio ;
- codec audio ;
- sample rate ;
- nombre de canaux.

Résultat :

- `PASS` si aucun écart n’est détecté ;
- `WARN` avec raisons détaillées sinon.

Le Delivery Center affiche ce statut après rendu.

Un test dédié vérifie également qu’un mauvais pixel format et une piste audio absente produisent bien WARN.

## Stockage

Livrables :

`exports/<edit>/<version>/`

Rapports :

`reports/delivery/`

Le rapport JSON contient :

- version du moteur delivery ;
- date ;
- edit ;
- version publiée ;
- cible ;
- framing ;
- rendu source ;
- sortie finale ;
- ffprobe ;
- préflight ;
- politique de sécurité.

## API

Routes validées :

- `GET /api/delivery/targets` ;
- `POST /api/delivery/{version}/preflight` ;
- `POST /api/delivery/{version}/export` ;
- `GET /api/delivery/reports/{report_name}` ;
- `GET /api/delivery/files/{edit_name}/{version}/{filename}`.

## Test ffmpeg réel

La CI génère un MP4 synthétique 320×180 avec audio.

PISTE produit ensuite un vrai livrable :

- 1080×1920 ;
- H.264 ;
- AAC ;
- 48 kHz.

ffprobe vérifie le fichier réellement encodé.

Ce test n’est pas un mock.

## Test API

Le scénario valide :

1. publication V001 ;
2. liste des cibles ;
3. FILL vertical sans consentement → BLOCKED ;
4. FIT → exportable ;
5. rendu Tesseract simulé ;
6. delivery simulé ;
7. création du rapport réel ;
8. téléchargement du fichier ;
9. téléchargement du JSON.

## Test Chromium

Le scénario navigateur valide :

1. bouton **Export** ;
2. ouverture du **Delivery Center** ;
3. sélection **Social · Vertical · 9:16** ;
4. FIT par défaut ;
5. préflight visible ;
6. export activé ;
7. passage en FILL ;
8. consentement crop visible ;
9. export bloqué tant que la case n’est pas cochée ;
10. consentement explicite ;
11. estimation **68,4 %** visible ;
12. bouton **Exporter avec avertissements** ;
13. export ;
14. résultat 1080×1920 ;
15. lien **Télécharger le livrable** ;
16. lien **Rapport JSON** ;
17. aucune erreur JavaScript.

## Validation V0.23.4

Run fonctionnel de référence :

**144 tests passés / 144**

---

# V0.23.5 — Presets de delivery

## Objectif

Permettre de transformer les cibles fixes V0.23.4 en configurations de delivery réutilisables sans rendre les profils intégrés mutables ni affaiblir le préflight.

## Modèle

Deux catégories coexistent.

### Presets intégrés

Les profils intégrés restent toujours disponibles.

Ils portent :

`custom = false`

Ils ne peuvent pas être modifiés ou supprimés.

L’action attendue pour les adapter est :

**Dupliquer**

### Presets personnalisés

Une copie personnalisée porte :

`custom = true`

Elle possède un ID technique stable indépendant de son label.

Format :

`custom_[a-z0-9_]+`

Le label peut être renommé sans changer l’ID.

## Persistance

Le store est :

`delivery-presets.yaml`

Il est local au projet.

Structure :

```yaml
schema_version: 1
default_preset_id: online_1080
presets:
  - ...
```

Le fichier n’est écrit qu’à la première mutation.

## Paramètres éditables

Un preset custom peut définir :

- label ;
- famille ;
- largeur ;
- hauteur ;
- FPS ;
- codec ;
- bitrate H.264 ;
- bitrate AAC ;
- source Tesseract ;
- cadrage par défaut ;
- notes.

## Validation

Dimensions :

- largeur 320–7680 ;
- hauteur 240–7680 ;
- nombres pairs.

FPS supportés par le bridge courant :

- 24 ;
- 30 ;
- 60.

H.264 :

- bitrate vidéo 1–200 Mb/s ;
- bitrate AAC 96–512 kb/s.

## Normalisation codec

### H.264

PISTE impose :

- MP4 ;
- libx264 ;
- yuv420p ;
- AAC ;
- 48 kHz ;
- stéréo.

### ProRes

PISTE impose :

- MOV ;
- prores_ks ;
- profile 3 ;
- yuv422p10le ;
- PCM 24-bit ;
- 48 kHz ;
- stéréo.

Les valeurs incompatibles d’un formulaire ne deviennent donc pas une configuration technique incohérente.

## Source Tesseract et cadrage

Correspondances :

- 720p = 1280×720 ;
- 1080p = 1920×1080 ;
- 4K = 3840×2160.

Le mode NATIVE est autorisé seulement si les dimensions finales correspondent au canvas source choisi.

Exemple testé :

- sortie : 1920×1080 ;
- source Tesseract : 4K ;
- cadrage demandé : NATIVE.

Résultat normalisé :

- modes disponibles : FIT / FILL ;
- défaut : FIT.

PISTE évite ainsi un faux NATIVE qui aurait produit un fichier 3840×2160 au lieu du 1920×1080 annoncé.

## Preset par défaut

Chaque projet possède un :

`default_preset_id`

Il peut pointer vers :

- un built-in ;
- un custom.

À l’ouverture du Delivery Center, ce preset est sélectionné.

Si un custom actuellement par défaut est supprimé :

`online_1080`

redevient automatiquement le défaut.

## Portabilité JSON

### Export

Document :

```json
{
  "schema_version": 1,
  "kind": "piste_studio_delivery_preset",
  "preset": {}
}
```

Les données propres au projet source ne sont pas exportées :

- ID ;
- timestamps ;
- flags internes.

### Import

L’import :

1. valide le document ;
2. normalise la configuration ;
3. génère un nouvel ID sûr ;
4. évite les collisions avec les presets existants.

Cela permet de transférer un profil entre projets sans état global invisible.

## Sécurité des IDs

Les IDs custom sont validés avant résolution.

Un `delivery-presets.yaml` modifié manuellement avec un ID contenant un chemin ou des caractères hors format ne peut pas être utilisé comme nom de sortie.

Les IDs générés depuis des labels longs sont également bornés.

## API

Cycle complet validé :

- créer ;
- modifier ;
- dupliquer ;
- supprimer ;
- définir par défaut ;
- exporter JSON ;
- importer JSON.

`GET /api/delivery/targets` retourne built-ins + custom + défaut courant.

## Intégration préflight/export

Un custom n’est pas une simple préférence UI.

`resolve_delivery_target(..., root=...)` l’injecte dans le même moteur que les built-ins.

Test dédié :

- création d’un custom 1080×1920 / 30 fps ;
- résolution par son ID ;
- préflight réel ;
- cible custom présente dans le résultat ;
- cadrage FIT ;
- export autorisé.

## Chromium

Le parcours navigateur valide :

1. ouverture du Delivery Center ;
2. choix du preset vertical intégré ;
3. export V0.23.4 et conformité ;
4. **Dupliquer** ;
5. apparition de l’éditeur custom ;
6. modification du nom ;
7. passage à 30 fps ;
8. bitrate H.264 à 14 Mb/s ;
9. **Enregistrer le preset** ;
10. résumé technique actualisé ;
11. **Définir par défaut** ;
12. badge **PERSONNALISÉ · DÉFAUT** ;
13. fermeture du drawer ;
14. nouvelle ouverture ;
15. custom toujours sélectionné ;
16. valeurs persistées ;
17. suppression ;
18. retour automatique à `online_1080`.

## Validation V0.23.5

Run fonctionnel de référence :

**144 tests passés / 144**

---

# Limites connues

- pas encore de drag direct du titre dans le Viewer ;
- pas encore d’animation entrée/sortie des titres ;
- pas encore de font picker avec ressources embarquées ;
- matérialisation Text native Tesseract toujours dépendante du schéma réel installé ;
- V0.23.4 ne produit pas de DCP ;
- pas d’auto-reframe sémantique pour le social ;
- le FILL actuel est un crop centré explicite ;
- les presets custom restent volontairement au niveau projet ; leur transfert entre projets passe par JSON ;
- les cadences custom sont limitées à 24 / 30 / 60 tant que le bridge Tesseract courant conserve cette contrainte ;
- V0.23 ne produit toujours pas de DCP ni d’auto-reframe sémantique.

# Conclusion

V0.23.1 à V0.23.5 forment désormais une chaîne Motion & Delivery complète :

**créer le titre / carton final → régler le style → définir la connexion Storyline → sauvegarder en timeline v6 → publier Vxxx → authorer Tesseract → choisir ou personnaliser un preset → vérifier version/audio/titres/cadrage → choisir FIT ou autoriser explicitement FILL → rendre → inspecter ffprobe → vérifier la conformité → télécharger le livrable et son rapport JSON.**

**V0.23 — Motion & Delivery est terminée.**

La suite de la roadmap revient au hardening avant V1 : refactor progressif de l’état UI, recovery après crash, approfondissement des tests d’interactions timeline, performances catalogue, packaging desktop et premier test PISTE 0 → Tesseract réel → teaser exporté.
