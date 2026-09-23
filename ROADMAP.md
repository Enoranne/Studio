# Roadmap PISTE Studio

## Acquis ✅

- **V0.01** — projet local, master SHA-256, canon, HARD/SOFT/OPEN, SQLite.
- **V0.02** — Decision Engine, trailer-safe/spoiler, versions et PATCH.
- **V0.03** — bridge Tesseract séparé, version pin, dry-run, bootstrap, preview/filmstrip/export.
- **V0.04** — authoring vidéo Tesseract via checkout/commit, sourceRange/activeRange, remplacement atomique.
- **V0.05–V0.09 UI** — Media Library, timeline multi-pistes, drag/trim, viewer multi-source, audio local, waveforms, gain/fades.
- **V0.10** — application locale UI + FastAPI, projet réel comme source de vérité.
- **V0.11** — timeline UI publiée en V001+, authoring Tesseract vidéo + audio, preview/export depuis l’application.

## V0.12 — Audio & review hardening

- matérialiser les fades audio en enveloppes natives Tesseract ;
- vérifier le mix final et les éventuelles doubles lectures audio ;
- comparer structure avant/après authoring ;
- afficher preview/filmstrip directement dans l’UI ;
- checkpoint / rollback explicite.

## V0.13 — Editorial Source Selector

- inspection des rushes avant coupe ;
- filmstrips sources et waveform ;
- fenêtres IN/OUT candidates ;
- raisons éditoriales par coupe ;
- validation humaine avant matérialisation.

## V0.14 — Titres & motion graphics

- titres éditables ;
- overlays ;
- carton final ;
- motifs graphiques canon ;
- export festival / social.

## Plus tard

- A/B compare synchronisé ;
- teaser 15/30/45 s et bande-annonce 60/75/90 s ;
- desktop shell Tauri ;
- adaptateurs Resolve / Premiere si pertinent.
