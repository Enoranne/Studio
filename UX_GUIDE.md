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
