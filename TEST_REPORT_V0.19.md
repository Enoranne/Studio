# PISTE Studio v0.19 — Rapport de validation audio

Date : 23 septembre 2026

## Résultat

- Python/API/UI : **62 tests passés / 62**.
- JavaScript : tous les modules UI passent `node --check`.
- Chromium réel via Playwright : succès.
- Aucune `pageerror` dans le scénario audio final.

## Audio schema v3

Validé :

- migration du gain legacy `0..1` vers `gainDb` ;
- gain `-60..+12 dB` ;
- pan `-1..+1` ;
- rôles `dialogue / vo / music / ambience / sfx` ;
- fade in / fade out ;
- volumeEnvelope ;
- validation des keyframes hors clip ;
- rejet de deux points au même instant ;
- Solo persisté au niveau de la piste.

## Preview Web Audio

Le navigateur utilise :

- MediaElementAudioSourceNode ;
- GainNode ;
- StereoPannerNode lorsque disponible ;
- bus par piste ;
- master ;
- ChannelSplitter + Analyser L/R ;
- Mute / Solo ;
- meters stéréo.

Le gain positif est donc réellement audible dans le preview.

## Timeline / UX

Le test Chromium couvre :

- présence des meters L/R ;
- sélection d’un clip VO ;
- ouverture de la section AUDIO MIX ;
- lecture du gain en dB ;
- présence des poignées de fade ;
- passage de -6 dB à +3 dB ;
- affichage de +3.0 dB sur le clip ;
- création d’un point d’automation au playhead ;
- présence du point sur la timeline ;
- activation du Solo sur la piste VO ;
- absence d’erreur JavaScript.

## Checkpoint / Undo

Les modifications audio utilisent le même historique persistant que les opérations magnétiques :

- modification de mix ;
- création/suppression de keyframe ;
- déplacement de fade ;
- déplacement de keyframe ;
- duplication audio.

## Tesseract

Le plan d’authoring V0.19, schema v3, conserve :

- gain_db ;
- pan ;
- role ;
- fade_in_ms ;
- fade_out_ms ;
- volume_envelope.

Le gain statique est actuellement matérialisé dans la propriété `volume` de la couche Audio.

PISTE Studio ne génère pas de champs Tesseract non documentés pour pan/fades/automation. Ces valeurs restent auditables dans le plan et le manifest jusqu’à ce que le schéma installé confirme un mécanisme natif compatible.

## Limites restantes

- pas encore de LUFS / true peak backend ;
- pas encore de normalisation non destructive ;
- pas encore de ducking automatique proposé ;
- pas encore de crossfade audio réel ;
- pas encore de fader de bus de piste persistant ;
- meters actuellement orientés preview navigateur, pas mesure de mastering certifiée ;
- vrai Tesseract + vrais fichiers PISTE 0 reste à tester sur la machine utilisateur.

## Avertissements CI

- Starlette/TestClient : dépréciation autour de httpx ;
- GitHub Actions : migration Node.js 20 → 24 pour certaines actions externes.

Aucun de ces avertissements ne correspond à une régression audio PISTE Studio.

## Conclusion

V0.19 fait passer l’audio d’un état de prévisualisation basique à un véritable modèle de mixage non destructif : dB, pan, fades, automation, rôles, Solo/Mute et meters sont maintenant intégrés au même workflow sécurisé que la Storyline.
