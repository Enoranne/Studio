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


## 30. Qualité de référence ≠ vérité

Primaire / Secondaire / Faible décrit la **qualité de la preuve visuelle**, pas la certitude de l’identité.

Une référence primaire devrait idéalement être :
- nette ;
- lisible ;
- représentative ;
- peu ambiguë ;
- correctement cadrée pour le facet visé.

Le niveau ne doit jamais être présenté comme une probabilité.

## 31. Pondérer dans le groupe, équilibrer les groupes

Plusieurs images très proches d’un même objet ne doivent pas gagner artificiellement du poids parce qu’elles sont nombreuses.

PISTE Studio doit :
1. pondérer les références selon leur qualité à l’intérieur d’un groupe ;
2. produire une représentation du groupe ;
3. comparer ensuite les groupes comme preuves indépendantes de poids égal.

La quantité ne doit pas se substituer à la diversité des preuves.

## 32. Les groupes sont des outils humains

Un groupe est créé ou choisi par l’utilisateur.

Le système peut proposer la réutilisation d’un nom existant, mais ne doit pas fusionner automatiquement deux groupes sur la seule base d’une similarité visuelle.


## 33. Absence de Canon ≠ contradiction

Le système doit distinguer trois situations :

1. preuve canonique explicite compatible ;
2. contradiction canonique explicite ;
3. information absente ou insuffisante.

La troisième situation ne doit jamais être affichée comme une erreur.

## 34. Un conflit se lit avant de se contourner

Quand un conflit Canon ou HARD LOCK exige un override :

- afficher le tag concerné ;
- afficher chaque raison ;
- afficher la source de la règle ;
- préciser qu’aucune modification n’a encore eu lieu ;
- utiliser un libellé explicite **Accepter malgré conflit**.

Un bouton générique **Accepter** ne doit pas contourner silencieusement une contradiction.

## 35. HARD LOCK contextuel

Un lock temporel n’est pertinent pour un tag sémantique que si :

- le média est effectivement utilisé dans la plage verrouillée ;
- et le lock couvre les opérations sémantiques.

Un lock de trim/reorder ne doit pas devenir artificiellement un conflit de métadonnées.

## 36. L’override ne réécrit pas le Canon

Accepter une exception signifie accepter le tag malgré le signal pour ce média.

Cela ne doit jamais :
- retirer une règle du Canon ;
- ouvrir un facet fermé ;
- modifier un HARD LOCK ;
- faire disparaître la trace du conflit.


## 37. Continuité contextuelle, pas absolue

Un plan peut être cohérent seul et problématique entre deux voisins.

Les signaux de continuité doivent donc indiquer :
- le voisin concerné ;
- le facet concerné ;
- les tags comparés ;
- la nature exacte du signal.

## 38. Métadonnée absente ≠ élément absent

Si le plan A porte `prop:fisher` et que le plan B n’a aucun tag `prop`, PISTE Studio ne peut pas conclure que le Fisher disparaît.

Il doit afficher une **preuve manquante / à vérifier**.

Une rupture explicite exige des preuves structurées incompatibles des deux côtés.

## 39. Tester avant de remplacer

La comparaison d’un rush candidat doit être non destructive.

Tester un candidat à la position d’un clip :
- conserve le clip monté ;
- conserve ses trims ;
- ne déplace rien ;
- ne crée pas de checkpoint ;
- ne modifie pas les tags.

La simulation doit pouvoir être répétée librement avant toute décision éditoriale.

## 40. Le voisinage reste une aide

Même deux tags incompatibles ne prouvent pas qu’une coupe est mauvaise.

Un changement de personnage, décor ou look peut être narrativement volontaire.

Le statut **RUPTURE POTENTIELLE** décrit un changement structuré détecté ; il ne constitue jamais une interdiction de montage.


## 41. Un titre est un objet de montage

Un titre doit rester un clip éditable de timeline, avec sa propre durée et son propre style.

Le texte affiché dans le Viewer ne doit jamais devenir une propriété implicite ou cachée du plan vidéo sous-jacent.

