# PISTE Studio — Recette de production V0.24

## Objectif

Valider PISTE Studio sur un **vrai extrait de PISTE 0** et non plus seulement sur des fixtures de test.

La recette V0.24.1 est réussie uniquement si un montage réel de **30 à 60 secondes** traverse toute la chaîne :

**médias réels → montage → audio → titres → version publiée → Tesseract → rendu source → Delivery Center → livrable final contrôlé.**

## 1. Préflight de la machine et du projet

Depuis l'environnement virtuel PISTE Studio :

```bash
piste-studio readiness --root "/chemin/vers/PISTE_0"
```

Si plusieurs montages publiés existent :

```bash
piste-studio readiness --root "/chemin/vers/PISTE_0" --name teaser_30
```

Pour cibler exactement une version :

```bash
piste-studio readiness --root "/chemin/vers/PISTE_0" --name teaser_30 --version V001
```

Le rapport distingue :

- `can_start_editing` ;
- `can_bootstrap` ;
- `can_author` ;
- `can_deliver` ;
- `next_action`.

Le même rapport est disponible dans l'application via :

`GET /api/readiness`

## 2. Montage réel à utiliser

Le premier essai doit rester volontairement petit mais représentatif.

Cible :

- 30–60 s ;
- au moins 5 plans vidéo réels ;
- au moins une source VO ou dialogue ;
- une musique ou ambiance si pertinente ;
- au moins un fade audio ;
- au moins une automation ou variation de gain si elle est utile au passage ;
- un titre ou overlay ;
- un carton final ;
- au moins un élément connecté à la Storyline ;
- aucune modification destructive des rushes ou du master.

L'objectif n'est pas de fabriquer le meilleur teaser possible. L'objectif est de forcer les principales briques de PISTE Studio à travailler ensemble.

## 3. Publication

Dans l'UI :

1. scanner le projet ;
2. monter le passage ;
3. vérifier les connexions Storyline ;
4. enregistrer ;
5. effectuer le Master Check audio ;
6. publier une version `Vxxx`.

Relancer ensuite :

```bash
piste-studio readiness --root "/chemin/vers/PISTE_0" --name teaser_30
```

Le check doit alors sélectionner la dernière version timeline publiée et construire un plan d'authoring exploitable.

## 4. Bootstrap Tesseract

Le `next_action` doit proposer une commande équivalente à :

```bash
piste-studio tesseract bootstrap \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --version V001 \
  --execute
```

Après bootstrap, le dossier de version doit contenir :

- le `.tsrct` ;
- `.tesseract-work/document.schema.json` ;
- les informations d'inspection/schema capturées par PISTE Studio.

Relancer le readiness check.

## 5. Authoring

Quand `can_author=true` :

```bash
piste-studio tesseract author \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --version V001 \
  --execute
```

Vérifier ensuite :

- import des vidéos ;
- import des sources audio ;
- conservation des plages SOURCE ;
- position des plans ;
- gain audio statique ;
- présence des informations d'automation/pan/fades dans le manifest ;
- état des titres : matérialisés ou explicitement signalés comme non matérialisés ;
- aucun changement des médias source ;
- aucun changement du master protégé.

## 6. Preview réelle

Produire au minimum une frame et un filmstrip :

```bash
piste-studio tesseract preview \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --version V001 \
  --time 5
```

```bash
piste-studio tesseract filmstrip \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --version V001 \
  --duration-ms 30000 \
  --interval-ms 1000
```

Points de contrôle :

- ordre des plans ;
- source IN/OUT ;
- raccords ;
- ratio/canvas ;
- titres ;
- carton final ;
- absence de média manquant.

## 7. Rendu source Tesseract

Pour le premier essai :

```bash
piste-studio tesseract export \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --version V001 \
  --resolution 1080p \
  --fps 24 \
  --format mp4
```

Le fichier attendu par défaut est :

`edits/teaser_30/V001/teaser_30_V001.mp4`

Relancer le readiness check. Il doit pouvoir atteindre :

`READY_FOR_DELIVERY`

si ffmpeg et ffprobe sont disponibles.

## 8. Delivery Center

Dans l'application :

1. ouvrir **Export** ;
2. choisir **Online · H.264 · 1080p** pour la première recette ;
3. vérifier le préflight ;
4. ne pas utiliser FILL sauf intention explicite ;
5. lancer l'export ;
6. inspecter le rapport ffprobe ;
7. télécharger/conserver le rapport JSON.

Critères minimum :

- vidéo H.264 ;
- 1920×1080 ;
- 24 fps pour cette recette ;
- yuv420p ;
- audio AAC ;
- 48 kHz ;
- 2 canaux ;
- rapport de conformité sans anomalie inexpliquée.

## 9. Critères de réussite V0.24.1

La recette est **PASS** si :

- PISTE Studio reste utilisable du scan à l'export ;
- aucun média source n'est modifié ;
- le master protégé reste intact ;
- la timeline publiée correspond au montage voulu ;
- Tesseract reçoit les médias et timings attendus ;
- le rendu source est lisible ;
- le Delivery Center produit un livrable conforme ;
- toutes les pertes fonctionnelles sont explicites ;
- aucune correction éditoriale n'est appliquée silencieusement.

La recette est **FAIL** si une étape exige une manipulation cachée, détruit de l'état, perd un média/titre/audio sans signalement, ou produit un rendu différent du montage sans diagnostic explicite.

## 10. Journal de friction

Pour chaque problème rencontré, noter :

| Étape | Gravité | Symptôme | Contournement | Correction produit |
| --- | --- | --- | --- | --- |
| Import | P0/P1/P2/P3 |  |  |  |
| Montage | P0/P1/P2/P3 |  |  |  |
| Audio | P0/P1/P2/P3 |  |  |  |
| Publication | P0/P1/P2/P3 |  |  |  |
| Tesseract | P0/P1/P2/P3 |  |  |  |
| Delivery | P0/P1/P2/P3 |  |  |  |

Priorité :

- **P0** : perte/corruption de données ou master ;
- **P1** : bloque la recette ;
- **P2** : contournement possible mais UX ou résultat dégradé ;
- **P3** : détail ou polish.

Cette liste de friction devient la source de vérité du hardening pré-V1.
