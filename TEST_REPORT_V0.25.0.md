# TEST REPORT — PISTE Studio V0.25.0

Date : 24 septembre 2026

## Statut

**VALIDÉ CÔTÉ DÉPÔT / CI**

Commit fonctionnel de référence : `8222e5b7a15c0ba929aee55acce20fd6bb9c2520`.

La fondation desktop macOS et le parcours de première utilisation V0.25.0 sont validés en intégration continue.

## Tests applicatifs

Workflow : `tests`

Résultat de référence :

- **153 tests passés / 153** ;
- vérification syntaxique JavaScript incluant désormais `piste_studio/ui` et `desktop/src` ;
- 1 warning de dépendance Starlette/httpx, non bloquant et sans échec fonctionnel.

Le delta par rapport à V0.24.1 ajoute deux tests dédiés au mode de création de projet du sidecar desktop :

- création d’un projet neuf ;
- refus d’une destination déjà non vide.

## Packaging macOS

Workflow : `desktop-macos`

Run de référence : `36027042704`.

### Apple Silicon / ARM64

- job : **SUCCESS** ;
- bundle `.app` : généré ;
- DMG : généré ;
- signature ad-hoc : vérifiée ;
- création d’un projet par le sidecar réellement empaqueté : **PASS** ;
- démarrage du backend empaqueté : **PASS** ;
- endpoint `/api/health` : **PASS** ;
- version backend `0.25.0` : **PASS** ;
- artefact : `piste-studio-macos-arm64` ;
- taille archive CI : environ 38,1 Mo.

### Intel / x86_64

- job : **SUCCESS** ;
- bundle `.app` : généré ;
- DMG : généré ;
- signature ad-hoc : vérifiée ;
- création d’un projet par le sidecar réellement empaqueté : **PASS** ;
- démarrage du backend empaqueté : **PASS** ;
- endpoint `/api/health` : **PASS** ;
- version backend `0.25.0` : **PASS** ;
- artefact : `piste-studio-macos-x86_64` ;
- taille archive CI : environ 40,2 Mo.

## First Run validé

Le lanceur V0.25.0 propose désormais :

1. **Ouvrir un projet…** ;
2. **Nouveau projet…** ;
3. saisie d’un nom ;
4. choix d’un dossier parent ;
5. création de la structure PISTE Studio par le sidecar embarqué ;
6. démarrage du backend local ;
7. validation HTTP de `/api/health` ;
8. vérification que `project_root` correspond au projet demandé ;
9. ouverture de la fenêtre Studio sans Terminal.

Le contrôle de disponibilité n’est donc plus un simple test de port TCP.

## Versions alignées

Les composants suivants déclarent désormais `0.25.0` :

- package Python `piste-studio` ;
- FastAPI et `/api/health` ;
- shell Rust/Tauri ;
- `tauri.conf.json` ;
- package desktop Node.

## Hors validation automatique

Deux validations restent volontairement extérieures à cette recette :

1. **Developer ID / notarisation Apple** : le workflow est préparé, mais son exécution exige les secrets et certificats Apple Developer du propriétaire du compte.
2. **Recette vraie PISTE 0 + Tesseract** : installation du DMG sur la machine de production, ouverture du vrai projet, lecture 30–60 s, authoring/rendu Tesseract et contrôle humain du résultat.

Ces deux points ne constituent plus des lacunes d’implémentation du packaging V0.25.0.
