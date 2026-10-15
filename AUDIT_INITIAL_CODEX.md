# Audit initial PISTE Studio — 15 octobre 2026

## Conclusion pour l’utilisateur

Le dépôt contient un vrai socle de montage, de sauvegarde, de contrôles éditoriaux et de livraison. Il ne démontre cependant pas encore le parcours complet d’une application Mac prête à monter un film : importer un rush, entendre son son, monter, fermer, rouvrir et exporter. Aucun rush personnel n’a été utilisé ni modifié pendant cet audit.

L’audit est réalisé avant les corrections, sur `main` au commit **f6a55be969740e8b789ca43ecd038a0048a3bd75**, puis sur la branche dédiée **codex/audit-macos-stability**. Ce commit ajoute `AGENTS.md` au-dessus de `c505c2d`. Le document a été lu intégralement, ainsi que `LICENSE`, `LICENSE_NOTE.md` et `THIRD_PARTY_NOTICES.md`. Tesseract/Mirage demeure un moteur externe, non modifié et non redistribué.

## Versions, historique et travaux à préserver

| Élément | Constat vérifié |
|---|---|
| Version du code principal | **0.29.0**, Python, UI, package desktop, Cargo et Tauri. Une constante de diagnostic Rust reste à 0.25.0. |
| Correctif macOS | Branche `v0.29.1-macos-sidecar-hotfix`, `68733a5`, [PR ouverte nº 7](https://github.com/Enoranne/Studio/pull/7), non fusionnée. |
| Journal transactionnel | Branche `v0.30-transaction-journal`, `3029bc7`, [PR ouverte nº 6](https://github.com/Enoranne/Studio/pull/6), non fusionnée. Modifie notamment historique, API, UI et tests : ne pas refaire ce chantier. |
| CI principale | [Tests réussis pour f6a55be](https://github.com/Enoranne/Studio/actions/runs/38708832856). Cette réussite Linux ne valide pas l’application installée. |
| CI 0.29.1 | [Build macOS réussi](https://github.com/Enoranne/Studio/actions/runs/36112613806), artefacts arm64 et x86_64 datés du 25 septembre, annoncés non expirés par GitHub. |
| CI 0.30 | [Dernière exécution en échec](https://github.com/Enoranne/Studio/actions/runs/36053953300). À diagnostiquer avant reprise, sans fusion automatique. |
| Tags / releases | Aucun tag récupéré ; aucune release publiée renvoyée par l’API. Les artefacts CI ne sont pas une release notarée. |
| Application déjà installée | `PISTE Studio.app` annonce **0.29.1**. Exécutables desktop et backend **arm64**, signatures **ad hoc**, sans Team ID. `codesign --verify --deep --strict` réussit. Aucun commit de provenance n’est indiqué dans les métadonnées examinées. |

Le correctif de la PR nº 7 sépare les builds locaux ad hoc sans Hardened Runtime des builds Developer ID et transmet l’identité de signature à PyInstaller. Sur `main`, `hardenedRuntime=true` et `signingIdentity="-"` sont encore associés. Reprendre ce travail existant plutôt que réinventer le correctif.

## Inventaire fonctionnel, code et preuves

« Prouvé » ci-dessous désigne le périmètre effectivement testé, pas une validation générale avec des rushes GH5.

| Fonction | État | Preuve et limite |
|---|---|---|
| Créer/ouvrir un projet | Opérationnel prouvé côté Python/API | `project.py`, `desktop_backend_entry.py`, tests : YAML, SQLite, dossiers, refus d’écraser un dossier occupé. Fenêtre Tauri non validée par ces tests. |
| Catalogue vidéo/audio/image | Opérationnel prouvé pour le scan | `media.py` scanne `rushes`, `audio`, `graphics`, conserve des chemins relatifs et des IDs SQLite. L’extension identifie le type ; ce n’est pas une validation de codec. |
| Import par sélecteur | Incomplet | `ui/backend.js` associe les vidéos existantes par nom via une URL mémoire. Un fichier audio peut être ajouté seulement à la session navigateur, sans ID persistant. Aucun endpoint d’import durable de rushes. |
| Métadonnées / filmstrips | Présent, dépendances externes absentes ici | `media_intelligence.py` utilise ffprobe et FFmpeg. L’analyse est distincte du scan. Avant analyse, l’UI substitue 5 s pour une vidéo sans durée connue et 2 s pour l’audio. |
| Lecture SOURCE / PROGRAM | Présente mais défaut audio certain dans le code initial | Lecteur HTML vidéo, navigation source et horloge PROGRAM en JavaScript. `index.html` déclare le lecteur principal `muted` ; aucune réactivation du son vidéo trouvée. Les erreurs de lecture PROGRAM sont souvent absorbées. |
| Mix VO / musique / SFX | Présent et tests de modèle | Web Audio, gain, panoramique, fades, solo et enveloppes. Le Master Check FFmpeg ne collecte que les clips `audioDbId`, pas le son embarqué des vidéos : il ne certifie pas tout le mix final. |
| Proxies / cache de lecture | Incomplet | Dossier `proxies` créé mais aucune génération et sélection automatique de proxies identifiée. Les filmstrips ne sont pas des proxies de lecture. Pas de garantie GH5 4K/10 bits. |
| Storyline magnétique | Opérationnel prouvé par tests du noyau | `storyline.py`, `timebase.py`, `timeline.py` : insertion, reflow, déplacement, trim et connexions ; schéma v6, ticks internes à 1 MHz, secondes publiques. |
| Locks / propositions humaines | Opérationnel dans les chemins testés, couverture à renforcer | Tests HARD/SOFT, validation Storyline et propositions refusées sans confirmation. L’endpoint direct de sauvegarde ne compare pas au montage précédent via `validate_locked_change` ; les contrôles ne sont pas centralisés. |
| Sauvegarde / reprise | Présente avec limites concrètes | `save_timeline` valide puis remplace le JSON temporaire ; chemins relatifs pour le catalogue. Pas de mécanisme de reliaison durable UI identifié. Un nom temporaire fixe est utilisé ; concurrence non sécurisée. Le scan recharge la timeline et peut écarter des modifications locales non enregistrées. |
| Projet neuf | Défaut initial identifié | `hydrateTimeline(null)` retourne sans vider les clips de démonstration initialisés dans `editor.js`. Ils peuvent rester visibles dans un nouveau projet réel. |
| Historique | Checkpoints présents | V0.29 propose undo par snapshots. V0.30 ajoute un journal : ne pas le dupliquer. Pas de preuve d’atomicité multi-fichiers en cas d’arrêt brutal. |
| Export vidéo / presets | Présent, parcours complet non prouvé ici | Publication → bootstrap/authoring Tesseract externe → export → transcodage FFmpeg. Presets festival/social, contrôle de cadrage et rapports. Plusieurs tests de bridge exécutent un faux CLI et écrivent des octets factices : ils ne prouvent pas une vidéo lisible. |
| Transcription / agent éditorial / vision | Présents, tests de logique | Consentement cloud, propositions virtuelles, validation humaine, anti-stale et Master Critic. Pas d’appel cloud ni téléchargement de modèle pendant l’audit. Qualité sur rushes personnels non évaluée. |
| Interface Mac | Présente, utilisabilité insuffisamment validée | Tauri ouvre une fenêtre 1440×900 ; nombreux textes CSS entre 5,8 et 9 px. Le mode confort/compact ne fournit pas de véritable échelle de texte. Pas de test Safari/WKWebView dans la CI. |

## Tests réellement lancés avant correction

Machine : **macOS 26.6.2 arm64**. Python isolé **3.12.14**, Node **24.19.0**. Pas de Command Line Tools Apple, de Rust/Cargo, de FFmpeg/ffprobe ni de CLI Tesseract détecté dans les emplacements standard consultés.

Commandes, depuis la racine du dépôt, avec le Python du virtualenv et Node explicitement accessibles dans le PATH :

```sh
python -m pip install --index-url https://pypi.org/simple -e '.[dev]'
python -m pytest --collect-only -q
python -m pytest -q --ignore=tests/test_ui_browser.py
for f in piste_studio/ui/*.js desktop/src/*.js; do node --check "$f" || exit 1; done
```

- **187 tests collectés**.
- Hors navigateur : **168 réussis, 10 échoués, 4 ignorés** en 5,97 s.
- Les 10 échecs utilisent des faux CLI dont le shebang impose `/usr/bin/python3`. Sur ce Mac, ce chemin demande les outils Apple absents, même si un Python fonctionnel lance pytest. C’est un défaut de portabilité des fixtures de tests ; cela ne prouve pas un défaut du moteur Tesseract réel.
- Les 4 tests ignorés nécessitent FFmpeg/ffprobe. Le détail est conservé dans les résultats complémentaires.
- Syntaxe de tous les fichiers JavaScript : **réussie**.
- Les 5 tests navigateur ne sont pas inclus dans ce premier résultat. Installation Chromium en cours à ce stade ; résultat final séparé ci-dessous ou dans le bilan de corrections.
- Dépendances nouvellement résolues : FastAPI 0.143.1, Uvicorn 0.54.0, PyYAML 6.0.3, pytest 9.1.1, HTTPX 0.28.1, Playwright 1.64.0. Avertissement Starlette sur l’usage de HTTPX. Pas de verrouillage Python, npm ou Cargo committé : les builds futurs peuvent résoudre d’autres versions.
- Tentative de création d’un projet synthétique avec le backend de l’application installée : arrêt du lanceur PyInstaller avec `semctl: Operation not permitted` dans le bac à sable Codex. **Inconclusif pour un lancement Finder** ; ne pas attribuer cet échec au correctif 0.29.1.
- Aucun DMG compilé localement. Les outils Apple et Rust manquent ; ni signature Developer ID ni notarisation validées. L’examen des sources ne démontre pas la cause de la fenêtre Terminal vue précédemment : le launcher Tauri invoque un sidecar sans script Terminal explicite.

## Les cinq obstacles prioritaires

1. **Installation reproductible et lancement Mac** : correctif 0.29.1 non fusionné, outils médias non fournis/détectables de façon garantie depuis Finder, validation WKWebView et notarisation à faire.
2. **Import durable et compatibilité** : association mémoire confondue avec import ; durées de remplacement ; reliaison et proxies absents.
3. **Lecture avec son et diagnostic** : vidéo muette dans l’UI initiale, erreurs de décodage peu visibles, Master Check incomplet pour le son embarqué.
4. **Confiance dans le projet enregistré** : clips fictifs au démarrage d’un projet neuf, perte possible d’état local lors d’un scan, sauvegardes/checkpoints concurrents et chemins de validation des locks à durcir.
5. **Lisibilité et export vérifié** : textes trop petits ; absence de recette complète Mac avec vrai fichier final contrôlé en durée, image et son.

## Trois itérations proposées

### 1 — Ouvrir, comprendre et conserver son travail

Reprendre séparément la PR nº 7, corriger les défauts évidents de projet neuf et de son, rendre les tests portables, améliorer la taille des contrôles puis protéger l’état non enregistré lors des scans/fermetures. Ajouter un diagnostic lisible des dépendances externes.

**Acceptation** : lancement Finder sur Apple Silicon sans Terminal, nouveau projet vide, source audible, mute VIDEO cohérent, sauvegarde/réouverture identique, absence de régression schéma v6 et locks. Un build testé ne doit pas être présenté comme notaré s’il ne l’est pas.

### 2 — Importer et monter de vrais rushes

Import persistant sans écrasement, ffprobe avant montage, erreurs compréhensibles, reliaison et proxies avec sources intactes. Vérifier SOURCE/PROGRAM, son embarqué et pistes séparées, trim/déplacement/connexions, reprise après fermeture et déplacement du dossier projet.

**Acceptation** : recette synthétique reproductible MOV/MP4/WAV, puis extraits GH5 fournis volontairement ; image/son synchronisés, durée correcte, aucune référence perdue. Aucun envoi cloud implicite.

### 3 — Livrer un montage vérifié

Tester le bridge avec une installation externe Tesseract épinglée, contrôler tout le mix final (y compris son vidéo), les titres et deux presets de livraison. Stabiliser la chaîne CI macOS et les versions de dépendances. Ensuite seulement réévaluer la PR nº 6 et son journal transactionnel.

**Acceptation** : exporter 10–30 s, vérifier codec, durée, dimensions, image et audio du fichier final puis le lire sur le Mac. Contrôler les rushes/master inchangés. Validation réelle PISTE 0 en attente de médias fournis.

## Première tranche de corrections

La tranche initiale reste limitée à la portabilité des fixtures de tests, au projet neuf sans clips de démonstration et au son du lecteur principal avec respect du mute VIDEO. Les résultats après correction sont consignés dans `BILAN_CORRECTIONS_CODEX.md`. Les corrections ne changent ni le schéma v6, ni les locks, ni les propositions éditoriales, ni le moteur Tesseract, ni les branches 0.29.1/0.30.
