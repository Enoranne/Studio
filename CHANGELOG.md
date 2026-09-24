# Changelog

## V0.22 — Editorial Vision Refinement

### V0.22.5 — Continuité de voisinage

- Nouveau moteur `timeline_continuity.py`.
- Analyse du plan sélectionné dans son contexte STORYLINE réel.
- Identification déterministe du plan précédent et du plan suivant.
- Comparaison des facets structurés `character`, `prop`, `decor`, `look`.
- Détection de continuité explicite lorsqu’un tag est partagé.
- Détection de **FACET_RUPTURE** uniquement lorsque deux côtés possèdent des tags structurés incompatibles.
- Détection de **BRIDGE_CONTINUITY** lorsque précédent et suivant partagent une preuve conservée par le plan central.
- Détection de **BRIDGE_EVIDENCE_GAP** lorsque les voisins partagent une preuve que le plan central ne documente pas.
- Les preuves manquantes sont classées **REVIEW / À VÉRIFIER**, jamais comme rupture certaine.
- Statuts de synthèse : **CONTINUOUS**, **RUPTURE**, **REVIEW**, **INSUFFICIENT**, **NO_SIGNAL**.
- Simulation d’un autre rush à la position du clip sélectionné via `candidate_media_id`.
- La simulation ne modifie ni timeline, ni IN/OUT, ni tags.
- Évaluation Canon V0.22.4 incluse pour les tags du candidat.
- API `GET /api/vision/timeline-continuity`.
- Inspector clip vidéo : **CONTINUITÉ DE VOISINAGE → Analyser voisins**.
- Drawer en triptyque **PRÉCÉDENT / PLAN-CANDIDAT / SUIVANT**.
- Sélecteur permettant de tester n’importe quel rush catalogué à cette position.
- Command Palette : **Vision · Continuité voisins**.
- Tests unitaires, API et Chromium dédiés.
- Les candidats simulés héritent du contexte HARD/SOFT LOCK de la position du clip central.
- CI de référence V0.22.5 : **112 tests passés / 112**.
- V0.22 Editorial Vision Refinement complète.

### V0.22.4 — Canon Conflict Detection

- Nouveau moteur `canon_conflicts.py`.
- Normalisation stable des tags sémantiques `character / prop / decor / look`.
- Index Canon combinant personnages, accessoires, décors, look, `visual.avoid` et règles sémantiques explicites.
- Nouvelle section Canon optionnelle :
  - `allowed_tags` ;
  - `forbidden_tags` ;
  - `closed_facets`.
- Statuts : **ALIGNED**, **UNVERIFIED**, **CONFLICT**, **HARD_LOCK**, **REVIEW**.
- Une absence dans le Canon n’est pas considérée comme contradiction sauf si le facet est explicitement fermé.
- `visual.avoid` peut produire un conflit explicite pour le facet `look`.
- Les propositions sémantiques transportent désormais un `canon_assessment` recalculé depuis le Canon courant.
- Détection du contexte HARD/SOFT LOCK lorsque le média proposé est réellement utilisé dans une zone temporelle concernée.
- Un HARD LOCK ne s’applique à la sémantique que si ses opérations interdites couvrent la sémantique, le tag concerné ou toutes les opérations.
- Acceptation d’un conflit/HARD LOCK impossible silencieusement : premier passage renvoie `REQUIRES_ACKNOWLEDGEMENT`.
- L’utilisateur peut ensuite choisir explicitement **Accepter malgré conflit** ; ni Canon ni lock ne sont modifiés.
- UI : badges Canon, raisons et sources visibles sur chaque proposition.
- Vue **Canon & Locks** enrichie avec règles sémantiques.
- Nouveaux projets initialisés avec Canon schema v2 et section `semantic`.
- Tests de classification, closed facets, `visual.avoid`, HARD/SOFT LOCK et override explicite.
- CI de référence : **101+ tests** avant validation Chromium finale.

### V0.22.3 — Groupes et qualité de référence

