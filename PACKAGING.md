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

1. ouvre un sélecteur de dossier natif ;
2. refuse un dossier sans `project.yaml` ;
3. choisit un port localhost libre ;
4. démarre le sidecar embarqué ;
5. attend que le backend écoute réellement ;
6. ouvre PISTE Studio dans une fenêtre desktop ;
7. arrête le sidecar lorsque la fenêtre Studio se ferme.

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

- valider le build Tauri en CI macOS ;
- tester Apple Silicon et Intel ;
- définir l'icône finale ;
- automatiser signature/notarisation sans stocker de secret dans le dépôt ;
- éventuellement embarquer ou guider l'installation de ffmpeg/ffprobe ;
- garder Tesseract comme dépendance externe explicitement détectée par Readiness.

## Principe produit

Le packaging ne doit jamais affaiblir les garanties existantes :

- master immuable ;
- médias source non destructifs ;
- localhost uniquement ;
- aucune télémétrie imposée ;
- Tesseract séparé ;
- diagnostic Readiness disponible avant production.
