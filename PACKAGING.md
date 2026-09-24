# PISTE Studio — Packaging Desktop

## Objectif

Le packaging desktop doit permettre d'utiliser PISTE Studio sans ouvrir Terminal et sans installer Python manuellement.

Architecture retenue :

```text
PISTE Studio.app
  └─ Tauri v2
      ├─ lanceur natif
      ├─ sélecteur de dossier projet
      ├─ fenêtre WebView Studio
      └─ sidecar piste-studio-backend
           └─ FastAPI + UI PISTE Studio empaquetés par PyInstaller
```

Tesseract reste volontairement séparé et n'est ni redistribué ni modifié par PISTE Studio.

## V0.25.0 — Packaging foundation

Le dépôt contient :

- `desktop/` : shell Tauri ;
- `scripts/desktop_backend_entry.py` : entrée du backend gelé ;
- `scripts/build_desktop_backend.sh` : construction du sidecar PyInstaller ;
- `scripts/build_desktop_macos.sh` : build local macOS complet ;
- `.github/workflows/desktop-macos.yml` : build macOS reproductible en CI.

Le lanceur :

1. permet soit d’ouvrir un projet existant, soit d’en créer un nouveau ;
2. pour un nouveau projet, demande un nom et un dossier parent puis initialise la structure via le sidecar embarqué ;
3. pour un projet existant, refuse un dossier sans `project.yaml` ;
4. choisit un port localhost libre ;
5. démarre le sidecar embarqué ;
6. interroge réellement `/api/health` et vérifie que le backend répond pour le dossier projet attendu ;
7. ouvre PISTE Studio dans une fenêtre desktop ;
8. arrête le sidecar lorsque la fenêtre Studio se ferme.

## Construire sur macOS

Prérequis développeur :

- macOS 10.15+ ;
- Xcode / Command Line Tools ;
- Python 3.10+ ;
- Rust stable ;
- Node.js LTS.

Puis :

```bash
bash scripts/build_desktop_macos.sh
```

Sorties attendues :

```text
desktop/src-tauri/target/release/bundle/macos/PISTE Studio.app
desktop/src-tauri/target/release/bundle/dmg/PISTE Studio_*.dmg
```

## Architecture CPU

PyInstaller produit par défaut un binaire pour l'architecture de la machine de build.

Sur macOS :

- Apple Silicon → `arm64` ;
- Intel → `x86_64` ;
- `universal2` est possible uniquement avec un Python et toutes les dépendances compatibles universal2.

Le script nomme automatiquement le sidecar avec le target triple attendu par Tauri.

## Signature et notarisation

Le build de développement peut être utilisé localement sans distribution publique signée.

Pour une diffusion propre hors Mac personnel, il faudra :

1. certificat **Developer ID Application** ;
2. signature de l'application ;
3. notarisation Apple ;
4. stapling du ticket ;
5. validation Gatekeeper sur une machine propre.

Ces opérations nécessitent un compte Apple Developer pour une distribution vérifiée/notarisée.

## Ce qui reste après V0.25.0

La fondation d’installation utilisateur est terminée côté dépôt. Restent des validations ou choix de distribution externes :

- tester le DMG sur la machine de production avec un vrai projet et les médias PISTE 0 ;
- exécuter la signature Developer ID et la notarisation Apple si une diffusion publique est souhaitée ;
- éventuellement embarquer ou guider plus explicitement l’installation de ffmpeg/ffprobe ;
- conserver Tesseract comme dépendance externe explicitement détectée par Readiness.

## Principe produit

Le packaging ne doit jamais affaiblir les garanties existantes :

- master immuable ;
- médias source non destructifs ;
- localhost uniquement ;
- aucune télémétrie imposée ;
- Tesseract séparé ;
- diagnostic Readiness disponible avant production.


## État validé au 24 septembre 2026

### V0.25.0 — validée

Le workflow macOS a produit avec succès sur un runner Apple Silicon :

- `PISTE Studio.app` ;
- `PISTE Studio_0.24.1_aarch64.dmg` ;
- sidecar PyInstaller `aarch64-apple-darwin` ;
- artifact GitHub Actions `piste-studio-macos`.

Le premier artifact validé faisait environ 38 Mo compressé.

### Validation bi-architecture

Le workflow `desktop-macos.yml` utilise désormais une matrice :

- `macos-14` → ARM64 / Apple Silicon ;
- `macos-15-intel` → x86_64 / Intel.

Chaque architecture construit son propre sidecar PyInstaller puis son propre bundle Tauri.

### Smoke test du bundle

Après le build, la CI :

1. localise le sidecar réellement contenu dans `PISTE Studio.app` ;
2. vérifie qu'il est exécutable ;
3. crée un mini-projet PISTE Studio ;
4. démarre le sidecar gelé sur un port localhost libre ;
5. appelle `/api/health` ;
6. refuse le build si le backend empaqueté ne répond pas.

Cela teste le backend **dans le bundle**, pas seulement l'environnement Python de CI.

### Signature de test

La configuration de développement utilise désormais :

```json
"signingIdentity": "-"
```

Il s'agit d'une signature ad-hoc destinée aux builds de test. Elle ne remplace pas Developer ID ni la notarisation Apple.

### Release signée et notarisée

Le workflow manuel `.github/workflows/release-macos.yml` est préparé pour les deux architectures.

Secrets GitHub attendus :

- `APPLE_CERTIFICATE` ;
- `APPLE_CERTIFICATE_PASSWORD` ;
- `KEYCHAIN_PASSWORD` ;
- `APPLE_ID` ;
- `APPLE_PASSWORD` ;
- `APPLE_TEAM_ID`.

Le workflow importe le certificat Developer ID, construit avec Tauri, puis vérifie `codesign`, le ticket de notarisation avec `stapler` et l'évaluation Gatekeeper avec `spctl`.

Aucun secret Apple n'est stocké dans le dépôt.


### First Run V0.25.0

L’écran d’accueil expose désormais deux parcours :

- **Ouvrir un projet…** : sélection d’un dossier contenant déjà `project.yaml` ;
- **Nouveau projet…** : saisie du nom, choix d’un dossier parent, création automatique de la structure PISTE Studio puis ouverture immédiate.

La création est exécutée par le **sidecar réellement empaqueté**, avec la même logique `init_project` que le CLI. La CI reproduit ce parcours avant de démarrer le serveur du projet créé.

Le contrôle de démarrage ne se contente plus de vérifier qu’un port TCP est ouvert. Le shell attend une réponse HTTP 200 de `/api/health`, parse le JSON et vérifie que `project_root` correspond au projet demandé. Cela évite d’ouvrir la WebView sur un service étranger ou un backend démarré sur le mauvais dossier.

### Version

À partir de V0.25.0, les versions suivantes sont alignées sur `0.25.0` :

- package Python ;
- FastAPI / `/api/health` ;
- shell Rust/Tauri ;
- configuration Tauri ;
- package desktop Node.
