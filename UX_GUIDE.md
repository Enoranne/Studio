# PISTE Studio — UX Principles

## 1. Le contenu avant l’interface

Le Viewer, les filmstrips et la Storyline doivent attirer l’œil avant les métadonnées. Une information technique ne reste visible en permanence que si elle sert une décision immédiate.

## 2. Progressive disclosure

Ne pas ajouter un panneau permanent pour chaque nouvelle fonction.

- informations fréquentes : visibles ;
- réglages contextuels : Inspector ;
- actions secondaires : menu contextuel ou Command Palette ;
- diagnostic technique : vues projet / statuts.

## 3. Trois intentions, trois workspaces

### ASSEMBLE
Regarder, skimmer, choisir, définir IN/OUT.

### EDIT
Monter, trimmer, connecter et régler.

### REVIEW
Regarder le film, contrôler les décisions et les locks.

Chaque workspace doit modifier réellement l’espace disponible, pas seulement changer un libellé.

## 4. Viewer-first

SOURCE sert à comprendre un média.
PROGRAM sert à juger le montage.

Le Viewer doit rester le centre visuel de l’application. Les overlays sont optionnels et configurables.

## 5. Storyline lisible

Le récit vidéo est la structure principale.
TITLES / VO / MUSIC / SFX sont des éléments connectés.

Les connexions doivent être compréhensibles visuellement avant d’être compréhensibles via les données.

## 6. Couleurs sémantiques

- ambre : sélection, Storyline, décision éditoriale ;
- vert : validé / safe / favorite ;
- rouge : lock / erreur / reject ;
- violet : title ;
- bleu/cyan : audio ;
- gris : structure générale.

La couleur ne doit pas servir de décoration.

## 7. Réduire le chrome

Éviter :
- bordures sur chaque élément ;
- badges opaques inutiles ;
- labels redondants ;
- gros boutons pour actions secondaires.

Préférer :
- contraste de surface ;
- espace ;
- typographie ;
- apparition au survol ;
- icônes sobres.

## 8. Focus Mode

Le panneau sous la souris peut devenir l’espace de travail principal avec `~`.
Échap restaure la disposition.

Le Focus Mode doit fonctionner pour :
- Viewer ;
- Browser ;
- Timeline ;
- Inspector.

## 9. Command Palette

`Ctrl/Cmd+K` donne accès aux commandes sans ajouter de boutons permanents.

Une fonction fréquente devrait idéalement être accessible par :
- interaction directe ;
- raccourci ;
- Command Palette.

## 10. Tests UX

Une évolution UI n’est pas considérée stable uniquement parce que son JavaScript est syntaxiquement valide.

La CI doit vérifier dans Chromium :
- chargement sans pageerror ;
- navigation ;
- workspaces ;
- Focus Mode ;
- popovers critiques ;
- Command Palette ;
- interactions de montage au fur et à mesure de leur couverture.

## Référence de direction

PISTE Studio peut reprendre des patterns éprouvés des NLE professionnels sans recopier leur habillage. L’objectif est une workstation de montage sobre, centrée sur l’intention, le canon et la sécurité éditoriale — pas un clone de Final Cut Pro, Premiere ou Resolve.


## 11. Intelligence éditoriale explicable

Une suggestion ne doit jamais se présenter comme une décision objective.

Le Source Selector doit :
- afficher ses signaux de classement ;
- préserver les contraintes Canon / Safe / Spoiler ;
- permettre la prévisualisation avant action ;
- ne jamais remplacer automatiquement un plan ;
- distinguer clairement recommandation, sélection humaine et modification effective de la Storyline.

Une future analyse visuelle ou IA devra respecter les mêmes règles.


## 12. Intelligence média : ne pas surinterpréter

Une empreinte perceptuelle indique une proximité d’images, pas une compréhension sémantique.

L’interface doit distinguer :
- **proximité visuelle** : calcul local sur images échantillonnées ;
- **continuité structurée** : tags validés dans le catalogue ;
- **reconnaissance sémantique** : future analyse par modèle visuel.

Ne jamais transformer une forte similarité perceptuelle en affirmation du type « même personnage », « même accessoire » ou « même décor » sans preuve sémantique correspondante.


## 13. Référence visuelle avant reconnaissance

PISTE Studio ne doit pas déduire l’identité d’un personnage ou d’un accessoire à partir de son nom seul.

Une proposition sémantique spécifique doit être reliée à :
- un ou plusieurs rushes de référence déjà tagués ;
- un profil visuel compatible ;
- un score et un seuil visibles ;
- une validation humaine explicite.

Le libellé `character:malo` signifie donc : « suffisamment proche des références validées Malo pour proposer ce tag », pas « identité prouvée par le modèle ».

## 14. Consentement de calcul

Les traitements média restent locaux par défaut.

Un téléchargement de modèle peut être proposé, mais :
- jamais silencieusement ;
- uniquement après action explicite ;
- sans upload des médias ;
- avec une alternative de fonctionnement sans vision sémantique.


