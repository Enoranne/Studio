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
- groupes de références et qualité de référence ;
- détection de conflit entre tags sémantiques et Canon ;
- comparaison de continuité plan précédent / plan suivant.

## V0.23 — Motion & Delivery

- titres et overlays éditables ;
- carton final ;
- point de connexion graphique déplaçable ;
- exports festival / social ;
- presets de delivery.

## Avant V1

- refactor progressif des globals JS vers state/actions ;
- recovery après crash ;
- tests navigateur approfondis de drag/trim/ripple/fades ;
- performances sur catalogues média importants ;
- packaging desktop Tauri ;
- premier test PISTE 0 → vrai Tesseract → teaser exporté.

## Plus tard

- A/B compare synchronisé ;
- teaser 15/30/45 s et bande-annonce 60/75/90 s ;
- adaptateurs Resolve / Premiere si pertinent.
