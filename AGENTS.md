# Instructions pour Codex — PISTE Studio (projet appelé « Tesseract » dans nos échanges)

**Date de transmission : 15 octobre 2026.** Dépôt canonique : https://github.com/Enoranne/Studio — branche `main`.

## 1. Mission et périmètre

Tu reprends un **projet existant** de logiciel de montage audiovisuel **PISTE Studio**. L'utilisateur appelle parfois l'ensemble « Tesseract », mais **Tesseract de Mirage est un moteur externe distinct**, invoqué au moyen d'un bridge. Ne le confonds pas avec le code propriétaire PISTE Studio ; ne l'intègre, ne le copie, ne le redistribue et ne le modifie pas. Lire `LICENSE`, `LICENSE_NOTE.md` et `THIRD_PARTY_NOTICES.md` avant les décisions d'architecture.

L'utilisateur est créateur audiovisuel, non développeur. Son objectif concret : pouvoir **installer et utiliser une application Mac agréable**, importer de vrais rushes de son film « PISTE 0 — BONUS TRACK (REC) », visualiser images et son, monter via une **Storyline magnétique type Final Cut Pro**, sauvegarder/reprendre un projet, puis prévisualiser et **exporter une vidéo réelle**. Garder la direction à long terme : VO/SFX/titres connectés, intelligence éditoriale, transcription et montage proposé non destructif. Ne pas substituer un prototype factice à un produit utilisable.

## 2. État établi et points à vérifier

- État de GitHub consulté le 15/10/2026 : `main` au commit `c505c2de431cc8003dc9eb59c60c424966dcae21` ; `pyproject.toml` indique **0.29.0**.
- Le rapport `TEST_REPORT_V0.29.md` **annonce** 187/187 tests et V0.29 « Timeline Core Reliability » fusionnée. **Relancer toi-même les tests** : ce rapport n'est pas une preuve de validation du logiciel installé sur Mac avec des rushes réels.
- Les anciennes discussions mentionnent un **DMG macOS Apple Silicon 0.29.1**, et un chantier **V0.30 Transaction Journal** non fusionné. Vérifier l'existence, la provenance, l'état Git et les éventuelles branches/PR avant d'utiliser ou de créer une version. **Ne pas supposer que 0.29.1 est dans `main`.**
- Dans les essais utilisateur antérieurs : interface excessivement petite en plein écran, apparition d'une fenêtre Terminal, difficultés pratiques pour importer/tester des rushes ; aucune validation complète du parcours réel import → lecture/son → trim → sauvegarde → export n'est acquise.
- Environnement visé : **Mac Apple Silicon (probablement M4)**, également tenir compte du packaging Intel si celui-ci est maintenu. Médias réels potentiellement GH5, y compris H.264/H.265, UHD/4K, 10 bits 4:2:2 : vérifier la compatibilité et prévoir des **proxies** plutôt que garantir une lecture native fluide.
- PISTE Studio utilise Python/FastAPI, une interface web intégrée, Tauri v2, FFmpeg/ffprobe et un bridge externe Tesseract. Vérifier chaque point dans le code au lieu d'extrapoler depuis les descriptions.

## 3. Architecture et acquis à protéger

Le projet revendique notamment :
- Storyline magnétique avec point de connexion visible et déplaçable, reflow/trim/reorder déterministes, `apply_storyline_operation` backend, timebase interne entière à 1 MHz ; **timeline schema v6 et secondes publiques compatibles** ;
- Canon, HARD/SOFT LOCKS, checkpoints, versions et modifications éditoriales non destructives ;
- média/vision/audio intelligence, recherche de fenêtres candidates, transcript synchronisé, comparaison de prises ;
- V0.26 Editorial Agent : propositions d'EDL **virtuelles**, validation humaine obligatoire avant `Apply Proposal`, et `Master Critic` après rendu ;
- V0.27 Voice-to-Visual ; V0.28 interface contextuelle, aide optionnelle et recherche `Cmd/Ctrl+K` ;
- presets de livraison festival / social et pont vers le moteur de rendu externe.

**Ne jamais casser silencieusement** les anciens fichiers projet, locks, schémas, chemins média, exports, principes de validation ou flux de travail. Aucune mutation automatique du montage par un agent : l'humain approuve l'application. Aucune transmission silencieuse de médias/audio à des prestataires cloud ; consentement explicite.

## 4. Ordre de travail obligatoire

### Phase A — Inventaire technique (d'abord, sans refonte)

