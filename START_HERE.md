# Démarrage rapide — PISTE Studio v0.25

## 1. Application desktop macOS — parcours recommandé

Pour un build desktop V0.25 :

1. ouvre `PISTE Studio.app` ou installe l’application depuis le DMG de ton architecture ;
2. choisis **Ouvrir un projet…** pour un projet existant ;
3. ou choisis **Nouveau projet…**, donne un nom puis sélectionne le dossier qui contiendra le projet ;
4. PISTE Studio crée la structure et démarre le moteur local automatiquement ;
5. aucun Terminal ni installation Python manuelle n’est nécessaire pour ce parcours.

Tesseract reste volontairement séparé. Le panneau **Readiness** indique s’il est détecté et quelle action effectuer avant l’authoring/rendu.

Pour les builds de test non notarisés, macOS peut demander une autorisation explicite selon les réglages Gatekeeper. La diffusion publique propre passe par le workflow Developer ID/notarisation documenté dans `PACKAGING.md`.

## 2. Installation développeur / CLI

```bash
python -m venv .venv
```

macOS / Linux :

```bash
source .venv/bin/activate
pip install -e .
```

Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
pip install -e .
```

## 3. Lancer en mode développeur

Projet de démonstration :

```bash
piste-studio-app --project demo/PISTE_0_DEMO
```

Projet réel :

```bash
piste-studio-app --project /chemin/vers/PISTE_0
```

L’application s’ouvre sur `http://127.0.0.1:8765/`.

## 4. Workflow UI

1. Place les vidéos dans `rushes/` et les sons dans `audio/`.
2. Clique **Scanner projet**.
3. Monte dans la timeline et clique **Enregistrer**.
4. Clique **Publier version** : la timeline est figée en `edits/<edit>/V001/timeline.json`.
5. Si le CLI Tesseract configuré est prêt, clique **Authorer Tesseract**.
6. Utilise **Preview** puis **Export**.

Le `.tsrct` est créé dans le dossier de version, jamais dans `master/`.


## Storyline magnétique

Dans EDIT, déplacer un plan STORY réordonne la Storyline et recale l’aval. Trimmer un plan produit un ripple. Les titres, VO, musiques et SFX peuvent être reliés à un plan parent depuis l’Inspector ; ils suivent alors automatiquement son déplacement.


## Sécurité d’édition V0.14

Avant chaque reorder/ripple validé, PISTE Studio crée un checkpoint persistant. Utilisez **Undo** ou **Ctrl/Cmd+Z** pour restaurer l’état précédent. Les tests CI ouvrent désormais l’interface dans Chromium et vérifient les clics de navigation en plus des tests Python et du contrôle syntaxique JavaScript.


## UX V0.15

- **ASSEMBLE** : sélectionner et préparer les sources avec un Browser dominant.
- **EDIT** : montage principal avec Viewer, Inspector et Storyline.
- **REVIEW** : lecture avec Viewer dominant et Index.
- **Focus Mode** : survoler un panneau puis utiliser `~`, ou cliquer sur `⛶`.
- **Command Palette** : `Ctrl/Cmd+K`.
- **Overlays Viewer** : choisir l’affichage du timecode, du mix et de la plage IN/OUT.
- **Échap** : fermer un menu ou quitter le Focus.


## Editorial Intelligence V0.16

1. Dans SOURCE, règle IN / OUT.
2. Utilise **F** pour enregistrer la plage comme Favorite ou **X** pour Reject.
3. Utilise **M** dans la timeline pour poser une Note, Décision, Beat ou Vigilance.
4. Depuis l’Inspector, clique **Alternatives** pour ouvrir l’Editorial Source Selector.
5. Lis les raisons proposées et prévisualise les candidats.
6. **Charger la plage** ne modifie que la sélection SOURCE ; la Storyline n’est jamais remplacée automatiquement.


## Media Intelligence V0.17

1. Place les rushes dans `rushes/`.
2. Clique **Scanner**.
3. Clique **Analyser** pour lancer ffprobe/ffmpeg localement et générer les filmstrips.
4. Sélectionne un rush : l’Inspector affiche ses caractéristiques techniques.
5. Clique **Prises proches** pour comparer les autres rushes.
6. Utilise des tags structurés comme `character:malo`, `prop:fisher`, `decor:salon` ou `look:warm-tungsten` pour enrichir les contrôles de continuité.
7. **Alternatives** utilise ces signaux avec Favorite/Reject, Canon, Safe et Spoiler.

