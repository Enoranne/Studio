# Rapport de validation — PISTE Studio V0.24.0

## Statut

**V0.24.0 — Production Readiness : VALIDÉE ✅**

Cette version ne prétend pas valider un vrai film. Elle prépare et sécurise la première recette réelle **PISTE 0 → Tesseract → livrable**.

## Validation automatisée

Run de référence après intégration UI :

- Python / API / logique métier : **PASS** ;
- JavaScript : **PASS** via `node --check` ;
- Chromium / Playwright : **PASS** ;
- ffmpeg / ffprobe disponibles dans la CI ;
- suite globale : **148 tests passés / 148** ;
- aucune régression fonctionnelle détectée.

## Production Readiness

Le moteur `piste_studio.readiness` contrôle sans mutation :

1. structure du projet ;
2. intégrité du master lorsqu'il existe ;
3. présence des médias catalogués ;
4. présence des fichiers média réels ;
5. disponibilité ffmpeg ;
6. disponibilité ffprobe ;
7. disponibilité et version épinglée de Tesseract ;
8. présence d'une version timeline publiée ;
9. cohérence du `manifest.json`, `brief.yaml` et `timeline.json` ;
10. construction réelle du plan d'authoring ;
11. état du bootstrap Tesseract ;
12. état de l'authoring ;
13. présence d'un rendu source Tesseract.

## Niveaux de capacité

Le rapport expose séparément :

- `can_start_editing` ;
- `can_bootstrap` ;
- `can_author` ;
- `can_deliver`.

Un projet peut donc être prêt au montage sans être encore prêt à l'authoring ou au delivery.

## Sélection de version

Le moteur ne devine pas silencieusement entre plusieurs montages.

- un montage unique peut être sélectionné automatiquement ;
- `--name` cible un montage ;
- `--version` cible une version précise ;
- `--version` sans `--name` est refusé ;
- plusieurs montages publiés sans sélection explicite produisent un diagnostic demandant un choix.

## Prochaine action

Le rapport expose `next_action`.

Selon l'état réel, il demande par exemple :

- ajouter/scanner des rushes ;
- publier une timeline ;
- corriger un plan d'authoring ;
- configurer Tesseract ;
- lancer le bootstrap ;
- lancer l'authoring ;
- produire le rendu source ;
- installer ffmpeg/ffprobe ;
- ouvrir le Delivery Center.

Le diagnostic lui-même ne réalise jamais ces mutations.

## CLI

```bash
piste-studio readiness --root "/chemin/vers/PISTE_0"
```

Options :

```bash
--name teaser_30
--version V001
```

## API

`GET /api/readiness`

Paramètres optionnels :

- `edit_name` ;
- `version`.

## Interface

Deux accès sont validés dans Chromium :

- bouton **Readiness** dans la barre d'outils ;
- `Ctrl/Cmd+K` → **Production · Readiness**.

Le panneau affiche :

- statut global de la chaîne ;
- montage/version ciblés ;
- les quatre capacités ;
- chaque contrôle avec PASS/WARN/BLOCKED ;
- détails utiles médias/Tesseract/authoring ;
- prochaine action ;
- accès au Delivery Center seulement lorsque le rendu source est prêt.

## Politique de sécurité

Le Production Readiness :

- ne modifie pas les rushes ;
- ne modifie pas le master ;
- ne modifie pas la timeline ;
- ne publie aucune version ;
- ne lance pas Tesseract ;
- ne lance pas d'export ;
- ne transforme pas un avertissement en décision éditoriale.

## Étape suivante

**V0.24.1 — Première recette réelle PISTE 0**

Le protocole est défini dans :

`PRODUCTION_TEST_V0.24.md`

La V0.24.1 ne sera déclarée PASS qu'après passage d'un vrai extrait 30–60 s dans la chaîne complète :

**médias réels → montage → audio → titres → publication Vxxx → bootstrap Tesseract → authoring → preview → rendu source → Delivery Center → livrable inspecté.**
