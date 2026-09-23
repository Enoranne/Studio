# Changelog

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