1. Inspecter le dépôt réellement disponible : branches, PR ouvertes, tags, releases, versions, dépendances, documentation, CI, tests, build, packaging, commandes de démarrage et interfaces.
2. Identifier **fonctionnalité par fonctionnalité** ce qui existe dans le code, ce qui est testé, ce qui est seulement documenté et ce qui reste à faire. Ne pas déduire « terminé » du seul README.
3. Reproduire localement les tests, noter commandes, résultats, dépendances manquantes et limitations d'environnement ; étudier sécurité des sauvegardes et chemins des projets.
4. Chercher l'état effectif de V0.29.1 et V0.30, les éventuels travaux non fusionnés, et tout risque de double développement.
5. Produire un **AUDIT_INITIAL_CODEX.md** compréhensible par un non-développeur : commit, versions, fonctions, risques bloquants, résultats des tests, proposition de mini-feuille de route.

### Phase B — Priorité produit : usage réel sur Mac

Dans une **branche dédiée**, après l'audit, ne traiter en premier que les blocages du parcours minimal :

1. Installation et lancement clairs, sans Terminal parasite, messages lisibles en français ; compatibilité et démarrage macOS Apple Silicon.
2. UI utilisable en plein écran sur iMac : taille des textes, contrôles, densité et zones de travail, avec contraste suffisant et zoom/panneaux si nécessaire.
3. Création/ouverture d'un projet et import fiable de rushes MOV/MP4, WAV et fichiers courants ; métadonnées ffprobe et erreurs compréhensibles.
4. Lecture SOURCE/PROGRAM avec image et **audio synchronisé**, gestion des fichiers lourds par proxies/cache avec diagnostic de codec ; jamais masquer un média incompatible.
5. Timeline : placer un plan, déplacer, faire un trim, gérer les attaches et connexions sans détériorer les locks/versions.
6. Sauvegarder, fermer, rouvrir : retrouver la Storyline et les liens médias, avec gestion des chemins déplacés.
7. **Exporter réellement** un court montage, contrôler le fichier final (durée, image, son) et présenter les presets.
8. Recette sur vrais médias PISTE 0 si l'utilisateur les fournit ; sinon préparer jeu d'essai synthétique reproductible et indiquer « validation réelle en attente ».

Une **démonstration bout-en-bout** prouvée compte davantage que dix nouvelles fonctionnalités.

### Phase C — Seulement ensuite

- Reprendre/évaluer V0.30 **Transaction Journal** (undo/redo, regroupement des gestes, provenance utilisateur/agent), sans dupliquer le système de checkpoints.
- Durcir les transcriptions, la comparaison de prises, l'AI Timeline View, la proposition éditoriale/validation, le Master Critic et le pont Tesseract, dans cet ordre logique selon les dépendances réelles.
- Étudier seulement à titre optionnel les inspirations `browser-use/video-use`, Magnetic, OpenScene, WeftCut, Clypra, OpenFilm, Continuity Studio, VoiceStudio ; auditer réellement licences et code avant toute réutilisation. **Ne pas intégrer automatiquement** de dépôt tiers ou de service payant (Higgsfield inclus).

## 5. Règles d'exécution et de sécurité

- Travailler sur une **nouvelle branche**, faire des commits petits et traçables, ouvrir une PR en brouillon pour revue ; **ne pas pousser directement sur main ni fusionner sans validation de l'utilisateur**.
- Ne pas écraser de projet, film, rush, master, sauvegarde ou secret. Ne pas committer de rushes propriétaires, gros binaires, mots de passe, clés API ou fichiers personnels.
- Pas d'achat, d'appel API facturé ou de lancement massif de génération sans information préalable sur le coût et accord explicite.
- Respecter la licence propriétaire originale et les licences tierces ; Tesseract/Mirage reste externe.
- Conserver une batterie de tests, ajouter des régressions pertinentes, vérifier l'absence de régression de la timeline v6 et des locks ; lorsqu'un test ne peut pas être exécuté, expliquer précisément pourquoi.
- Adapter la consommation de Codex Plus : demandes de taille maîtrisée, ne pas lancer des tâches coûteuses sans bénéfice mesurable.
- **Pas de promesse de DMG fonctionnel** avant compilation effective, smoke tests, et validation sur Mac réel. Signaler signature/notarisation manquante au lieu d'inventer une validation.
- Pour chaque phase : livrer un résultat vérifiable, commandes de test, captures ou logs pertinents, commit/PR et explication courte en français.

## 6. Première réponse attendue de Codex

**Commencer par l'audit A, pas par une refonte ou un ajout d'IA**. Fournir :

1. Version et commit réels, branches/PR candidates, état du code et du build.
2. Liste « opérationnel prouvé / présent non testé / incomplet / non disponible ».
3. Liste des 5 obstacles prioritaires au parcours Mac réel.
4. Plan concret de 3 itérations courtes, chacune avec tests et critères d'acceptation.
5. Lancer les tests accessibles et reporter les résultats. Si une correction minime et sûre débloque les tests, l'effectuer sur une branche dédiée, sans toucher à main.

**Critère de succès initial :** le propriétaire peut ouvrir l'application, importer un rush, le lire avec son son, l'éditer sur la Storyline, sauvegarder et exporter un fichier lisible sur son Mac.