Si ffmpeg/ffprobe n’est pas présent, le reste de PISTE Studio continue de fonctionner et l’analyse affiche explicitement que les outils sont indisponibles.


## Semantic Vision V0.18

1. Commence par valider quelques tags de référence sur des rushes fiables :
   - `character:malo`
   - `prop:fisher`
   - `decor:salon`
   - `look:warm-tungsten`
2. Installe la vision locale si souhaité : `pip install -e '.[vision]'`.
3. Sélectionne un rush puis clique **Analyser vision**.
4. Si le modèle n’est pas déjà en cache, PISTE Studio demande une autorisation explicite avant téléchargement.
5. Clique **Proposer continuité**.
6. Examine le score, le seuil et les rushes de référence.
7. **Accepter** écrit le tag ; **Rejeter** mémorise le refus.
8. Aucune proposition ne modifie la Storyline.

La vision locale fonctionne comme une aide à la continuité, pas comme une décision automatique d’identité.


## Audio Mixing V0.19

1. Sélectionne ou dépose un clip audio dans la timeline.
2. Dans **AUDIO MIX**, règle :
   - rôle ;
   - gain dB ;
   - pan ;
   - fade in / fade out.
3. Utilise **+ Point au playhead** pour créer une automation de volume.
4. Déplace directement les points de volume ou les poignées de fade sur le clip.
5. Utilise **M** pour Mute et **S** pour Solo sur les pistes audio.
6. Contrôle les meters L/R dans le Viewer.
7. Enregistre la timeline : le format V3 conserve gain, pan, rôles, fades et automation.
8. À l’authoring Tesseract, le gain statique est appliqué ; les autres paramètres restent préservés tant que le schéma Tesseract installé ne confirme pas leur automation native.


## Audio Intelligence V0.20

1. Sélectionne un clip audio.
2. Clique **Analyser loudness** pour mesurer LUFS, true peak, LRA et silences.
3. Choisis une cible LUFS et un ceiling TP.
4. Clique **Normaliser** puis examine le delta proposé avant **Accepter**.
5. Utilise **Clipping** pour voir les clips dont le true peak estimé dépasse le plafond choisi.
6. Sur un clip MUSIC, utilise **Ducking VO** pour générer une enveloppe selon les chevauchements VO/DIALOGUE.
7. Pour deux clips audio adjacents de même piste, utilise **Crossfade suivant**.
8. Ajuste ensuite manuellement les fades et keyframes si nécessaire.
9. Avant une livraison finale, mesure le master rendu : le rapport V0.20 reste une estimation par clip.


## Audio Delivery V0.21

1. Termine d’abord le mix avec les outils V0.19 / V0.20.
2. Ouvre la Command Palette avec **Ctrl/Cmd+K**.
3. Lance **Audio · Master Check**.
4. Choisis un preset de référence ou règle directement :
   - cible LUFS ;
   - ceiling true peak ;
   - tolérance loudness.
5. Laisse **Limiteur master** décoché pour mesurer le mix tel qu’il est réellement.
6. Clique **Mesurer le master**.
7. Lis séparément le LUFS-I master, le true peak et le statut PASS/WARN.
8. Télécharge le rapport JSON si tu dois conserver une preuve de contrôle.
9. N’active le limiteur que volontairement si tu veux comparer un rendu limité.

Les presets sont des repères configurables et ne remplacent jamais les spécifications du diffuseur ou du festival concerné.


## Editorial Vision V0.22.1

1. Sélectionne un rush vidéo dans le Browser.
2. Dans **MEDIA INTELLIGENCE**, clique **Fenêtres IN/OUT**.
3. Commence avec la sensibilité **Normale**.
4. Examine les segments proposés entre les ruptures visuelles.
5. Utilise **Prévisualiser** pour regarder une fenêtre sans l’adopter.
6. Utilise **Charger IN/OUT** pour préparer cette plage dans SOURCE.
7. Ajuste ensuite manuellement IN/OUT si nécessaire avant d’ajouter le plan.

Une sensibilité plus forte propose potentiellement davantage de ruptures. PISTE Studio ne modifie jamais la Storyline à partir de cette détection.


