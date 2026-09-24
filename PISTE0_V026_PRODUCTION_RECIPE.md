# PISTE 0 — Recette réelle V0.26 Editorial Agent

## Objectif

Valider V0.26 sur un **vrai passage de PISTE 0**, sans confondre validation
machine et validation artistique.

Chaîne cible :

```text
rushes PISTE 0
  → pistes audio
  → transcript
  → candidats
  → AI Timeline View
  → stratégie éditoriale
  → Proposed Edit / EDL virtuelle
  → VALIDATION HUMAINE
  → transaction Storyline + checkpoint
  → publication
  → Tesseract
  → Rendered Master Critic
  → recette V0.24.1 / Delivery
```

La première recette doit rester petite : **30 à 60 secondes**, avec environ
**5 à 12 rushes réels**. Il faut inclure au moins un rush comportant une piste
parlée exploitable pour tester réellement Transcript Intelligence.

## Règle PISTE 0

PISTE 0 ne doit pas devenir un montage « transcript-first ». Le film repose
aussi sur le silence, les objets, les gestes, les ambiances, la continuité
visuelle et le rythme.

Le transcript est donc **un signal parmi plusieurs** :

```text
AUDIO + IMAGE + TEMPS + CONTINUITÉ + INTENTION
```

Un silence narratif ou une respiration ne devient jamais une coupe simplement
parce qu'un détecteur le signale.

## Nouveau rapport de recette

La commande suivante ne modifie rien :

```bash
piste-studio editorial-production-run \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --media-id 12 13 14 18 21
```

Pour enregistrer le rapport :

```bash
piste-studio editorial-production-run \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --media-id 12 13 14 18 21 \
  --save
```

Si `--media-id` est omis, le rapport utilise d'abord les médias VIDEO déjà
présents dans la timeline de travail. Si la timeline ne contient encore aucun
plan, il examine le catalogue VIDEO du projet.

Le rapport est écrit dans :

```text
reports/production/<edit>_<version>_editorial-v026-production-run.json
```

## Étapes contrôlées

### 1. Rushes réels

Les médias doivent être catalogués et présents sur disque.

**PASS** signifie que le rapport travaille réellement avec les fichiers du
projet, pas avec des fixtures.

### 2. Audio Track Intelligence

Pour chaque rush retenu :

- analyser les pistes embarquées ;
- repérer les pistes silencieuses ;
- contrôler codec/canaux/sample-rate ;
- choisir explicitement la piste utile.

Aucune transcription n'est lancée automatiquement.

### 3. Transcript Engine

Sur au moins un rush parlé représentatif :

- conserver les timestamps mot/phrase ;
- conserver les fillers ;
- conserver les speakers lorsque disponibles ;
- utiliser le cache ;
- ne jamais envoyer un média vers ElevenLabs sans consentement explicite.

L'import d'un transcript externe/local reste possible sans réseau.

### 4. Candidats

Contrôler les trois familles :

- silences ;
- fillers ;
- retakes.

Ces éléments restent uniquement des **candidats**.

### 5. AI Timeline View

Vérifier ensemble :

- filmstrip ;
- waveform ;
- transcript ;
- informations audio ;
- Semantic Vision / références ciblées ;
- candidats éditoriaux.

L'objectif est de juger une séquence avec plusieurs signaux simultanés.

### 6. Stratégie éditoriale

Brief conseillé pour le premier passage :

> Construire un extrait PISTE 0 de 30–60 secondes qui conserve la progression
> narrative, les respirations utiles, le rôle du son et la continuité
> personnages/accessoires/décors. Ne pas couper un silence uniquement parce
> qu'il est détecté. Préserver les favoris, exclure les rejects et ne modifier
> aucune zone HARD LOCK.

La stratégie actuelle reste déterministe et explicable. Elle n'est pas encore
un « réalisateur LLM » autonome.

### 7. Proposed Edit

Créer une EDL virtuelle.

Critères :

- la Storyline doit rester inchangée ;
- les médias source restent inchangés ;
- la proposition doit référencer ses segments SOURCE ;
- le rapport doit rester lisible avant application.

### 8. Validation humaine

C'est un **garde-fou obligatoire**.

Avant Apply Proposal :

- regarder les segments proposés ;
- vérifier le rythme ;
- vérifier les silences ;
- vérifier la logique PISTE 0 ;
- vérifier Canon / HARD-SOFT locks ;
- accepter ou rejeter.

Le rapport affiche alors `AWAITING_HUMAN_VALIDATION`.

### 9. Storyline

Après validation seulement :

- checkpoint Undo ;
- contrôle anti-stale ;
- validation locks ;
- transaction Storyline.

### 10. Tesseract

Publier ensuite la version puis suivre le `readiness` existant :

```bash
piste-studio readiness --root "/chemin/vers/PISTE_0" --name teaser_30
```

Puis bootstrap / author / preview / filmstrip / export selon le
`next_action`.

### 11. Rendered Master Critic

Le Critic intervient **sur le fichier réellement rendu**.

Il contrôle notamment :

- flux vidéo/audio ;
- durée ;
- plages noires internes ;
- LUFS / true peak ;
- cohérence technique avec la timeline.

Il ne corrige rien automatiquement.

### 12. Boucle finale V0.24.1

Une fois le Master Critic examiné, exécuter :

```bash
piste-studio production-run \
  --root "/chemin/vers/PISTE_0" \
  --name teaser_30 \
  --save
```

V0.26 valide ainsi l'intelligence éditoriale ; V0.24.1 valide ensuite le
montage publié, Tesseract et le Delivery Center.

## Statuts

- `BLOCKED` : rushes réels absents/inaccessibles ;
- `IN_PROGRESS` : prochaine brique machine identifiée ;
- `AWAITING_HUMAN_VALIDATION` : EDL virtuelle prête, Apply interdit sans humain ;
- `AWAITING_FINAL_REVIEW` : Tesseract + Master Critic présents, visionnage final requis.

Il n'existe volontairement **aucun PASS artistique automatique**.

## Extension V0.27 — VO séparée → images

Le point de vigilance identifié en V0.26 est désormais couvert par le
**Voice-to-Visual Editorial Bridge V0.27**.

Une VO stockée dans `audio/` peut être transcrite indépendamment puis guider :

```text
phrase / intention
→ rushes présélectionnés
→ fenêtres Editorial Vision
→ tags + références Semantic Vision
→ Favorite / Reject
→ comparaison de plans
→ EDL VO→image virtuelle
→ validation humaine
```

Le test réel PISTE 0 doit maintenant mesurer la pertinence artistique des
candidats, notamment sur les silences, les motifs sonores et les passages où
l’image doit volontairement **ne pas illustrer littéralement** la phrase.
