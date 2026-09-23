# PISTE Studio

PISTE Studio est un environnement local de montage/production piloté par **canon, locks, versions, PATCH, historique de sécurité, décisions éditoriales, intelligence média, continuité visuelle et mixage audio non destructif**. Tesseract reste un moteur externe installé séparément : il n’est ni redistribué ni modifié ici.

## V0.21 — Audio Delivery & Master Check

La V0.21 ferme le principal écart audio restant : PISTE Studio peut désormais contrôler **le mix réellement rendu**, après sommation des sources audibles de la timeline.

### Master Check

Depuis la Command Palette (`Ctrl/Cmd+K` → **Audio · Master Check**), l’application :

- rend localement un master audio temporaire via ffmpeg ;
- respecte Mute/Solo, gain dB, automation, fades, pan et crossfades ;
- mesure ensuite le LUFS intégré et le true peak du master ;
- compare séparément loudness et plafond true peak ;
- retourne un statut **PASS** ou **WARN** avec les raisons ;
- génère un rapport JSON exportable dans `reports/audio/`.

Le rendu de contrôle est stéréo 48 kHz / 24 bits et reste dans le cache du projet. Les médias source ne sont jamais modifiés.

### Presets de livraison

PISTE Studio propose des presets de référence configurables. Ils ne sont pas présentés comme des normes universelles : la cible LUFS, le ceiling true peak et la tolérance restent modifiables selon le diffuseur, le festival ou le contexte de livraison.

### Limiteur explicite

Le limiteur master est **désactivé par défaut**. Il n’est ajouté au rendu que si l’utilisateur l’active volontairement. Il n’existe ni normalisation master automatique, ni correction silencieuse.

## V0.20 — Audio Intelligence & Loudness

La V0.20 ajoute une couche de contrôle et d’assistance audio au mixage V0.19.

### Analyse loudness locale

PISTE Studio utilise ffmpeg pour mesurer les sources audio :

- LUFS intégré ;
- true peak source ;
- loudness range (LRA) ;
- seuil loudness ;
- plages de silence détectées.

Les résultats sont persistés dans SQLite et restent associés au média source.

### Normalisation non destructive

L’utilisateur choisit une cible LUFS et un ceiling true peak.

PISTE Studio calcule alors un **ajustement de gain proposé**.

Si le gain nécessaire pour atteindre la cible ferait dépasser le ceiling true peak, la proposition est limitée et l’interface l’indique explicitement.

Exemple :

    source          -20.0 LUFS
    true peak        -4.0 dBTP
    cible           -16.0 LUFS
    ceiling          -1.5 dBTP

    gain théorique    +4.0 dB
    gain proposé      +2.5 dB
    résultat estimé  -17.5 LUFS
    TP estimé         -1.5 dBTP

La normalisation ne réécrit jamais le fichier source. Elle modifie le gain du clip et décale de la même valeur ses keyframes éventuels.

### Contrôle clipping

PISTE Studio peut produire un rapport de **risque de clipping par clip**.

Il combine :

- true peak mesuré sur la source ;
- gain maximal du clip ou de son automation.

Il ne s’agit pas d’une mesure true peak du master final. Plusieurs sources simultanées peuvent s’additionner : un rendu/mix final devra être mesuré séparément avant une livraison critique.

### Ducking VO / Dialogue

Sur un clip MUSIC, PISTE Studio peut analyser les chevauchements temporels avec :

- VO ;
- DIALOGUE.

Il propose alors une enveloppe de volume avec :

- niveau de base ;
- réduction configurable ;
- attack ;
- release.

La proposition est visible avant application.

Politique :

- validation humaine obligatoire ;
- aucun changement automatique ;
- aucun déplacement de Storyline ;
- automation totalement éditable après acceptation.

### Crossfade audio

Deux clips audio adjacents d’une même piste peuvent recevoir un crossfade contrôlé.

PISTE Studio :

- avance légèrement le second clip pour créer l’overlap ;
- ajoute fade out / fade in ;
- enregistre une relation réciproque `crossfadeWith` ;
- conserve la durée `crossfadeDuration`.

Un overlap audio arbitraire sur une même piste reste interdit. Seul un crossfade explicitement déclaré contourne la règle de collision.

### Silence

L’analyse locale peut également repérer des plages silencieuses via ffmpeg.

V0.20 ne prétend pas encore détecter automatiquement une « bonne respiration » ou une intention vocale : elle identifie des zones de silence mesurables qui pourront alimenter de futures suggestions éditoriales.

## Timeline schema v4

La timeline conserve désormais explicitement les crossfades en plus du modèle audio V0.19 :

- rôle ;
- gain dB ;
- pan ;
- fades ;
- automation ;
- Mute / Solo ;
- crossfade réciproque.

## Tesseract

Le modèle audio enrichi reste auditable dans le plan d’authoring.

Le gain statique est matérialisé dans Tesseract.

PISTE Studio ne génère toujours pas de propriétés non documentées pour automation/pan/fades : les informations restent conservées tant que le schéma Tesseract installé ne confirme pas un mécanisme natif compatible.

## Ce que V0.20 ne prétend pas encore faire

- mesure true peak du master final rendu ;
- limiteur/mastering automatique ;
- détection sémantique des respirations ;
- correction audio destructive ;
- choix automatique d’une norme de loudness universelle.

La cible LUFS est configurable car elle dépend du contexte de diffusion.

## Installation

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

L’analyse loudness nécessite ffmpeg disponible sur la machine.

Lancer :

    piste-studio-app --project /chemin/vers/PISTE_0

## Workflow audio conseillé

1. Catalogue les sources audio.
2. Sélectionne un clip et lance **Analyser loudness**.
3. Vérifie LUFS / true peak / LRA / silences.
4. Choisis ta cible et utilise **Normaliser** si nécessaire.
5. Lance **Clipping** pour repérer les clips à risque.
6. Sur MUSIC, utilise **Ducking VO** puis examine l’enveloppe proposée.
7. Entre deux clips adjacents, utilise **Crossfade suivant**.
8. Ajuste manuellement les keyframes/fades.
9. Ouvre **Audio · Master Check**, mesure le master rendu et vérifie LUFS-I / true peak.\n10. Télécharge le rapport JSON si tu dois conserver une trace de conformité.\n11. N’active le limiteur que volontairement si le contexte de livraison le justifie.

## Tests

    pip install -e '.[dev]'
    python -m playwright install chromium
    find piste_studio/ui -name '*.js' -print0 | xargs -0 -n1 node --check
    pytest -q

Voir aussi `START_HERE.md`, `ROADMAP.md`, `UX_GUIDE.md`, `README_APP.md`, `THIRD_PARTY.md` et `LICENSE_NOTE.md`.
