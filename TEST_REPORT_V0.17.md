# PISTE Studio v0.17 — Rapport de validation

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **51 tests passés / 51**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Aucune `pageerror` dans le scénario utilisateur couvert.

## Media Intelligence validée

### Analyse locale
- détection de ffmpeg / ffprobe ;
- état explicite `TOOLS_UNAVAILABLE` lorsque les outils manquent ;
- probe technique ;
- persistance de l’analyse dans SQLite ;
- mise à jour d’une durée média manquante depuis le probe ;
- réutilisation d’une analyse existante ;
- régénération d’un filmstrip cache manquant.

### Filmstrips
- génération prévue dans `cache/filmstrips/` ;
- cache exclu de Git ;
- URL exposée uniquement si le fichier existe ;
- Browser utilisant le filmstrip cache au repos ;
- retour au skimming vidéo au survol.

### Empreinte visuelle
- échantillonnage multi-images en niveaux de gris ;
- average-hash par image ;
- comparaison Hamming normalisée ;
- similarité exacte testée à 100 % ;
- séparation nette d’une prise visuellement différente.

### Prises proches
- combinaison pondérée empreinte visuelle / nom / durée ;
- fallback nom/durée sans empreinte ;
- raisons du calcul exposées ;
- tiroir **Prises proches** testé dans Chromium.

### Continuité
- tags structurés `character:`, `prop:`, `decor:`, `look:` ;
- raisons de continuité remontées dans le Source Selector ;
- proximité visuelle utilisée avec un poids modéré ;
- validation humaine toujours requise ;
- remplacement automatique toujours désactivé.

## Scénario Chromium V0.17

Le test navigateur couvre notamment :

- chargement de deux rushes analysés ;
- présence des badges ANALYSÉ ;
- présence des filmstrips backend ;
- navigation/workspaces ;
- Focus Mode ;
- Viewer Overlays ;
- Command Palette ;
- création d’un Marker ;
- sélection d’un rush ;
- Inspector Editorial ;
- Inspector Media Intelligence ;
- ouverture de **Prises proches** ;
- affichage d’une prise similaire ;
- ouverture du Source Selector ;
- prévisualisation d’une alternative ;
- absence d’erreur JavaScript.

## Limites explicites

V0.17 **ne reconnaît pas sémantiquement** un personnage, un accessoire, un décor, une émotion ou une action.

L’empreinte visuelle mesure une proximité globale d’images. Les notions de personnage/accessoire/décor proviennent actuellement de tags structurés validés dans le catalogue.

Une future couche de vision sémantique devra conserver :
- traitement local privilégié ;
- consentement explicite si service externe ;
- propositions de tags révisables ;
- aucune modification automatique de la Storyline.

## Dépendances

`ffmpeg` et `ffprobe` sont optionnels et détectés au runtime. Ils ne sont pas installés automatiquement par le package Python.

## Avertissements CI

- Starlette/TestClient signale une dépréciation autour de `httpx`.
- Les actions GitHub remontent un avertissement Node.js 20 provenant des actions externes utilisées.

Ces avertissements ne correspondent pas à une régression fonctionnelle de PISTE Studio.

## Conclusion

V0.17 transforme le catalogue média en source de signaux éditoriaux locaux mesurables : filmstrips, caractéristiques techniques, empreintes perceptuelles et prises proches. Elle améliore le Source Selector sans prétendre encore comprendre sémantiquement les images.