## Références ciblées V0.22.2

1. Sélectionne un rush et affiche le frame utile dans SOURCE.
2. Ouvre **SEMANTIC VISION → Référence ciblée**.
3. Choisis le facet et la valeur, par exemple `prop:fisher`.
4. Clique **Utiliser le frame affiché** si le timecode est correct.
5. Garde **Frame entier** si toute l’image est pertinente.
6. Pour isoler un personnage ou un accessoire, choisis **Zone de l’image** et règle X / Y / largeur / hauteur.
7. Clique **Créer la référence**.
8. Vérifie le crop affiché dans la liste.
9. Lance ensuite **Proposer continuité** sur un autre rush.

Créer une référence ciblée n’ajoute pas son tag au média source. Elle sert uniquement de preuve visuelle explicite pour les comparaisons futures.


## Groupes et qualité V0.22.3

Quand plusieurs références décrivent la même identité visuelle :

1. donne-leur le même **Groupe**, par exemple `Fisher principal` ;
2. marque la meilleure vue nette et représentative **Primaire** ;
3. garde les vues utiles mais moins fortes en **Secondaire** ;
4. classe les vues partielles, floues ou très contextuelles en **Faible** ;
5. vérifie le résumé du groupe dans le gestionnaire.

Repère de poids :

- Primaire = 1,5× ;
- Secondaire = 1,0× ;
- Faible = 0,5×.

Ces poids ne sont pas des scores de vérité. Ils indiquent uniquement quelle référence doit peser davantage **à l’intérieur d’un groupe**.

Les groupes sont ensuite équilibrés entre eux : multiplier les captures similaires d’un même plan ne doit pas écraser une autre preuve visuelle indépendante.


## Conflits Canon V0.22.4

Quand **Proposer continuité** affiche un tag :

- **CANON ALIGNÉ** : le Canon contient une preuve explicite compatible ;
- **NON VÉRIFIÉ** : aucune règle explicite ne tranche ;
- **CONFLIT CANON** : règle interdite ou facet fermé ;
- **HARD LOCK** : le média est utilisé dans une zone verrouillée applicable à la sémantique ;
- **À REVOIR** : SOFT LOCK.

Ne transforme pas un facet en facet fermé simplement pour réduire les propositions : un facet fermé signifie que sa liste autorisée est réellement exhaustive.

Pour un conflit, lis la source affichée avant d’utiliser **Accepter malgré conflit**. Cette action ne modifie pas le Canon ; elle documente uniquement une décision humaine consciente d’accepter le tag malgré le signal.


## Continuité de voisinage V0.22.5

1. Clique un clip vidéo de la STORYLINE.
2. Dans l’Inspector, ouvre **Continuité de voisinage → Analyser voisins**.
3. Lis le triptyque **Précédent / Plan / Suivant**.
4. Examine les signaux par `character / prop / decor / look`.
5. **RUPTURE POTENTIELLE** signifie que des tags explicites se contredisent.
6. **À VÉRIFIER** signifie seulement qu’une preuve structurée manque.
7. Pour comparer une autre prise, choisis-la dans **Tester un autre rush à cette position**.
8. Clique **Tester ce candidat**.

Le candidat n’est pas inséré dans le montage. Le résultat sert uniquement à éclairer une décision de remplacement ultérieure.


## Titres / overlays V0.23.1

1. Place le playhead à l’endroit voulu.
2. Clique **+ Titre**.
3. Sélectionne le clip de la piste TITLES.
4. Dans **TITRE / OVERLAY**, saisis le texte.
5. Choisis Centre, Lower third, Haut ou Personnalisé.
6. Ajuste taille, graisse, alignement, couleur et fond.
7. En mode Personnalisé, règle Position X / Y.
8. Observe le résultat directement dans PROGRAM.
9. Clique **Appliquer PATCH**.
10. Enregistre la timeline.

Les familles Sans / Serif / Mono sont intentionnellement génériques : elles améliorent la portabilité entre Viewer, machine locale et futurs exports.


## Carton final V0.23.2

1. Clique **+ Carton final** dans la timeline.
2. Le carton se place automatiquement à la fin du montage.
3. Remplace le texte par le titre/crédit souhaité.
4. Ajuste la typographie comme pour un titre normal.
5. Choisis la couleur du **Fond canvas**.
6. Garde 100 % pour un vrai carton plein.
7. Règle **Noir / fond seul final (s)** pour réserver une fin sans texte.
8. Clique **Appliquer PATCH**.
9. Lis la fin dans PROGRAM pour vérifier le rythme.
10. Enregistre la timeline.