## 42. Position normalisée

Les coordonnées de titre doivent être indépendantes de la taille momentanée du Viewer.

PISTE Studio stocke X, Y et largeur en valeurs normalisées afin que le même overlay puisse être adapté à différents canvases sans dépendre d’une résolution d’écran locale.

## 43. Typographie portable avant typographie décorative

Une police locale introuvable sur la machine de delivery est une dépendance cachée.

V0.23.1 privilégie donc Sans / Serif / Mono, avec des stacks système explicites.

L’ajout futur de fontes spécifiques devra passer par une ressource de projet explicite, vérifiable et transportable.

## 44. Ne jamais perdre silencieusement un overlay

Si le moteur cible ne sait pas matérialiser un titre, le système doit :

- conserver la définition du titre ;
- lister clairement l’élément non matérialisé ;
- produire un warning ;
- ne jamais prétendre que l’export est visuellement complet.

## 45. Preview ≠ preuve de delivery

Le Viewer PROGRAM doit être fidèle au modèle PISTE, mais un aperçu navigateur réussi ne prouve pas qu’un moteur externe sait produire exactement le même résultat.

La chaîne de delivery doit donc vérifier séparément la matérialisation finale.


## 46. Le carton final reste un clip

Un carton final ne doit pas être une exception cachée dans l’export.

Il reste un clip visible sur TITLES, avec :
- début ;
- durée ;
- texte ;
- style ;
- fond canvas ;
- éventuelle queue finale.

## 47. Fond canvas ≠ fond du texte

Le fond d’une boîte de texte et un carton plein ne sont pas la même chose.

L’interface doit distinguer :
- `backgroundColor / backgroundOpacity` : boîte du texte ;
- `canvasBackgroundColor / canvasBackgroundOpacity` : image entière.

## 48. Noir final sans média artificiel

Une queue noire peut être décrite par le comportement temporel du carton final.

Créer automatiquement un faux fichier vidéo noir ajouterait une dépendance inutile au catalogue.

Le modèle doit donc conserver le noir final comme propriété du clip tant que le rendu final peut l’interpréter.

## 49. Une fin alignée doit réellement être alignée

Quand l’utilisateur demande un carton final automatique, sa création doit se terminer exactement au timecode final de la timeline.

Le snap ne doit pas déplacer silencieusement cette borne.

## 50. Le texte qui disparaît n’est pas un clip supprimé

Pendant `blackTailSeconds`, seul le rendu du texte est masqué.

Le clip final reste actif, son fond reste visible et son historique reste intact.


## 51. L’attache graphique n’est pas le timing du clip

Déplacer un point de connexion ne doit pas déplacer le média connecté.

Le logiciel doit distinguer :
- la relation temporelle enfant/parent ;
- la position graphique de l’attache.

Cette distinction doit être visible dans le modèle de données comme dans l’Inspector.

## 52. Une seule poignée active

Afficher toutes les lignes aide à comprendre la structure du montage.

Afficher toutes les poignées actives créerait en revanche du bruit et des erreurs de manipulation.

PISTE Studio affiche donc :
- toutes les connexions discrètement ;
- une poignée manipulable uniquement pour la sélection courante.

## 53. Traverser une coupe peut changer le parent

Une connexion graphique déplacée sur un autre plan peut exprimer une nouvelle dépendance éditoriale.

Dans ce cas :
- le clip enfant reste en place ;
- le parent change ;
- son offset temporel est recalculé ;
- le nouveau point est persisté.

Le changement doit rester undoable.

## 54. Drag et précision numérique sont complémentaires

Une manipulation graphique primaire doit disposer d’une alternative précise et accessible.

Le drag sert à l’intuition et au placement rapide.

Le champ **Point sur parent (s)** sert aux ajustements précis et aux usages sans drag.

## 55. Une connexion est soumise aux locks

Déplacer seulement une ligne graphique peut modifier la dépendance éditoriale du montage.

Cette action doit donc passer par les mêmes checkpoints et contrôles HARD/SOFT LOCK qu’un autre changement structurel.
