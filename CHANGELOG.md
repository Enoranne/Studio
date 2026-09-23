# Changelog

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
