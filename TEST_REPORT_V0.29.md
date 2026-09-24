# Rapport de validation — PISTE Studio V0.29

## Statut

**TIMELINE CORE RELIABILITY : FUSIONNÉE DANS MAIN ✅**

Pull request : **#5**

Commit de fusion : `79e610a3fb22eee13c15ee9600b3186fb833ae8d`

## Validation automatisée

Tête finale de la PR #5 : `d476adf7b39d2fb1480433b2527efdf1dffc49b6`

- **187 tests passés / 187** ;
- syntaxe JavaScript : PASS ;
- tests Python : PASS ;
- tests Chromium / navigation réelle : PASS ;
- installation des dépendances : PASS ;
- ffmpeg disponible dans la CI : PASS.

Un avertissement de dépréciation Starlette/httpx est présent dans la dépendance de test ; il ne constitue pas un échec fonctionnel de V0.29.

## Paliers validés

### V0.29.1 — Integer Timebase

- timebase interne entier à 1 MHz ;
- conversion secondes/ticks déterministe ;
- positions de frames rationnelles ;
- reflows répétés sans accumulation de bruit flottant ;
- format public des timelines conservé en secondes.

### V0.29.2 — Canonical Storyline Kernel

Surface unique `apply_storyline_operation` pour :

- move ;
- trim ;
- connection point ;
- attach / detach ;
- insert ;
- remove ;
- reflow.

Le pipeline backend applique validation avant/après et contrôle des locks.

### V0.29.3 — Backend-authoritative gestures

En utilisation connectée, les gestes principaux délèguent leur mutation au backend :

- reorder ;
- ripple trim ;
- changement de parent ;
- déplacement du point de connexion ;
- réglage numérique du point de connexion.

Le JavaScript conserve la preview interactive et le fallback navigateur autonome.

### V0.29.4 — Insert / Remove & Lock Safety

- insert/remove VIDEO passent par le kernel ;
- les changements de présence sont contrôlés par les HARD/SOFT LOCKS ;
- sémantique existante conservée : `reorder`, `graphics`, `audio_change` ;
- checkpoint Storyline enregistré de façon atomique avec l’opération backend.

## Compatibilité

- timeline schema : **v6 inchangé** ;
- JSON public : secondes inchangées ;
- anciens projets : compatibles ;
- Canon : inchangé ;
- MASTER : inchangé ;
- checkpoints persistants existants : conservés.

## Packaging

La version Python/FastAPI/Tauri est alignée sur **0.29.0**.

Les builds macOS ARM64 / Intel et leurs smoke tests restent une validation packaging distincte. Ils ne sont pas déclarés validés dans ce rapport tant que leurs jobs dédiés n’ont pas été vérifiés.

## Suite

Le prochain chantier structurel prévu est le **Transaction Journal** : transactions de geste, coalescing, Redo et provenance User/Agent, tout en conservant les checkpoints persistants comme filet de sécurité.

Son numéro de version doit être vérifié contre l’état réel du dépôt immédiatement avant création.