- Migration SQLite rétrocompatible des références V0.22.2.
- Ajout de `group_name` et `quality` aux références ciblées.
- Trois qualités explicites : **Primaire 1,5×**, **Secondaire 1,0×**, **Faible 0,5×**.
- La pondération s’applique à l’intérieur d’un groupe.
- Les centroïdes de groupes contribuent ensuite à poids égal afin qu’un groupe contenant beaucoup d’images ne domine pas artificiellement les autres.
- Une référence non groupée reste une preuve indépendante.
- Les anciens profils de rush entier restent compatibles et sont traités comme preuves indépendantes.
- Résumé projet des groupes : tag, facet, références, médias, répartition qualité et poids total.
- API PATCH pour modifier groupe/qualité sans recalculer ni modifier le tag global.
- API de résumé `/api/vision/reference-groups`.
- Création d’une référence avec groupe/qualité dès l’origine.
- Déduplication conservée : recréer exactement la même référence met à jour ses métadonnées.
- UI : groupe, qualité, poids visible et édition postérieure.
- Réutilisation des noms de groupes déjà présents dans le projet.
- Les preuves de continuité affichent nombre de groupes et distribution Primaire/Secondaire/Faible.
- Migration d’une base V0.22.2 testée.
- Chromium : création primaire dans « Fisher principal », puis reclassement en faible dans « Fisher secondaire ».
- CI fonctionnelle de référence : **96 tests passés / 96**.

### V0.22.2 — Références visuelles ciblées

- Nouvelle table SQLite `semantic_references`.
- Références explicites attachées à un média, un timecode et un tag structuré.
- Support d’un frame entier ou d’une zone ROI normalisée.
- Extraction locale du frame/crop avec ffmpeg.
- Calcul d’embedding sur la zone extraite, pas nécessairement sur le rush complet.
- Une référence ciblée peut porter `character:`, `prop:`, `decor:` ou `look:` sans ajouter ce tag globalement au média source.
- Déduplication des références strictement identiques.
- Les propositions de continuité combinent références ciblées et anciens profils de rush entier.
- Preuves enrichies : ids des références ciblées, nombre ciblé/legacy, meilleure référence.
- Auto-référence interdite : une zone d’un rush ne peut pas servir à lui proposer son propre tag.
- API CRUD pour créer, lister, afficher et supprimer les références ciblées.
- UI **Référence ciblée** dans SEMANTIC VISION.
- Command Palette : **Vision · Référence ciblée**.
- Sélection frame affiché, facet, valeur, timecode et ROI en pourcentages.
- Aperçu du crop extrait dans la liste de références.
- Aucun tag global ni changement de Storyline automatique.
- Test ffmpeg réel d’extraction ROI.
- Test Chromium de création `prop:fisher` sur une zone et vérification de l’absence de tag global.
- CI de référence : **91 tests passés / 91**.

### V0.22.1 — Fenêtres IN/OUT issues de ruptures visuelles

- Détection locale de changements de scène via ffmpeg `select(scene)`.
- Seuil de sensibilité configurable.
- Parsing déterministe des timestamps de rupture.
- Construction de segments chronologiques entre ruptures.
- Durée minimale de fenêtre configurable.
- Fallback explicite vers le rush complet si aucun segment exploitable ne dépasse la durée minimale.
- API `/api/media/{media_id}/editorial-windows`.
- Politique stricte : suggestion uniquement, validation humaine obligatoire, aucune modification automatique de Storyline.
- Inspector Media Intelligence : bouton **Fenêtres IN/OUT**.
- Tiroir de comparaison avec sensibilité Faible / Normale / Forte.
- Actions **Prévisualiser** et **Charger IN/OUT**.
- Command Palette : **Vision · Fenêtres IN/OUT**.
- Réutilisation du workflow SOURCE existant : charger une fenêtre ne remplace aucun plan monté.
- Test ffmpeg réel avec vidéo synthétique rouge → bleu → vert.
- Test Chromium du parcours jusqu’au chargement effectif de Source IN/OUT.
- CI de référence : **85 tests passés / 85**.


## V0.21 — Audio Delivery & Master Check

