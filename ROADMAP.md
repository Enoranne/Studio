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

## V0.17 — Media Intelligence

- vignettes / filmstrips pré-calculés côté backend ;
- inspection visuelle et sémantique des rushes ;
- fenêtres IN/OUT candidates dérivées du contenu ;
- continuité personnage / accessoire / décor ;
- détection de doublons ou prises proches ;
- raisons éditoriales enrichies sans remplacer la décision humaine.

## V0.18 — Audio & motion

- fades audio en enveloppes natives Tesseract ;
- titres et overlays éditables ;
- carton final ;
- export festival / social ;
- point de connexion graphique déplaçable.

## Avant V1

- refactor progressif des globals JS vers état/actions ;
- recovery après crash ;
- tests navigateur de drag/trim/ripple ;
- performances sur catalogues média importants ;
- packaging desktop Tauri ;
- premier test PISTE 0 → Tesseract réel → teaser exporté.

## Plus tard

- A/B compare synchronisé ;
- teaser 15/30/45 s et bande-annonce 60/75/90 s ;
- adaptateurs Resolve / Premiere si pertinent.
