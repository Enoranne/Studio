from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import os
import shutil
import subprocess

from .config import read_yaml
from .project import load_project, verify_master
from .tesseract_bridge import (
    TesseractBridgeError,
    _ready_context,
    _latest_version_dir,
    _env_for_config,
)


VIDEO_EXT = {".mp4", ".mov", ".m4v"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
SUPPORTED_CANVASES = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "3:4": (810, 1080),
    "4:3": (1350, 1080),
}


@dataclass(frozen=True)
class PlannedClip:
    beat: str
    media_id: int | None
    relative_path: str
    timeline_start_ms: int
    requested_duration_ms: int
    source_start_ms: int
    volume: float
    fit: str


@dataclass(frozen=True)
class PlannedAudio:
    clip_id: str
    track: str
    media_id: int
    relative_path: str
    timeline_start_ms: int
    requested_duration_ms: int
    source_start_ms: int
    source_duration_ms: int
    volume: float
    fade_in_ms: int
    fade_out_ms: int


def _stable_json_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(data.encode("utf-8")).hexdigest()


def _brief_path(root: Path, edit_name: str, version: str) -> Path:
    version_dir = _latest_version_dir(root, edit_name, version)
    path = version_dir / "brief.yaml"
    if not path.exists():
        raise TesseractBridgeError(f"Brief introuvable : {path}")
    return path


def _brief_duration_seconds(brief: dict) -> float:
    deliverable = brief.get("deliverable", {})
    raw = deliverable.get("duration_seconds", brief.get("duration_seconds", 0))
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise TesseractBridgeError("Durée du brief invalide.") from exc
    if value <= 0:
        raise TesseractBridgeError("Durée du brief absente ou <= 0.")
    return value


def _brief_aspect_ratio(brief: dict) -> str:
    deliverable = brief.get("deliverable", {})
    ratio = str(deliverable.get("aspect_ratio") or brief.get("aspect_ratio") or "16:9")
    if ratio not in SUPPORTED_CANVASES:
        raise TesseractBridgeError(
            f"Ratio {ratio!r} non supporté par le mapping V0.04. "
            f"Valeurs: {', '.join(SUPPORTED_CANVASES)}"
        )
    return ratio


def _candidate_id_map(brief: dict) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for item in brief.get("candidate_pool", []):
        rel = item.get("relative_path") or item.get("path")
        if rel:
            out[str(rel)] = item.get("id")
    return out


def _safe_media_path(root: Path, relative_path: str) -> Path:
    p = (root / relative_path).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError as exc:
        raise TesseractBridgeError(f"Média hors projet refusé : {p}") from exc
    if not p.exists() or not p.is_file():
        raise TesseractBridgeError(f"Média du brief introuvable : {p}")
    if p.suffix.lower() not in VIDEO_EXT:
        raise TesseractBridgeError(
            f"V0.04 authoring accepte MP4/MOV/M4V pour les couches vidéo : {p.name}"
        )
    return p



def _safe_audio_path(root: Path, relative_path: str) -> Path:
    p = (root / relative_path).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError as exc:
        raise TesseractBridgeError(f"Média audio hors projet refusé : {p}") from exc
    if not p.exists() or not p.is_file():
        raise TesseractBridgeError(f"Média audio introuvable : {p}")
    if p.suffix.lower() not in AUDIO_EXT:
        raise TesseractBridgeError(
            f"Tesseract v0.2.0 accepte WAV/MP3/M4A/AAC/FLAC/OGG pour les couches audio : {p.name}"
        )
    return p