## 15. Audio : afficher la forme du geste

L’audio ne doit pas être réduit à des champs numériques dans l’Inspector.

Les actions fréquentes doivent avoir une représentation directe dans la timeline :
- waveform pour la matière sonore ;
- poignée pour le fade ;
- ligne et points pour l’automation ;
- dB visibles sur le clip ;
- Mute/Solo au niveau de la piste ;
- meters au niveau du Viewer.

L’Inspector reste l’endroit des valeurs précises ; la timeline reste l’endroit du geste.

## 16. dB comme unité utilisateur

Le gain utilisateur s’exprime en dB.

Le pourcentage linéaire n’est conservé que comme compatibilité technique interne avec les anciens projets ou moteurs.

Une interface de mixage ne doit pas afficher « 55 % » lorsqu’elle signifie réellement environ -5 dB.

## 17. Automation réversible

Une automation audio est une décision éditoriale.

Elle doit :
- être visible ;
- rester modifiable ;
- être sauvegardée dans la timeline ;
- bénéficier de checkpoint/Undo ;
- ne jamais être aplatie silencieusement lors de l’authoring.


## 18. Loudness : mesurer avant de corriger

L’interface doit distinguer quatre choses :
- mesure source ;
- objectif utilisateur ;
- proposition de correction ;
- résultat estimé.

Ne jamais présenter un gain proposé comme un traitement déjà effectué.

## 19. True peak : source vs master

Un true peak mesuré sur un fichier source est une mesure réelle.

Un true peak calculé comme `source + gain du clip` est une estimation de risque.

Le mix de plusieurs sources peut créer un pic supérieur. L’UI doit toujours distinguer ces deux niveaux de confiance.

## 20. Ducking : proposition visible

Le ducking doit rester une automation de volume ordinaire :
- keyframes visibles ;
- attack/release compréhensibles ;
- réduction indiquée en dB ;
- modification manuelle possible ;
- aucune application silencieuse.

## 21. Crossfade : overlap intentionnel

Une collision accidentelle et un crossfade ne sont pas la même chose.

PISTE Studio continue de refuser les overlaps même piste, sauf lorsque deux clips déclarent explicitement une relation de crossfade réciproque.


## 22. Master : mesurer le mix rendu

Une estimation par clip ne doit jamais être présentée comme un true peak master.

Le contrôle de livraison doit :
- rendre réellement les sources audibles ;
- respecter Mute/Solo, gain, automation, fades, pan et crossfades ;
- mesurer ensuite le fichier obtenu ;
- distinguer clairement mesure source, estimation par clip et mesure master.

## 23. Presets de livraison : repères, pas vérité universelle

Une cible de loudness dépend du contexte de diffusion.

L’interface peut proposer des presets pratiques, mais doit :
- les présenter comme références configurables ;
- afficher leurs valeurs ;
- laisser l’utilisateur modifier cible, ceiling et tolérance ;
- éviter toute formulation laissant croire à une norme unique valable partout.

## 24. Limiteur : action explicite

Un limiteur modifie le signal.

Il ne doit donc jamais être activé silencieusement dans un Master Check.

L’option reste désactivée par défaut et son état doit apparaître dans le rapport exporté.


## 25. Rupture visuelle ≠ décision de coupe

Un changement de scène détecté par un algorithme est un **signal**, pas une intention de montage.

Une fenêtre issue d’une rupture visuelle doit :
- être présentée comme candidate ;
- montrer explicitement ses bornes ;
- indiquer la méthode de détection ;
- rester prévisualisable avant adoption ;
- ne jamais modifier automatiquement la Storyline.

## 26. Sensibilité compréhensible

Un seuil technique brut ne doit pas être le seul contrôle exposé.

L’interface propose des niveaux Faible / Normale / Forte, tout en affichant le seuil ffmpeg correspondant pour l’auditabilité.

Augmenter la sensibilité doit être décrit comme une augmentation possible du nombre de ruptures détectées, pas comme une augmentation de la « qualité » de l’analyse.


## 27. Une référence n’est pas un tag global

Une zone choisie comme `prop:fisher` signifie :

« cette image ou cette zone est une référence validée du Fisher ».

Elle ne signifie pas :

« tout le rush représente le Fisher ».

L’interface et le modèle de données doivent donc distinguer référence ciblée et tag global du média.

## 28. Cibler avant de comparer

Quand l’identité visuelle porte sur un détail localisé — visage, accessoire, élément de décor — comparer un crop ciblé est préférable à moyenner tout le rush.

La référence doit conserver :
- son timecode ;
- sa zone ROI ;
- son média d’origine ;
- son tag explicite ;
- sa méthode/modèle d’embedding.

Une proposition doit rester auditable jusqu’à cette preuve précise.

## 29. Pas d’auto-référence

Une référence extraite d’un média ne doit jamais être utilisée pour proposer le même tag à ce média lui-même.

Sans cette règle, la similarité serait circulaire et donnerait une fausse impression de confiance.