La queue finale fait partie du même clip : le texte disparaît, mais le fond reste présent jusqu’au dernier frame.


## Point de connexion graphique V0.23.3

1. Sélectionne un titre, une VO, une musique ou un SFX connecté.
2. Repère la ligne qui descend vers la Storyline.
3. La poignée active apparaît sur le plan parent.
4. Glisse cette poignée horizontalement pour déplacer **l’attache seulement**.
5. Le clip connecté reste à son timecode actuel.
6. Si la poignée traverse une coupe, le parent peut changer.
7. Pour une valeur précise, utilise **CONNEXION STORY → Point sur parent (s)**.
8. Enregistre ensuite la timeline si le résultat te convient.

Le badge du clip indique le plan parent et la position locale du point, par exemple :

`↳ Plan B · +1.0s`

Un déplacement bloqué par un lock est refusé avant mutation. `Ctrl/Cmd+Z` restaure le parent et le point précédents.


## Delivery festival / social V0.23.4

1. Enregistre ton montage.
2. Publie une version `Vxxx`.
3. Authorise-la avec Tesseract si nécessaire.
4. Clique **Export**.
5. Choisis le livrable :
   - Festival ProRes ;
   - Festival H.264 ;
   - Online 1080p ;
   - Social vertical 9:16 ;
   - Social carré 1:1.
6. Lis les quatre blocs du préflight :
   - Version publiée ;
   - Audio master ;
   - Titres / overlays ;
   - Cadrage.
7. Pour un export social, choisis :
   - **FIT** pour conserver toute l’image ;
   - **FILL** pour remplir le cadre en acceptant un crop.
8. Si tu choisis FILL, coche explicitement **Autoriser le crop centré**.
9. Vérifie l’estimation de crop affichée.
10. Lance l’export.
11. Télécharge le livrable et son rapport JSON.

Un statut WARN n’est pas masqué. Le bouton devient **Exporter avec avertissements**.

Un FILL sans consentement reste **BLOCKED**.

Si un festival fournit une fiche technique précise, utilise-la comme référence prioritaire plutôt que les cibles intégrées.


## Presets de delivery V0.23.5

### Créer un preset personnalisé

1. Publie une version.
2. Clique **Export**.
3. Choisis le profil le plus proche de ton besoin.
4. Clique **Dupliquer**.
5. Modifie la copie :
   - nom ;
   - dimensions ;
   - FPS ;
   - codec ;
   - bitrates si H.264 ;
   - source Tesseract ;
   - cadrage par défaut.
6. Clique **Enregistrer le preset**.
7. Vérifie le préflight.
8. Exporte normalement.

Les profils intégrés restent intacts.

### Utiliser un preset par défaut

Dans le Delivery Center :

**Définir par défaut**

Le preset sera sélectionné automatiquement aux prochaines ouvertures du projet.

Si tu supprimes le preset par défaut, PISTE revient à **Online · H.264 · 1080p**.

### Réutiliser dans un autre projet

Dans le projet source :

**Exporter JSON**

Dans le projet cible :

**Importer JSON**

PISTE crée une nouvelle copie locale avec un ID sans collision.

### Important

Un preset contenant **FILL** ne mémorise jamais ton consentement au crop.

À chaque export FILL, tu dois toujours cocher explicitement :

**Autoriser explicitement le crop centré**

Le preset mémorise une configuration technique, pas une autorisation éditoriale permanente.


## Production Readiness V0.24.0

Avant la première recette sur un vrai projet, lance :

```bash
piste-studio readiness --root "/chemin/vers/PISTE_0"
```

Si plusieurs montages existent, ajoute `--name`. Pour cibler une version précise, ajoute aussi `--version Vxxx`.

Le rapport indique :

- si le projet peut commencer à être monté ;
- si Tesseract peut être bootstrapé ;
- si l'authoring peut être exécuté ;
- si un rendu source peut partir vers le Delivery Center ;
- la **prochaine action exacte** à effectuer.

La recette complète du premier essai réel est décrite dans `PRODUCTION_TEST_V0.24.md`.
