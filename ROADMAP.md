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

## V0.25 — Desktop Packaging & First Run

- ✅ **V0.25.0 — Packaging desktop macOS** : shell Tauri v2, sidecar PyInstaller, ouverture de projet sans Terminal, création de projet au premier lancement, validation réelle de /api/health, bundles .app/.dmg ARM64 et x86_64, smoke tests du bundle et signature ad-hoc de test ;
- ⏳ **Distribution Developer ID / notarisation** : workflow préparé, exécution conditionnée à la fourniture des secrets/certificats Apple Developer. Cette étape ne bloque pas les builds de test locaux.

**V0.25 — FONDATION PACKAGING UTILISATEUR TERMINÉE ✅**

## V0.26 — Editorial Agent & Transcript Intelligence

- ✅ **V0.26.1 — Audio Track Intelligence** : inventaire des pistes audio embarquées, codec/canaux/sample-rate, mesure peak/mean, détection de piste silencieuse, recommandation non contraignante et sélection explicite persistée pour transcription ;
- ✅ **V0.26.2 — Transcript Engine** : extraction de la piste choisie, cache par média/piste/provider/modèle/hash source, import de transcript, Scribe v2 opt-in, timestamps mot, diarisation et regroupement en phrases ;
- ✅ **V0.26.3 — Transcript Panel SOURCE/PROGRAM** : transcript cliquable, navigation SOURCE et suivi de la phrase correspondant au playhead PROGRAM ;
- ✅ **V0.26.4 — Silence / filler / retake candidates** : pauses, disfluences et formulations répétées deviennent des signaux explicables, jamais des coupes automatiques ;
- ✅ **V0.26.5 — AI Timeline View** : filmstrip, waveform compacte, transcript, pistes audio, références Semantic Vision et candidats de coupe réunis dans une vue machine compacte ;
- ✅ **V0.26.6 — Take Comparator** : comparaison de formulations entre rushes transcrits avec similarité textuelle, sans désigner automatiquement une « meilleure » prise ;
- ✅ **V0.26.7 — Editorial Strategy** : stratégie en langage naturel construite à partir du brief, de la cible de durée, des transcripts, favoris/rejets et niveau spoiler ;
- ✅ **V0.26.8 — Proposed Edit** : EDL virtuelle persistée avec timeline candidate, Storyline inchangée tant que la proposition reste PENDING ;
- ✅ **V0.26.9 — Apply Proposal** : confirmation humaine, contrôle anti-stale par hash, validation timeline, locks, checkpoint Undo puis transaction Storyline ;
- ✅ **V0.26.10 — Rendered Master Critic** : ffprobe, durée, présence audio/vidéo, plages noires, LUFS/true peak et rapport persistant ; diagnostic uniquement, revue humaine toujours requise.
- ✅ **V0.26.11 — Editorial Production Run / recette PISTE 0** : rapport non destructif de progression rushes → pistes audio → transcript → candidats → AI Timeline View → stratégie → EDL virtuelle → validation humaine → Storyline → Tesseract → Master Critic ; CLI, API et affichage dans l'Editorial Agent ; aucun appel réseau ni Apply automatique.

**V0.26 — FONDATION EDITORIAL AGENT FUSIONNÉE DANS MAIN ✅**

Validation de code V0.26 : **162 tests passés / 162** après ajout de la recette PISTE 0, syntaxe JavaScript validée. Le bundle macOS V0.26 a atteint construction, signature et démarrage du sidecar avec `/api/health` en 0.26.0 ; le garde-fou de smoke test resté en 0.25.0 a été corrigé. La chaîne de recette PISTE 0 est désormais instrumentée de bout en bout ; reste à l'exécuter sur les médias locaux réels PISTE 0 et à effectuer le smoke final du workflow macOS courant. Les appels de transcription externes restent explicitement opt-in.

## V0.27 — Voice-to-Visual Editorial Bridge

