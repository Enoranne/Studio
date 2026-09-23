# PISTE Studio v0.18 — Rapport de validation

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **56 tests passés / 56**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Aucune `pageerror` dans les scénarios utilisateur couverts.

## Semantic Vision validée

### Architecture
- provider vision séparé et optionnel ;
- modèle configuré par `PISTE_VISION_MODEL` ;
- dépendances vision dans l’extra `.[vision]` ;
- stockage SQLite des profils sémantiques ;
- stockage SQLite des propositions de tags ;
- embeddings normalisés.

### Confidentialité / consentement
- aucun média envoyé vers un service externe ;
- frames extraites localement via ffmpeg ;
- aucun téléchargement de modèle sans `allow_model_download=true` ;
- le diagnostic du cache ne charge pas le modèle complet ;
- absence de vision sémantique = dégradation propre, pas blocage du montage.

### Références visuelles
- les tags `character:`, `prop:`, `decor:`, `look:` servent de références déjà validées ;
- les références doivent disposer d’un profil sémantique READY ;
- chaque tag est représenté par le centroïde des embeddings de ses références ;
- meilleure référence et similarité conservées comme preuve.

### Propositions
- seuils distincts par facette ;
- état initial `PENDING` ;
- `ACCEPTED` uniquement après action utilisateur ;
- `REJECTED` mémorisé ;
- un rejet n’est pas réactivé silencieusement ;
- reset explicite possible ;
- aucune écriture automatique de tag ;
- aucune modification automatique de Storyline.

### Accept / Reject
Le test serveur confirme :

1. le rush cible ne possède pas encore `character:malo` ;
2. le moteur propose `character:malo` ;
3. la proposition reste PENDING ;
4. l’état projet ne contient toujours pas le tag ;
5. l’utilisateur accepte ;
6. la proposition devient ACCEPTED ;
7. le tag apparaît alors dans les métadonnées du rush.

## Chromium V0.18

Le scénario navigateur couvre notamment :

- deux rushes avec profils vision READY ;
- affichage de la section Semantic Vision dans l’Inspector ;
- ouverture de **Proposer continuité** ;
- trois propositions issues d’une référence validée ;
- sélection de la carte `character:malo` ;
- clic **Accepter** ;
- réhydratation du projet ;
- apparition effective de `character:malo` dans l’Inspector ;
- maintien des fonctions V0.17 : filmstrips, Prises proches, Source Selector, Markers, Focus, Overlays et Command Palette ;
- absence d’erreur JavaScript.

## Modèle réel

La CI ne télécharge ni n’exécute le vrai modèle CLIP.

Les tests de calcul sémantique utilisent :
- un provider fake déterministe pour l’interface d’analyse ;
- des embeddings synthétiques normalisés pour les propositions ;
- le même pipeline SQLite / API / validation que le provider réel.

Le premier essai avec le vrai modèle local reste donc à effectuer sur la machine utilisateur après installation de `.[vision]` et présence/téléchargement explicite du modèle.

## Limites connues

- embedding calculé sur le rush complet échantillonné, pas encore sur une zone d’image spécifique ;
- un décor dominant peut influencer un embedding de personnage ;
- une seule référence peut suffire actuellement si le seuil est dépassé ;
- pas encore de notion de qualité/poids manuel d’une référence ;
- pas encore de comparaison de continuité directement entre plan précédent et plan suivant ;
- pas encore de fenêtre IN/OUT dérivée d’événements sémantiques ;
- premier test PISTE 0 + vrai modèle vision + vrai Tesseract reste à réaliser.

## Avertissements CI

- Starlette/TestClient signale une dépréciation autour de `httpx`.
- GitHub Actions signale la migration Node.js 20 → 24 de certaines actions externes.

Ces avertissements ne correspondent pas à une régression PISTE Studio.

## Conclusion

V0.18 franchit le passage de la simple similarité visuelle à une continuité sémantique assistée par références. PISTE Studio peut désormais proposer qu’un rush corresponde probablement à un personnage, accessoire, décor ou look déjà validé, tout en conservant l’utilisateur comme seul arbitre de l’écriture des tags et du montage.
