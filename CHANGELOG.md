# Changelog

## V0.22 — Editorial Vision Refinement

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
