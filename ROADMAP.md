# Roadmap PISTE Studio

## Acquis ✅

- **V0.01** — projet local, master SHA-256, canon, HARD/SOFT/OPEN, SQLite.
- **V0.02** — Decision Engine, trailer-safe/spoiler, versions et PATCH.
- **V0.03** — bridge Tesseract séparé, version pin, dry-run, bootstrap, preview/filmstrip/export.
- **V0.04** — authoring vidéo Tesseract transactionnel.
- **V0.05–V0.09 UI** — Media Library, timeline multi-pistes, drag/trim, viewer multi-source, audio local, waveforms, gain/fades.
- **V0.10** — application locale UI + FastAPI.
- **V0.11** — timeline UI publiée en V001+, authoring Tesseract vidéo + audio.
- **V0.12** — refonte UX : Assemble/Edit/Review, Browser filmstrip, SOURCE/PROGRAM, Inspector contextuel, Timeline Index.
- **V0.13** — Storyline magnétique : reorder/ripple trim, connexions parent/enfant, validation serveur des effets domino contre les locks.
- **V0.14** — hardening : checkpoint/Undo persistant, schema v2, Playwright/Chromium en CI, store d’état UI initial.
- **V0.15** — UX Refinement : Viewer-first, Browser plus visuel, Focus Mode, Overlays et Command Palette.
- **V0.16** — Editorial Intelligence : Favorite/Reject persistants, marqueurs, Source Selector explicable et validation humaine.
- **V0.17** — Media Intelligence : ffprobe, filmstrips backend, empreinte perceptuelle, prises proches et continuité structurée.
- **V0.18** — Semantic Vision & Continuity : embeddings locaux optionnels, références visuelles validées, propositions de tags acceptées/rejetées humainement.
- **V0.19** — Audio Editing & Mixing : dB, pan, rôles, fades graphiques, volume automation, Web Audio, Solo/Mute et meters stéréo.
- **V0.20** — Audio Intelligence & Loudness : LUFS, true peak, silences, normalisation non destructive, clipping estimé, ducking et crossfade.
- **V0.21** — Audio Delivery & Master Check : rendu master ffmpeg, sommation réelle, LUFS-I/true peak master, presets configurables, rapport JSON exportable, limiteur opt-in, empreinte de fraîcheur du mix et préflight export PASS/WARN/STALE/MISSING non bloquant.

## V0.22 — Editorial Vision Refinement

- ✅ **V0.22.1** — fenêtres IN/OUT candidates issues de ruptures/changements visuels, détection ffmpeg locale, sensibilité configurable, validation humaine ;
- ✅ **V0.22.2** — références visuelles ciblées sur un frame ou une zone ROI, indépendantes des tags globaux du rush, intégrées aux preuves de continuité ;
- ✅ **V0.22.3** — groupes de références projet et qualité Primaire/Secondaire/Faible, pondération intra-groupe et équilibrage entre groupes ;
- ✅ **V0.22.4** — détection de conflit entre tags sémantiques, Canon et contexte HARD/SOFT LOCK, avec acquittement humain explicite ;
- ✅ **V0.22.5** — continuité contextuelle plan précédent / plan courant / plan suivant, simulation d’un rush candidat sans mutation et distinction rupture explicite / preuve manquante.

**V0.22 — Editorial Vision Refinement : TERMINÉE ✅**

## V0.23 — Motion & Delivery

- ✅ **V0.23.1** — titres et overlays éditables : timeline schema v5, presets centre/lower-third/haut/custom, style/position/fond/opacité, preview Viewer live et conservation intégrale dans le plan d’authoring ;
- ✅ **V0.23.2** — carton final spécialisé : fond canvas plein, alignement automatique sur la fin de timeline, texte éditable et noir/fond seul final intégré ;
- ✅ **V0.23.3** — point de connexion graphique déplaçable : lignes d’attache visibles, poignée active sur l’élément sélectionné, changement de parent par drag sans déplacer le clip connecté, réglage numérique, locks/checkpoints/Undo et timeline schema v6 ;
- ✅ **V0.23.4** — exports festival / social : Delivery Center, cibles Festival ProRes/H.264, Online 1080p, Social 9:16 et 1:1, préflight version/audio/titres/cadrage, FIT sans perte, FILL/CROP uniquement sur autorisation explicite, transcodage ffmpeg, ffprobe et rapport JSON ;
- ✅ **V0.23.5** — presets de delivery : profils intégrés immuables + presets projet personnalisables, duplication, édition, défaut projet, validation codec/dimensions/FPS, import/export JSON inter-projets et réutilisation complète dans préflight/export.

**V0.23 — Motion & Delivery : TERMINÉE ✅**

## V0.24 — Production Validation

- ✅ **V0.24.0 — Production Readiness** : diagnostic projet/outils/médias/version publiée, sélection prudente de la timeline, validation du plan d'authoring, détection bootstrap/authoring/rendu Tesseract, capacités `can_start_editing / can_bootstrap / can_author / can_deliver`, prochaine action explicite, CLI `piste-studio readiness` et API `/api/readiness` ;
- ⏳ **V0.24.1 — Première recette réelle PISTE 0** : rapport machine de recette intégré (5+ plans, audio, fade, automation, titre, carton final, connexion, delivery) ; validation finale toujours humaine. Reste à exécuter la chaîne sur les vrais médias PISTE 0 et le Tesseract local.

## Avant V1

- valider **V0.24.1** sur le vrai projet PISTE 0 ;
- refactor progressif des globals JS vers state/actions ;
- recovery après crash ;
- tests navigateur approfondis de drag/trim/ripple/fades ;
- performances sur catalogues média importants ;
- finaliser packaging desktop Tauri / notarisation ;
- premier test PISTE 0 → vrai Tesseract → teaser exporté.

## Plus tard

- A/B compare synchronisé ;
- teaser 15/30/45 s et bande-annonce 60/75/90 s ;
- adaptateurs Resolve / Premiere si pertinent.
