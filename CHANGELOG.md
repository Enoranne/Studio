# Changelog

## V0.11

- Publication de la timeline UI en version immuable `V001 / V002 / …`.
- `timeline.json` devient l’état éditorial autoritaire de la version publiée.
- Génération automatique d’un `brief.yaml` de compatibilité pour le bridge Tesseract.
- Authoring Tesseract directement depuis la timeline publiée.
- Matérialisation native des couches `Video` avec `activeRange` / `sourceRange`.
- Import et matérialisation native des couches `Audio` via `project import-asset --kind audio`.
- Gain statique audio et mute de piste transmis à Tesseract.
- Fades conservés et tracés dans le plan/manifeste ; leur animation native est reportée à la prochaine étape.
- API locale : publication, bootstrap, authoring, preview, filmstrip et export.
- UI : boutons Publier version / Authorer Tesseract / Preview / Export.
- 27 tests passent.