def _build_timeline_authoring_plan(root: Path, edit_name: str, version: str, brief: dict, timeline_path: Path) -> dict:
    from .metadata import fetch_media_with_metadata

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    duration_seconds = float(timeline.get("duration_seconds") or _brief_duration_seconds(brief))
    ratio = _brief_aspect_ratio(brief)
    rows = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    tracks = {str(t["id"]): t for t in timeline.get("tracks", [])}
    cuts: list[PlannedClip] = []
    audio_cuts: list[PlannedAudio] = []
    warnings: list[str] = []
    media_map: dict[tuple[str, int], dict] = {}

    for clip in timeline.get("clips", []):
        track_id = str(clip.get("track") or "")
        track = tracks.get(track_id, {})
        kind = str(track.get("kind") or track_id).lower()
        start_ms = round(float(clip.get("start", 0)) * 1000)
        duration_ms = round(float(clip.get("duration", 0)) * 1000)
        source_start_ms = round(float(clip.get("sourceStart", 0) or 0) * 1000)
        if duration_ms <= 0:
            warnings.append(f"{clip.get('id','?')}: durée vide, ignorée.")
            continue

        if clip.get("mediaDbId") is not None:
            media_id = int(clip["mediaDbId"])
            item = rows.get(media_id)
            if not item or item.get("kind") != "video":
                warnings.append(f"{clip.get('id','?')}: vidéo catalogue introuvable, ignorée.")
                continue
            rel = str(item["relative_path"])
            _safe_media_path(root, rel)
            media_map[("video", media_id)] = {
                "kind": "video",
                "media_id": media_id,
                "relative_path": rel,
                "absolute_path": str((root / rel).resolve()),
                "asset_id": _asset_id(media_id, rel),
            }
            cuts.append(PlannedClip(
                beat=str(clip.get("label") or clip.get("id") or "clip"),
                media_id=media_id,
                relative_path=rel,
                timeline_start_ms=start_ms,
                requested_duration_ms=duration_ms,
                source_start_ms=source_start_ms,
                volume=0.0 if bool(track.get("muted")) else float(clip.get("videoVolume", 1.0) or 1.0),
                fit=str(clip.get("fit") or "contain"),
            ))
            continue

        if clip.get("audioDbId") is not None:
            media_id = int(clip["audioDbId"])
            item = rows.get(media_id)
            if not item or item.get("kind") != "audio":
                warnings.append(f"{clip.get('id','?')}: audio catalogue introuvable, ignoré.")
                continue
            rel = str(item["relative_path"])
            _safe_audio_path(root, rel)
            source_duration = item.get("duration_seconds")
            if source_duration is None:
                warnings.append(f"{clip.get('id','?')}: durée audio inconnue, couche ignorée.")
                continue
            source_duration_ms = round(float(source_duration) * 1000)
            media_map[("audio", media_id)] = {
                "kind": "audio",
                "media_id": media_id,
                "relative_path": rel,
                "absolute_path": str((root / rel).resolve()),
                "asset_id": _asset_id(media_id, rel),
            }
            fade_in_ms = round(float(clip.get("fadeIn", 0) or 0) * 1000)
            fade_out_ms = round(float(clip.get("fadeOut", 0) or 0) * 1000)
            if fade_in_ms or fade_out_ms:
                warnings.append(
                    f"{clip.get('id','?')}: fades conservés dans le plan mais pas encore matérialisés en V0.11; "
                    "le gain statique est authoré."
                )
            audio_cuts.append(PlannedAudio(
                clip_id=str(clip.get("id") or f"audio-{media_id}"),
                track=track_id,
                media_id=media_id,
                relative_path=rel,
                timeline_start_ms=start_ms,
                requested_duration_ms=duration_ms,
                source_start_ms=source_start_ms,
                source_duration_ms=source_duration_ms,
                volume=0.0 if bool(track.get("muted")) else float(clip.get("gain", 1.0) if clip.get("gain") is not None else 1.0),
                fade_in_ms=fade_in_ms,
                fade_out_ms=fade_out_ms,
            ))
            continue

        if kind in {"titles", "title"}:
            warnings.append(f"{clip.get('id','?')}: titre conservé dans timeline.json; authoring texte prévu après V0.11.")

    width, height = SUPPORTED_CANVASES[ratio]
    return {
        "schema_version": 2,
        "engine": "piste-studio-authoring-v0.11",
        "source": "timeline.json",
        "edit_name": edit_name,
        "version": version,
        "brief_sha256": _stable_json_hash(brief),
        "timeline_sha256": _stable_json_hash(timeline),
        "deliverable": {"duration_seconds": duration_seconds, "aspect_ratio": ratio, "canvas": {"width": width, "height": height}},
        "policy": {
            "timeline_is_authoritative": True,
            "preserve_embedded_video_audio": True,
            "static_audio_gain_supported": True,
            "audio_fades_deferred": True,
            "append_footage_behind_existing_overlays": True,
            "work_on_copy_then_atomic_replace": True,
            "never_modify_source_media": True,
            "never_modify_master": True,
            "require_installed_document_schema": True,
        },
        "media": list(media_map.values()),
        "cuts": [asdict(c) for c in cuts],
        "audio_cuts": [asdict(c) for c in audio_cuts],
        "warnings": warnings,
    }