- Rendu master audio temporaire local via ffmpeg.
- Sommation réelle des clips audibles de la timeline.
- Respect du Mute/Solo des pistes.
- Prise en compte du gain, de l’automation, des fades, du pan et des overlaps/crossfades.
- Master PCM stéréo 48 kHz / 24 bits en cache.
- Mesure LUFS intégré du master rendu.
- Mesure true peak master après sommation.
- Contrôle séparé loudness / true peak avec statut PASS ou WARN.
- Tolérance loudness configurable.
- Presets de livraison configurables présentés comme repères, jamais comme norme universelle.
- Rapport JSON exportable dans `reports/audio/`.
- Limiteur master désactivé par défaut et disponible uniquement sur choix explicite.
- Aucune normalisation automatique du master.
- Command Palette : **Audio · Master Check**.
- Résultat synthétique affiché dans l’overlay MIX du Viewer.
- API dédiée aux presets, au Master Check et au téléchargement du rapport.
- Empreinte SHA-256 du mix audio enregistrée dans chaque Master Check.
- Détection PASS / WARN / STALE / MISSING avant export.
- Préflight export non bloquant avec choix **Master Check / Exporter quand même / Annuler**.
- État audio renvoyé par l’API d’export pour traçabilité.
- Test ffmpeg réellement end-to-end en CI, avec génération WAV, rendu master et mesure loudnorm.
- ffmpeg système installé explicitement dans GitHub Actions.


## V0.20 — Audio Intelligence & Loudness

- Analyse LUFS intégrée via ffmpeg loudnorm.
- Mesure true peak source.
- Loudness range et threshold persistés.
- Détection locale de plages de silence.
- Table SQLite dédiée aux analyses loudness.
- Analyse par média et par catalogue audio.
- Normalisation non destructive avec cible LUFS configurable.
- Limitation automatique du gain proposé par ceiling true peak.
- Politique de validation humaine avant application.
- Décalage cohérent du gain et des keyframes lors d’une normalisation acceptée.
- Rapport de risque de clipping par clip.
- Distinction explicite entre estimation par clip et mesure master finale.
- Ducking MUSIC piloté par chevauchements VO / DIALOGUE.
- Attack / release / réduction configurables.
- Enveloppe de ducking proposée avant application.
- Crossfade audio contrôlé entre clips adjacents.
- Overlap même piste autorisé uniquement pour un crossfade réciproque explicite.
- Timeline schema v4.
- Inspector LOUDNESS.
- Actions Normaliser / Clipping / Ducking VO / Crossfade suivant.
- Command Palette enrichie pour loudness, normalisation, clipping et ducking.
- Tests moteur, API, UI et Chromium étendus à V0.20.

## V0.19 — Audio Editing & Mixing

- Timeline schema v3.
- Migration automatique du gain legacy 0..1 vers gain dB.
- Gain audio -60 à +12 dB.
- Pan stéréo -1 à +1.
- Rôles dialogue / VO / music / ambience / SFX.
- Volume automation par keyframes.
- Poignées graphiques de fade in / fade out.
- Points d’automation manipulables directement sur les clips.
- Preview Web Audio avec GainNode et StereoPannerNode.
- Bus audio par piste + master.
- Mute / Solo / Lock par piste.
- Solo persisté dans la timeline.
- Meters stéréo L/R dans le Viewer.
- Inspector AUDIO MIX.
- Audio automation dans la Command Palette.
- Authoring Tesseract schema v3.
- gainDb/pan/rôle/fades/enveloppe conservés dans le plan d’authoring.
- Gain statique matérialisé dans Tesseract.
- Automation Tesseract native explicitement différée jusqu’à confirmation du schéma installé.
- Démo migrée en timeline schema v3.
- Tests backend/API/UI/Chromium étendus au mixage audio.

## V0.18 — Semantic Vision & Continuity

- Provider de vision locale optionnel basé sur CLIP.
- Dépendances vision séparées dans l’extra `.[vision]`.
- Aucun téléchargement de modèle sans opt-in explicite.
- Extraction locale d’images de référence via ffmpeg.
- Embedding moyen normalisé par rush.
- Profils sémantiques persistés dans SQLite.
- Références visuelles issues de tags déjà validés.
- Facettes `character:`, `prop:`, `decor:`, `look:`.
- Proposition de tags par centroïde des références.
- Seuils distincts selon la facette.
- État PENDING / ACCEPTED / REJECTED.
- Accept : écrit le tag dans les métadonnées.
- Reject : mémorise le refus et empêche la réapparition silencieuse.
- Aucune écriture automatique de tag.
- Aucune modification automatique de Storyline.
- UI Inspector Semantic Vision.
- Tiroir de propositions avec références, seuil et similarité.
- Command Palette : Analyser le rush / Proposer continuité.
- Tests backend/API/UI/Chromium pour la chaîne référence → proposition → Accept.

## V0.17 — Media Intelligence

