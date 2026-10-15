# Premières corrections et validation — 15 octobre 2026

Travail disponible dans la [PR nº 8 en brouillon](https://github.com/Enoranne/Studio/pull/8), branche `codex/audit-macos-stability`. `main`, les PR nº 6 et nº 7, l’application déjà installée et les projets personnels n’ont pas été modifiés. La version reste **0.29.0** : aucun numéro de release n’a été inventé.

## Ce qui est corrigé

1. **Un projet neuf commence vide.** L’absence de timeline enregistrée initialise les cinq pistes habituelles et une Storyline magnétique vide, au lieu de conserver les clips fictifs de la démonstration. L’inspecteur indique comment cataloguer les médias. La sauvegarde et la réouverture restent vides ; une timeline déjà enregistrée conserve ses clips.
2. **Le son embarqué du rush est rétabli.** SOURCE permet d’écouter le rush original. PROGRAM respecte le bouton M de la piste VIDEO, y compris après sauvegarde et réouverture. Ce changement ne prétend pas intégrer ce son aux meters des pistes audio séparées ni au Master Check : cette limite reste à traiter.
3. **Les tests peuvent employer le Python réellement utilisé sur le Mac.** Les faux exécutables Tesseract utilisent maintenant le même interpréteur que pytest. Le contrôle de validation humaine est testé avec et sans FFmpeg/ffprobe, au lieu de dépendre de ce qui est installé sur l’ordinateur.

Le format projet, la timeline v6, les locks, les connexions, les propositions éditoriales et le moteur Tesseract externe ne sont pas modifiés.

## Résultats vérifiables

Code testé : **d9a514245529e8c0391a5b6507463d7b7e12f00d**.

| Contrôle | Résultat |
|---|---|
| Suite complète GitHub, Linux, Python 3.12, Chromium et FFmpeg | **190 réussis, aucun ignoré**, 37,52 s. [Exécution et logs](https://github.com/Enoranne/Studio/actions/runs/38738619060) |
| Python sur ce Mac, hors les deux fichiers de tests navigateur | **179 réussis, 4 ignorés**, 7,04 s. Les quatre tests nécessitent FFmpeg/ffprobe, absents localement. |
| Syntaxe de tous les fichiers JavaScript | Réussie localement et en CI. |
| Diff Git | `git diff --check` réussi. |
| Compilation macOS arm64 en CI | **Réussie** : sidecar, `.app`, `.dmg`, contrôle codesign, création projet et `/api/health` du backend embarqué. [Job Apple Silicon](https://github.com/Enoranne/Studio/actions/runs/38738618616/job/116434225203) |
| Compilation Intel | État final à consulter dans le [même workflow](https://github.com/Enoranne/Studio/actions/runs/38738618616). Ce résultat ne conditionne pas la validation du code Python/JS ci-dessus. |
| Chromium lancé depuis Codex sur le Mac | Bloqué avant chargement de l’application : `MachPortRendezvousServer … Permission denied (1100)`. Le résultat navigateur utilisé est donc celui de la CI, pas une fausse validation locale. |
| Backend de l’app installée lancé depuis le sandbox | PyInstaller bloqué par `semctl: Operation not permitted`. Cela ne démontre pas un échec depuis Finder. |
| Installation Finder / WKWebView / notarisation / GH5 / export Tesseract réel | **Non validés**. Aucun nouveau DMG n’est présenté comme prêt à installer. |

Un avertissement Starlette/HTTPX est présent ; il ne fait pas échouer les tests. Les dépendances restent à verrouiller dans une itération dédiée.

Les 190 tests incluent les contrôles existants de timebase, trim/reflow/connexions, locks, checkpoints, publication, consentement de transcription, propositions éditoriales et livraison. Un test réussi utilisant un faux CLI demeure une preuve de logique d’intégration, pas une preuve de rendu Tesseract réel.

## Reproduire les validations

Dans un environnement de développement avec Python ≥ 3.10, Node, FFmpeg/ffprobe et Chromium utilisables :

```sh
python -m pip install -e '.[dev]'
python -m playwright install chromium
python -m pytest -q
```

Le test `tests/test_ui_mac_workflow.py` crée automatiquement, dans un dossier temporaire, un WAV sinusoïdal de 3 secondes et une vidéo WebM bleue avec ce son. Il scanne le fichier, charge une timeline, vérifie que SOURCE avance et que le signal audio décodé n’est pas nul, vérifie le mute PROGRAM, enregistre, recharge et contrôle que le rush est inchangé. Il ne télécharge aucun média personnel et n’envoie rien au cloud.

```sh
python -m pytest -q tests/test_ui_mac_workflow.py
```

Les limites sont explicites : le test crée la timeline côté Python et utilise le scan existant. Il ne valide pas un import depuis un sélecteur Finder, le glisser/trim sur média GH5, l’écoute sur haut-parleurs ou l’export du vrai moteur. La vidéo synthétique sert de recette reproductible, pas de film de démonstration livré.

## Prochaine étape produit

La première des trois itérations de `AUDIT_INITIAL_CODEX.md` reste à achever : reprendre le correctif de packaging existant dans la PR nº 7, rendre les textes lisibles et protéger les modifications non enregistrées. Puis traiter l’import durable/proxies et enfin la livraison réelle. Il faudra vérifier ces étapes sur l’application Mac, avec un dossier d’essai distinct, avant d’y ouvrir un projet de film important.

La PR nº 8 est prête à être relue ; elle n’est pas fusionnée. L’application 0.29.1 actuellement installée n’inclut pas automatiquement ces corrections de code.