def build_authoring_plan(root: Path, edit_name: str, version: str) -> dict:
    root = root.expanduser().resolve()
    load_project(root)
    project_doc = read_yaml(root / "project.yaml")
    if project_doc.get("project", {}).get("master") is not None:
        ok, msg = verify_master(root)
        if not ok:
            raise TesseractBridgeError(f"Master non conforme : {msg}")

    brief = read_yaml(_brief_path(root, edit_name, version))
    version_dir = _latest_version_dir(root, edit_name, version)
    timeline_path = version_dir / "timeline.json"
    if timeline_path.exists():
        return _build_timeline_authoring_plan(root, edit_name, version, brief, timeline_path)
    duration_seconds = _brief_duration_seconds(brief)
    ratio = _brief_aspect_ratio(brief)
    candidate_ids = _candidate_id_map(brief)

    cuts: list[PlannedClip] = []
    warnings: list[str] = []
    for beat in brief.get("suggested_beats", []):
        rel = beat.get("primary_media_path")
        if not rel:
            warnings.append(f"Beat {beat.get('name', '?')}: aucun média assigné.")
            continue
        _safe_media_path(root, str(rel))
        start_s = float(beat.get("start", 0))
        end_s = float(beat.get("end", start_s))
        if end_s <= start_s:
            warnings.append(f"Beat {beat.get('name', '?')}: plage de temps vide, ignorée.")
            continue
        source_start_s = float(beat.get("source_start_seconds", 0) or 0)
        if source_start_s < 0:
            raise TesseractBridgeError(f"source_start_seconds négatif pour {beat.get('name', '?')}")
        cuts.append(
            PlannedClip(
                beat=str(beat.get("name") or "beat"),
                media_id=candidate_ids.get(str(rel)),
                relative_path=str(rel),
                timeline_start_ms=round(start_s * 1000),
                requested_duration_ms=round((end_s - start_s) * 1000),
                source_start_ms=round(source_start_s * 1000),
                volume=float(beat.get("volume", 1.0)),
                fit=str(beat.get("fit") or "contain"),
            )
        )

    if not cuts:
        warnings.append("Aucune coupe vidéo exploitable dans le brief.")

    unique_media: list[dict] = []
    seen: set[str] = set()
    for cut in cuts:
        if cut.relative_path in seen:
            continue
        seen.add(cut.relative_path)
        unique_media.append(
            {
                "kind": "video",
                "media_id": cut.media_id,
                "relative_path": cut.relative_path,
                "absolute_path": str(_safe_media_path(root, cut.relative_path)),
                "asset_id": _asset_id(cut.media_id, cut.relative_path),
            }
        )

    width, height = SUPPORTED_CANVASES[ratio]
    plan = {
        "schema_version": 1,
        "engine": "piste-studio-authoring-v0.04",
        "edit_name": edit_name,
        "version": version,
        "brief_sha256": _stable_json_hash(brief),
        "deliverable": {
            "duration_seconds": duration_seconds,
            "aspect_ratio": ratio,
            "canvas": {"width": width, "height": height},
        },
        "policy": {
            "source_selection_default": "start_of_clip_unless_beat_override",
            "preserve_embedded_audio": True,
            "append_footage_behind_existing_overlays": True,
            "work_on_copy_then_atomic_replace": True,
            "never_modify_source_media": True,
            "never_modify_master": True,
            "require_installed_document_schema": True,
        },
        "media": unique_media,
        "cuts": [asdict(c) for c in cuts],
        "audio_cuts": [],
        "warnings": warnings,
    }
    return plan