- Analyse technique locale via ffprobe.
- Mise à jour automatique d’une durée catalogue manquante.
- Filmstrips JPEG pré-calculés côté backend.
- Cache filmstrip exclu de Git.
- Browser : filmstrip cache au repos, skimming vidéo au survol.
- Empreinte visuelle perceptuelle multi-images locale.
- Mesure de proximité visuelle entre prises.
- Fallback proximité nom/durée lorsque l’empreinte n’est pas disponible.
- Inspector Media Intelligence.
- Tiroir **Prises proches**.
- Source Selector enrichi avec proximité visuelle et facettes de continuité structurées.
- Tags `character:`, `prop:`, `decor:`, `look:` reconnus comme signaux de continuité.
- Dégradation explicite `TOOLS_UNAVAILABLE` lorsque ffmpeg/ffprobe manque.
- Aucun média envoyé vers un service externe.
- Tests moteur/API/UI/Chromium étendus à la Media Intelligence.

## V0.16 — Editorial Intelligence

- Plages Favorite/Reject persistées dans SQLite.
- Affichage des plages persistantes dans les filmstrips Browser.
- Suppression individuelle des plages depuis l’Inspector.
- Marqueurs persistants Note / Décision / Beat / Vigilance.
- Marqueurs visibles sur la règle de timeline.
- Raccourci `M` et composeur de marqueur.
- Editorial Source Selector depuis une source ou un plan STORY.
- Suggestions classées par signaux explicites : tags, canon, safe, rating, Favorite/Reject, spoiler et statut.
- Fenêtre source Favorite proposée en priorité lorsqu’elle existe.
- Prévisualisation d’une suggestion sans modification de la Storyline.
- Chargement explicite d’une plage candidate en SOURCE.
- Politique serveur : validation humaine obligatoire, remplacement automatique désactivé.
- Tests backend/API et Chromium étendus aux fonctions éditoriales.

## V0.15 — UX Refinement

- Viewer plus dominant et surfaces UI simplifiées.
- Browser avec filmstrips plus grands et métadonnées moins envahissantes.
- Workspaces ASSEMBLE / EDIT / REVIEW plus différenciés.
- Focus Mode pour Browser, Viewer, Timeline et Inspector.
- Command Palette via Ctrl/Cmd+K.
- Viewer Overlays configurables.
- Réduction du chrome visuel : bordures, badges et boutons secondaires.
- Couleurs davantage réservées au sens éditorial.
- Ajout d’une charte `UX_GUIDE.md`.
- Tests Chromium étendus aux nouvelles interactions.

## V0.14 — Hardening

- Correction de la navigation multi-vues révélée par le test Chromium.
- Ajout de checkpoints persistants avant les opérations magnétiques.
- Undo persistant côté backend + Ctrl/Cmd+Z et bouton UI.
- Ajout de l’état d’historique dans l’API projet.
- Migration de la démo vers `timeline schema_version: 2`.
- Ajout de Playwright/Chromium à la CI pour de vrais clics UI.
- Surveillance des erreurs JavaScript de page pendant les tests navigateur.
- Introduction du store `PisteState` et migration progressive des états transversaux.
- Conservation des validations Python et `node --check`.

## V0.13 — Magnetic Storyline

- Réordonnancement magnétique des plans STORY.
- Ripple trim IN/OUT avec déplacement automatique des plans en aval.
- Connexions parent/enfant pour TITLES, VO, MUSIC et SFX.
- parentClipId, anchorOffset et connectionMode=follow persistés dans timeline.json.
- Inspector : attacher, changer de parent ou détacher un élément.
- Suppression d’un plan STORY : refermeture magnétique et détachement de ses enfants.
- Validation locale des collisions, bornes source et pistes verrouillées.
- Validation serveur des connexions et de la continuité magnétique.
- Validation des déplacements induits par ripple contre HARD/SOFT LOCKS.
- Migration prudente des anciennes timelines : pas de reflow silencieux au chargement.
- CI renforcée avec node --check sur tous les modules JavaScript.

## V0.12 — UX refactor

