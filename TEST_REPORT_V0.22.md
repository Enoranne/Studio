# PISTE Studio v0.22.1 — Rapport de validation Editorial Vision / Fenêtres IN-OUT

Date : 23 septembre 2026

## Périmètre

Cette validation couvre la première brique de V0.22 :

**proposer des fenêtres SOURCE IN/OUT à partir de ruptures/changements visuels détectés localement.**

Les autres objectifs V0.22 restent ouverts :

- références visuelles ciblées sur une zone ou un frame ;
- groupes et qualité de références ;
- conflits tags sémantiques / Canon ;
- comparaison de continuité plan précédent / plan suivant.

## Résultat

- Python/API/UI : **85 tests passés / 85**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium / Playwright : succès.
- ffmpeg système installé explicitement dans la CI.
- Test réel de rupture visuelle exécuté, sans mock.
- Aucune modification automatique de Storyline.

## Détection de ruptures

Le moteur V0.22.1 utilise ffmpeg avec le signal `scene`.

Le seuil est borné et configurable.

Valeurs UI :

- Faible : 0,45 ;
- Normale : 0,32 ;
- Forte : 0,22.

Plus le seuil est bas, plus l’analyse peut retenir de changements visuels.

Le moteur parse les timestamps réellement sélectionnés par ffmpeg puis les déduplique.

## Construction des fenêtres

À partir de :

    début rush → rupture 1 → rupture 2 → ... → fin rush

PISTE Studio construit des fenêtres chronologiques.

Chaque fenêtre contient :

- Source IN ;
- Source OUT ;
- durée ;
- rupture précédente ;
- rupture suivante ;
- méthode `ffmpeg_scene_change` ;
- seuil utilisé ;
- raison textuelle.

Les segments plus courts que la durée minimale configurable sont ignorés.

Si aucun segment ne dépasse cette durée, le moteur propose explicitement le rush complet comme fallback pour validation humaine plutôt que de prétendre qu’aucune source n’est exploitable.

## Politique éditoriale

La réponse API porte explicitement :

- `suggestion_only = true` ;
- `automatic_storyline_edit = false` ;
- `human_validation_required = true` ;
- `local_processing = true`.

La détection ne peut donc pas constituer silencieusement une décision de montage.

## API

Nouvelle route :

`GET /api/media/{media_id}/editorial-windows`

Paramètres :

- `threshold` ;
- `min_duration` ;
- `limit`.

La route refuse les médias non vidéo et signale explicitement l’absence de ffmpeg ou du fichier source.

## Interface

Nouvel accès dans **MEDIA INTELLIGENCE** :

**Fenêtres IN/OUT**

Nouvelle commande :

**Vision · Fenêtres IN/OUT**

Le tiroir affiche :

- le rush concerné ;
- la politique « aucune coupe automatique » ;
- la sensibilité ;
- le nombre de ruptures ;
- le seuil technique ;
- les fenêtres candidates.

Pour chaque fenêtre :

- **Prévisualiser** ;
- **Charger IN/OUT**.

Le workflow réutilise le mécanisme SOURCE existant.

## Test Chromium

Le scénario navigateur valide :

1. sélection d’un rush ;
2. ouverture **Fenêtres IN/OUT** ;
3. présence de la politique **RUPTURES VISUELLES** ;
4. trois fenêtres simulées ;
5. sensibilité Normale ;
6. clic sur **Charger IN/OUT** ;
7. valeurs Source IN = 0 et Source OUT = 2 visibles dans l’Inspector ;
8. aucune erreur JavaScript.

## Test ffmpeg réel

Le test crée une vidéo synthétique de trois plans francs :

**rouge 1 s → bleu 1 s → vert 1 s**

Puis il appelle réellement le moteur de détection.

Validé :

- rupture proche de 1,00 s ;
- rupture proche de 2,00 s ;
- au moins trois fenêtres candidates ;
- politique sans montage automatique.

Ce test démontre que le cœur V0.22.1 ne dépend pas uniquement de fixtures ou de réponses mockées.

## UX

Principes ajoutés :

- une rupture visuelle est un signal, pas une décision de coupe ;
- les bornes doivent être visibles ;
- la méthode doit rester auditable ;
- la sensibilité ne doit pas être présentée comme une mesure de « qualité » ;
- l’adoption d’une plage reste une action humaine explicite.

## Limites

- la détection de scène repère un changement visuel, pas nécessairement un bon point de montage narratif ;
- un mouvement de caméra, un flash ou un changement lumineux peut produire une rupture ;
- un plan continu long sans coupure ne fournit pas à lui seul de sous-fenêtres sémantiques ;
- aucune analyse de visage, personnage, objet ou qualité de jeu n’est impliquée dans cette étape ;
- la prochaine couche V0.22 devra pouvoir cibler un frame ou une zone précise plutôt qu’un rush entier.

## Conclusion

V0.22.1 introduit une première assistance de **dérushage interne au rush**.

PISTE Studio ne se contente plus de considérer un média vidéo comme un bloc unique : il peut maintenant repérer des transitions visuelles et proposer des plages SOURCE directement exploitables, tout en préservant la philosophie du projet :

**détecter → expliquer → prévisualiser → laisser l’utilisateur décider.**