def save_authoring_plan(root: Path, edit_name: str, version: str) -> Path:
    root = root.expanduser().resolve()
    plan = build_authoring_plan(root, edit_name, version)
    version_dir = _latest_version_dir(root, edit_name, version)
    path = version_dir / "authoring-plan.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _asset_id(media_id: int | None, relative_path: str) -> str:
    stem = f"ps-media-{media_id}" if media_id is not None else "ps-media"
    digest = sha256(relative_path.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{digest}"


def _parse_json_output(stdout: str, what: str) -> dict:
    text = (stdout or "").strip()
    if not text:
        raise TesseractBridgeError(f"{what}: réponse JSON vide.")
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise TesseractBridgeError(f"{what}: impossible de lire la réponse JSON du CLI.")


def _load_document_schema(version_dir: Path, *, require_audio: bool = False) -> dict:
    path = version_dir / ".tesseract-work" / "document.schema.json"
    if not path.exists():
        raise TesseractBridgeError(
            "Schéma document absent : exécutez d'abord `tesseract bootstrap --execute`."
        )
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TesseractBridgeError(f"Schéma document invalide : {exc}") from exc
    probe = json.dumps(schema, ensure_ascii=False)
    required_tokens = ["Video", "activeRange", "sourceRange", "sourceIntrinsicDuration"]
    if require_audio:
        required_tokens.append("Audio")
    missing = [token for token in required_tokens if token not in probe]
    if missing:
        raise TesseractBridgeError(
            "Le schéma Tesseract installé ne confirme pas les champs vidéo requis : "
            + ", ".join(missing)
        )
    return schema


def _composition_from_document(doc: dict) -> dict:
    if isinstance(doc.get("composition"), dict):
        return doc["composition"]
    compositions = doc.get("compositions")
    if isinstance(compositions, list) and len(compositions) == 1 and isinstance(compositions[0], dict):
        return compositions[0]
    nested = doc.get("document")
    if isinstance(nested, dict) and isinstance(nested.get("composition"), dict):
        return nested["composition"]
    raise TesseractBridgeError("Structure du JSON checkout inconnue : composition unique introuvable.")


def _duration_owner(doc: dict) -> dict:
    if "duration" in doc:
        return doc
    nested = doc.get("document")
    if isinstance(nested, dict) and "duration" in nested:
        return nested
    raise TesseractBridgeError("Champ document.duration introuvable dans le checkout.")


def _set_canvas_from_existing_shape(doc: dict, composition: dict, width: int, height: int) -> str:
    if "width" in doc and "height" in doc:
        doc["width"], doc["height"] = width, height
        return "document.width/height"
    canvas = doc.get("canvas")
    if isinstance(canvas, dict) and "width" in canvas and "height" in canvas:
        canvas["width"], canvas["height"] = width, height
        return "document.canvas.width/height"
    if "width" in composition and "height" in composition:
        composition["width"], composition["height"] = width, height
        return "composition.width/height"
    nested = doc.get("document")
    if isinstance(nested, dict):
        if "width" in nested and "height" in nested:
            nested["width"], nested["height"] = width, height
            return "document.document.width/height"
        canvas = nested.get("canvas")
        if isinstance(canvas, dict) and "width" in canvas and "height" in canvas:
            canvas["width"], canvas["height"] = width, height
            return "document.document.canvas.width/height"
    raise TesseractBridgeError(
        "Impossible d'identifier les champs canvas dans le checkout. "
        "PISTE Studio refuse d'inventer leur forme."
    )


def _collect_integer_ids(value: Any, out: set[int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"id", "layerId", "groupLayerId"} and isinstance(item, int):
                out.add(item)
            _collect_integer_ids(item, out)
    elif isinstance(value, list):
        for item in value:
            _collect_integer_ids(item, out)


def _next_layer_id(doc: dict) -> int:
    ids: set[int] = set()
    _collect_integer_ids(doc, ids)
    return (max(ids) + 1) if ids else 1


def _import_video(
    *, cli: str, project: Path, media: dict, cwd: Path, env: dict[str, str]
) -> dict:
    argv = [
        cli,
        "project",
        "import-video",
        "--project",
        str(project),
        "--file",
        media["absolute_path"],
        "--asset-id",
        media["asset_id"],
    ]
    cp = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, env=env, check=False)
    if cp.returncode != 0:
        raise TesseractBridgeError(
            f"Import vidéo Tesseract échoué ({Path(media['relative_path']).name}) : "
            f"{cp.stderr.strip() or cp.stdout.strip()}"
        )
    result = _parse_json_output(cp.stdout, "import-video")
    for required in ("assetId", "durationMs", "width", "height"):
        if required not in result:
            raise TesseractBridgeError(f"import-video: champ attendu absent : {required}")
    if str(result["assetId"]) != media["asset_id"]:
        raise TesseractBridgeError(
            f"import-video: assetId inattendu {result['assetId']!r}, attendu {media['asset_id']!r}."
        )
    return result


def _import_audio(*, cli: str, project: Path, media: dict, cwd: Path, env: dict[str, str]) -> dict:
    argv = [
        cli, "project", "import-asset", "--project", str(project),
        "--file", media["absolute_path"], "--asset-id", media["asset_id"], "--kind", "audio",
    ]
    cp = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, env=env, check=False)
    if cp.returncode != 0:
        raise TesseractBridgeError(
            f"Import audio Tesseract échoué ({Path(media['relative_path']).name}) : "
            f"{cp.stderr.strip() or cp.stdout.strip()}"
        )
    return {"assetId": media["asset_id"], "stdout": cp.stdout.strip()}