- ✅ **V0.27.1 — VO source indépendante** : transcript audio/VO utilisable même lorsque la parole n’est pas embarquée dans le rush vidéo ;
- ✅ **V0.27.2 — Phrase / intention → images** : intention explicite optionnelle, mots-clés, métadonnées et tags ;
- ✅ **V0.27.3 — Text ↔ Semantic Vision** : embeddings texte CLIP locaux optionnels et comparaison avec profils / références ciblées, sans téléchargement silencieux ;
- ✅ **V0.27.4 — Fenêtres candidates & comparaison** : Editorial Vision, Favorite/Reject, score détaillé, comparaison de plans, aucun gagnant appliqué automatiquement ;
- ✅ **V0.27.5 — VO→Image Proposed Edit** : beats visuels, pauses VO conservées, EDL virtuelle, VO préservée et validation via le pipeline transactionnel V0.26.

**V0.27 — VOICE-TO-VISUAL EDITORIAL BRIDGE FUSIONNÉE DANS MAIN ✅**

## V0.28 — UX Navigation & Context System

- ✅ **V0.28.1 — Context Design Tokens** : accents discrets Video / Audio / Transcript / Editorial / Delivery / Projet, avec libellés explicites ;
- ✅ **V0.28.2 — Contextual Help** : Guidée / Minimale / Désactivée et micro-textes de conséquence ;
- ✅ **V0.28.3 — Universal Search** : Actions / Aller à / Aide / Ressources, recherche visible + Cmd/Ctrl+K ;
- ✅ **V0.28.4 — Context Quick Actions** : raccourcis utiles selon la sélection sans masquer les outils avancés ;
- ✅ **V0.28.5 — Help Center** : FAQ, glossaire, workflow, raccourcis et principes de sécurité intégrés ;
- ✅ **V0.28.6 — Action Semantics** : repères Analyse / Proposition / Application / Rendu ;
- ✅ **V0.28.7 — UX Preferences** : Confort/Compact, couleurs et actions contextuelles configurables localement.

**V0.28 — UX NAVIGATION & CONTEXT SYSTEM FUSIONNÉE DANS MAIN ✅**

Validation V0.28 : **170 tests passés / 170**, syntaxe JavaScript validée sur la tête finale de la PR #4. Les builds macOS 0.28.0 restent une validation packaging distincte tant qu’ils ne sont pas terminés.

## V0.29 — Timeline Core Reliability

- ✅ **V0.29.1 — Integer Timebase** : ticks entiers 1 MHz, conversion déterministe secondes/ticks, positions de frames rationnelles et Storyline sans accumulation de dérive flottante ;
- ✅ **V0.29.2 — Canonical Storyline Kernel** : surface backend unique pour move, trim, connexion, attach/detach, insert, remove et reflow, avec validation + locks ;
- ✅ **V0.29.3 — Backend-authoritative gestures** : reorder, ripple trim et points de connexion délégués au kernel en mode connecté ;
- ✅ **V0.29.4 — Insert / Remove & Lock Safety** : ajout/suppression VIDEO délégués au kernel et protégés par la sémantique `reorder` des HARD/SOFT LOCKS existants.

**V0.29 — TIMELINE CORE RELIABILITY IMPLÉMENTÉE SUR BRANCHE DE VALIDATION ⏳**

Compatibilité : timeline schema v6 inchangé, JSON public toujours en secondes, anciens projets conservés. Le backend devient l'autorité des mutations magnétiques en mode connecté ; le JS garde la preview immédiate et le fallback autonome.
## Avant V1

- valider **V0.24.1** sur le vrai projet PISTE 0 ;
- tester le DMG V0.25 sur la machine de production avec un vrai projet ;
- exécuter la signature Developer ID / notarisation si une diffusion publique macOS est souhaitée ;
- refactor progressif des globals JS vers state/actions ;
- recovery après crash ;
- tests navigateur approfondis de drag/trim/ripple/fades ;
- performances sur catalogues média importants ;
- premier test PISTE 0 → vrai Tesseract → teaser exporté.

## Plus tard

- A/B compare synchronisé ;
- teaser 15/30/45 s et bande-annonce 60/75/90 s ;
- adaptateurs Resolve / Premiere si pertinent.