- Refonte de l’interface inspirée de patterns éprouvés de logiciels de montage, sans reprendre leur habillage.
- Trois espaces de travail : `ASSEMBLE`, `EDIT`, `REVIEW`.
- Browser à filmstrips avec recherche, filtres, skimming et statut Favorite/Reject pour la plage IN/OUT courante.
- Viewer intelligent `SOURCE / PROGRAM`.
- Inspector contextuel selon la sélection : source vidéo, audio, clip vidéo, audio ou titre.
- Storyline principale visuellement distincte des éléments connectés `TITLES / VO / MUSIC / SFX`.
- Timeline Index `CLIPS / LOCKS / DECISIONS`.
- Browser, Index et Inspector repliables.
- Raccourcis : `1/2/3`, `B`, `I`, `F`, `X`, `P`.
- Les HARD LOCKS du projet réel réhydratent désormais correctement la protection visible dans la timeline.
- La Storyline est volontairement dite « principale » et non « magnétique » : le ripple/attachement automatique n’est pas encore implémenté.
- 29 tests passent.

## V0.11

- Publication de la timeline UI en version immuable `V001 / V002 / …`.
- `timeline.json` devient l’état éditorial autoritaire de la version publiée.
- Authoring Tesseract directement depuis la timeline publiée.
- Matérialisation native des couches `Video` et `Audio`.
- API locale : publication, bootstrap, authoring, preview, filmstrip et export.
- 27 tests passent.

## V0.10

- Première application locale UI + backend.
- Serveur FastAPI `piste-studio-app`.
- Persistance atomique de la timeline de travail.

## V0.05–V0.09 UI

- Media Library, timeline multi-pistes, drag/trim, viewer multi-source, audio local, waveforms, gain/fades.


## V0.23 — Motion & Delivery

### V0.23.2 — Carton final

- Extension du modèle title v5 avec `titleRole = final_card`.
- Fond plein canvas avec couleur et opacité dédiées.
- Ajout de `canvasBackgroundColor`.
- Ajout de `canvasBackgroundOpacity`.
- Ajout de `blackTailSeconds`.
- Validation serveur : le noir final doit être >= 0 et strictement inférieur à la durée du carton.
- Bouton timeline **+ Carton final**.
- Création par défaut alignée exactement sur la fin de la timeline.
- Durée par défaut 3,5 s, avec queue noire/fond seul de 0,75 s.
- Inspector spécialisé **CARTON FINAL**.
- Preview PROGRAM avec fond plein au-dessus du plan vidéo.
- Pendant la queue finale, le texte disparaît mais le fond canvas reste visible.
- Command Palette : **Titre · Ajouter un carton final**.
- Conservation intégrale dans les `title_cuts` de l’authoring plan.
- Les champs de fond plein et de noir final restent présents dans `unmaterialized_titles` tant que la couche Text native Tesseract n’est pas documentée.
- Tests API : persistance du carton et rejet d’une queue noire invalide.
- Test authoring : conservation du fond plein et du noir final.
- Test Chromium : création, édition, extinction du texte, alignement exact sur la fin et sauvegarde.
- CI fonctionnelle de référence : **119 tests passés / 119**.

### V0.23.1 — Titres et overlays éditables

- Timeline schema v5.
- Validation serveur d’un modèle de titre portable.
- Texte jusqu’à 500 caractères.
- Presets : centre, lower-third, haut, custom.
- Familles génériques : sans, serif, mono.
- Taille 12–240 et graisse 100–900.
- Alignement gauche / centre / droite.
- Position X/Y normalisée.
- Largeur de boîte normalisée.
- Couleur et fond `#RRGGBB`.
- Opacité texte et fond.
- Padding et arrondi normalisés.
- Inspector complet **TITRE / OVERLAY**.
- Preview live dans PROGRAM Viewer.
- Redimensionnement proportionnel au Viewer.
- Suppression de l’ancien éditeur texte minimal en doublon.
- `+ Titre` crée désormais un overlay v5 à la position du playhead.
- Sauvegarde/rechargement backend de tous les paramètres.
- Authoring plan schema v4 avec `title_cuts`.
- Le style complet est conservé dans `authoring-plan.json`.
- Le manifest expose `unmaterialized_titles` lorsque le schéma Tesseract installé ne confirme pas une couche Text compatible.
- PISTE Studio refuse d’inventer la structure d’une couche Text native Tesseract.
- App/UI version portée à v0.23.
- Chromium : édition lower-third, serif, taille, alignement, couleur, fond, padding, arrondi et persistance.
- CI fonctionnelle de référence : **116 tests passés / 116**.