def execute_authoring(
    root: Path,
    edit_name: str,
    version: str,
    *,
    dry_run: bool = True,
) -> dict:
    root = root.expanduser().resolve()
    plan = build_authoring_plan(root, edit_name, version)
    version_dir = _latest_version_dir(root, edit_name, version)
    authoring_plan_path = version_dir / "authoring-plan.json"
    authoring_plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if dry_run:
        return {"dry_run": True, "plan": plan, "manifest": None}

    cfg, status, bridge_plan = _ready_context(root, edit_name, version)
    project_file = Path(bridge_plan["paths"]["project"])
    if not project_file.exists():
        raise TesseractBridgeError("Projet Tesseract absent : exécutez d'abord le bootstrap réel.")
    manifest_path = version_dir / "authoring-manifest.json"
    if manifest_path.exists():
        raise TesseractBridgeError(
            "Cette version possède déjà un authoring-manifest.json. "
            "Créez une nouvelle version/PATCH plutôt que de reconstruire silencieusement."
        )

    _load_document_schema(version_dir, require_audio=bool(plan.get("audio_cuts")))
    work = version_dir / ".tesseract-work"
    work.mkdir(parents=True, exist_ok=True)
    working_project = work / "authoring-working.tsrct"
    editable_path = work / "editable.authoring.json"
    inspect_after = work / "project.after-authoring.json"
    for disposable in (working_project, editable_path, inspect_after):
        disposable.unlink(missing_ok=True)
    shutil.copy2(project_file, working_project)

    env = _env_for_config(cfg)
    imported: dict[str, dict] = {}
    try:
        for media in plan["media"]:
            if media.get("kind", "video") == "audio":
                imported[media["relative_path"]] = _import_audio(
                    cli=status.executable, project=working_project, media=media, cwd=version_dir, env=env
                )
            else:
                imported[media["relative_path"]] = _import_video(
                    cli=status.executable, project=working_project, media=media, cwd=version_dir, env=env
                )

        cp = subprocess.run(
            [status.executable, "project", "checkout", "--project", str(working_project), "--output", str(editable_path)],
            cwd=str(version_dir), capture_output=True, text=True, env=env, check=False,
        )
        if cp.returncode != 0:
            raise TesseractBridgeError(f"Checkout Tesseract échoué : {cp.stderr.strip() or cp.stdout.strip()}")
        if not editable_path.exists():
            raise TesseractBridgeError("Checkout Tesseract n'a pas produit editable.authoring.json.")
        try:
            doc = json.loads(editable_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TesseractBridgeError(f"JSON checkout invalide : {exc}") from exc

        composition = _composition_from_document(doc)
        layers = composition.get("layers")
        if not isinstance(layers, list):
            raise TesseractBridgeError("composition.layers absent ou non-tableau dans le checkout.")
        duration_owner = _duration_owner(doc)
        duration_owner["duration"] = float(plan["deliverable"]["duration_seconds"])
        canvas = plan["deliverable"]["canvas"]
        canvas_field = _set_canvas_from_existing_shape(doc, composition, canvas["width"], canvas["height"])

        next_id = _next_layer_id(doc)
        materialized: list[dict] = []
        warnings = list(plan.get("warnings", []))
        for cut in plan["cuts"]:
            meta = imported.get(cut["relative_path"])
            if not meta:
                warnings.append(f"{cut['beat']}: média non importé, couche ignorée.")
                continue
            source_duration = int(meta["durationMs"])
            available = source_duration - int(cut["source_start_ms"])
            if available <= 0:
                warnings.append(
                    f"{cut['beat']}: source_start_ms={cut['source_start_ms']} au-delà de la durée source {source_duration}ms."
                )
                continue
            clip_duration = min(int(cut["requested_duration_ms"]), available)
            if clip_duration < int(cut["requested_duration_ms"]):
                warnings.append(
                    f"{cut['beat']}: coupe raccourcie de {cut['requested_duration_ms']}ms à {clip_duration}ms "
                    "car la source est plus courte."
                )
            layer = {
                "type": "Video",
                "id": next_id,
                "name": f"PS:{cut['beat']}:{Path(cut['relative_path']).name}",
                "activeRange": {"start": int(cut["timeline_start_ms"]), "duration": clip_duration},
                "sourceRange": {"start": int(cut["source_start_ms"]), "duration": clip_duration},
                "sourceIntrinsicDuration": source_duration,
                "volume": float(cut["volume"]),
                "transform": {
                    "anchorPoint": [0, 0],
                    "position": [0, 0],
                    "scale": [100, 100],
                    "rotation": 0,
                    "opacity": 100,
                },
                "source": {"assetId": str(meta["assetId"]), "fit": cut["fit"]},
            }
            layers.append(layer)
            materialized.append(
                {
                    "layer_id": next_id,
                    "beat": cut["beat"],
                    "relative_path": cut["relative_path"],
                    "asset_id": str(meta["assetId"]),
                    "source_duration_ms": source_duration,
                    "active_range": layer["activeRange"],
                    "source_range": layer["sourceRange"],
                }
            )
            next_id += 1

        materialized_audio: list[dict] = []
        for cut in plan.get("audio_cuts", []):
            meta = imported.get(cut["relative_path"])
            if not meta:
                warnings.append(f"{cut['clip_id']}: média audio non importé, couche ignorée.")
                continue
            source_duration = int(cut["source_duration_ms"])
            available = source_duration - int(cut["source_start_ms"])
            if available <= 0:
                warnings.append(f"{cut['clip_id']}: source audio hors durée, couche ignorée.")
                continue
            clip_duration = min(int(cut["requested_duration_ms"]), available)
            layer = {
                "type": "Audio",
                "id": next_id,
                "name": f"PS:{cut['track']}:{Path(cut['relative_path']).name}",
                "activeRange": {"start": int(cut["timeline_start_ms"]), "duration": clip_duration},
                "sourceRange": {"start": int(cut["source_start_ms"]), "duration": clip_duration},
                "sourceIntrinsicDuration": source_duration,
                "source": {"assetId": str(meta["assetId"])},
                "volume": float(cut["volume"]),
                "captionsEnabled": False,
            }
            layers.append(layer)
            materialized_audio.append({
                "layer_id": next_id,
                "clip_id": cut["clip_id"],
                "track": cut["track"],
                "relative_path": cut["relative_path"],
                "asset_id": str(meta["assetId"]),
                "source_duration_ms": source_duration,
                "active_range": layer["activeRange"],
                "source_range": layer["sourceRange"],
                "volume": layer["volume"],
                "fade_in_ms": int(cut.get("fade_in_ms", 0)),
                "fade_out_ms": int(cut.get("fade_out_ms", 0)),
            })
            next_id += 1

        if not materialized and not materialized_audio:
            raise TesseractBridgeError("Aucune couche vidéo ou audio n'a pu être matérialisée ; commit annulé.")

        editable_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        cp = subprocess.run(
            [status.executable, "project", "commit", "--project", str(working_project), "--file", str(editable_path)],
            cwd=str(version_dir), capture_output=True, text=True, env=env, check=False,
        )
        if cp.returncode != 0:
            raise TesseractBridgeError(f"Commit Tesseract refusé : {cp.stderr.strip() or cp.stdout.strip()}")

        cp = subprocess.run(
            [status.executable, "project", "inspect", "--project", str(working_project), "--pretty"],
            cwd=str(version_dir), capture_output=True, text=True, env=env, check=False,
        )
        if cp.returncode != 0:
            raise TesseractBridgeError(f"Inspection post-authoring échouée : {cp.stderr.strip() or cp.stdout.strip()}")
        inspect_after.write_text(cp.stdout, encoding="utf-8")

        os.replace(working_project, project_file)
        project_sha = _sha256_file(project_file)
        manifest = {
            "schema_version": 1,
            "engine": str(plan.get("engine") or "piste-studio-authoring-v0.11"),
            "status": "AUTHORED_TESSERACT",
            "detected_tesseract_version": status.detected_version,
            "brief_sha256": plan["brief_sha256"],
            "document_schema_sha256": _sha256_file(work / "document.schema.json"),
            "project_sha256": project_sha,
            "canvas_field": canvas_field,
            "canvas": canvas,
            "duration_seconds": plan["deliverable"]["duration_seconds"],
            "imported_assets": imported,
            "layers": materialized,
            "audio_layers": materialized_audio,
            "warnings": warnings,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"dry_run": False, "plan": plan, "manifest": manifest}
    except Exception:
        working_project.unlink(missing_ok=True)
        raise


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
