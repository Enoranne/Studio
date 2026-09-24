from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil

from .authoring import build_authoring_plan
from .metadata import fetch_media_with_metadata
from .project import PROJECT_DIRS, load_project, verify_master
from .tesseract_bridge import TesseractBridgeError, detect_tesseract
from .versioning import list_versions, slugify


READINESS_VERSION = "0.24.0"


def _check(check_id: str, status: str, message: str, **details) -> dict:
    item = {
        "id": check_id,
        "status": status,
        "message": message,
    }
    item.update(details)
    return item


def _select_timeline_version(
    root: Path,
    edit_name: str | None,
    version: str | None,
) -> tuple[dict | None, str]:
    if version and not edit_name:
        raise ValueError("--version exige aussi --name.")

    if edit_name:
        safe_name = slugify(edit_name)
        rows = list_versions(root, safe_name)
        if version:
            match = next((row for row in rows if row["version_label"] == version), None)
            if match is None:
                return None, f"Version introuvable : {safe_name}/{version}."
            if match.get("kind") != "timeline":
                return None, f"{safe_name}/{version} n'est pas une version timeline publiée."
            return match, "Version demandée sélectionnée."
        timelines = [row for row in rows if row.get("kind") == "timeline"]
        if not timelines:
            return None, f"Aucune version timeline publiée pour {safe_name}."
        return max(timelines, key=lambda row: int(row["version_number"])), "Dernière version timeline sélectionnée."

    timelines = [row for row in list_versions(root) if row.get("kind") == "timeline"]
    if not timelines:
        return None, "Aucune version timeline publiée."
    edits = sorted({str(row["edit_name"]) for row in timelines})
    if len(edits) > 1:
        return None, "Plusieurs montages publiés existent ; préciser --name pour choisir la recette."
    return max(timelines, key=lambda row: int(row["version_number"])), "Dernière version timeline du projet sélectionnée."


def build_production_readiness(
    root: Path,
    *,
    edit_name: str | None = None,
    version: str | None = None,
) -> dict:
    root = root.expanduser().resolve()
    _, project_doc = load_project(root)
    checks: list[dict] = []

    missing_dirs = [name for name in PROJECT_DIRS if not (root / name).is_dir()]
    if missing_dirs:
        checks.append(_check(
            "project_structure",
            "BLOCKED",
            "Structure projet incomplète.",
            missing_directories=missing_dirs,
        ))
    else:
        checks.append(_check(
            "project_structure",
            "PASS",
            "Structure projet PISTE Studio complète.",
            directories=list(PROJECT_DIRS),
        ))

    master = project_doc.get("project", {}).get("master")
    master_ok = True
    if master:
        master_ok, message = verify_master(root)
        checks.append(_check(
            "master",
            "PASS" if master_ok else "BLOCKED",
            message,
            configured=True,
        ))
    else:
        checks.append(_check(
            "master",
            "PASS",
            "Aucun master de référence configuré ; protection master non applicable.",
            configured=False,
        ))

    media = fetch_media_with_metadata(root)
    videos = [row for row in media if row.get("kind") == "video"]
    audio = [row for row in media if row.get("kind") == "audio"]
    missing_catalog_files = [
        str(row.get("relative_path"))
        for row in media
        if row.get("relative_path") and not (root / str(row["relative_path"])).is_file()
    ]
    if not videos:
        media_status = "BLOCKED"
        media_message = "Aucun rush vidéo catalogué."
    elif missing_catalog_files:
        media_status = "WARN"
        media_message = "Des médias catalogués ne sont plus présents sur disque."
    elif not audio:
        media_status = "WARN"
        media_message = "Rushes vidéo disponibles, mais aucune source audio séparée n'est cataloguée."
    else:
        media_status = "PASS"
        media_message = "Catalogue média prêt pour un essai de production."
    checks.append(_check(
        "media",
        media_status,
        media_message,
        video_count=len(videos),
        audio_count=len(audio),
        total_count=len(media),
        missing_files=missing_catalog_files,
    ))

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    checks.append(_check(
        "ffmpeg",
        "PASS" if ffmpeg else "BLOCKED",
        "ffmpeg disponible." if ffmpeg else "ffmpeg introuvable : rendu audio/delivery indisponible.",
        executable=ffmpeg,
    ))
    checks.append(_check(
        "ffprobe",
        "PASS" if ffprobe else "BLOCKED",
        "ffprobe disponible." if ffprobe else "ffprobe introuvable : contrôle de conformité indisponible.",
        executable=ffprobe,
    ))

    tess = detect_tesseract(root)
    tess_details = asdict(tess)
    tess_details.pop("message", None)
    checks.append(_check(
        "tesseract",
        "PASS" if tess.ready else "BLOCKED",
        tess.message,
        **tess_details,
    ))

    selected, selection_message = _select_timeline_version(root, edit_name, version)
    selected_edit = str(selected["edit_name"]) if selected else None
    selected_version = str(selected["version_label"]) if selected else None
    if selected:
        version_dir = root / "edits" / selected_edit / selected_version
        required = ["manifest.json", "brief.yaml", "timeline.json"]
        missing = [name for name in required if not (version_dir / name).is_file()]
        checks.append(_check(
            "published_version",
            "PASS" if not missing else "BLOCKED",
            selection_message if not missing else "Version publiée incomplète.",
            edit_name=selected_edit,
            version=selected_version,
            version_dir=str(version_dir),
            missing_files=missing,
        ))
    else:
        version_dir = None
        checks.append(_check(
            "published_version",
            "WARN",
            selection_message,
            edit_name=edit_name,
            version=version,
        ))

    plan = None
    plan_ok = False
    if selected and version_dir:
        try:
            plan = build_authoring_plan(root, selected_edit, selected_version)
            cuts = list(plan.get("cuts") or [])
            audio_cuts = list(plan.get("audio_cuts") or [])
            title_cuts = list(plan.get("title_cuts") or [])
            warnings = list(plan.get("warnings") or [])
            if not cuts:
                status = "BLOCKED"
                message = "Plan d'authoring valide mais sans coupe vidéo exploitable."
            elif warnings:
                status = "WARN"
                message = "Plan d'authoring construit avec avertissements."
                plan_ok = True
            else:
                status = "PASS"
                message = "Plan d'authoring construit sans avertissement."
                plan_ok = True
            checks.append(_check(
                "authoring_plan",
                status,
                message,
                video_cuts=len(cuts),
                audio_cuts=len(audio_cuts),
                title_cuts=len(title_cuts),
                media_count=len(plan.get("media") or []),
                warnings=warnings,
            ))
        except (TesseractBridgeError, ValueError, OSError) as exc:
            checks.append(_check(
                "authoring_plan",
                "BLOCKED",
                f"Plan d'authoring impossible : {exc}",
            ))
    else:
        checks.append(_check(
            "authoring_plan",
            "WARN",
            "Publier d'abord une timeline pour construire le plan d'authoring réel.",
        ))

    project_file = None
    document_schema = None
    authoring_manifest = None
    source_export = None
    if selected and version_dir:
        project_file = version_dir / f"{selected_edit}_{selected_version}.tsrct"
        document_schema = version_dir / ".tesseract-work" / "document.schema.json"
        authoring_manifest = version_dir / "authoring-manifest.json"
        source_candidates = [
            version_dir / f"{selected_edit}_{selected_version}.mp4",
            version_dir / f"{selected_edit}_{selected_version}.mov",
        ]
        source_export = next((path for path in source_candidates if path.is_file()), None)

        bootstrap_ready = project_file.is_file() and document_schema.is_file()
        checks.append(_check(
            "tesseract_bootstrap",
            "PASS" if bootstrap_ready else "WARN",
            "Bootstrap Tesseract présent." if bootstrap_ready else "Bootstrap Tesseract à exécuter pour cette version.",
            project_file=str(project_file),
            project_exists=project_file.is_file(),
            document_schema=str(document_schema),
            schema_exists=document_schema.is_file(),
        ))
        checks.append(_check(
            "authoring_execution",
            "PASS" if authoring_manifest.is_file() else "WARN",
            "Authoring Tesseract déjà exécuté." if authoring_manifest.is_file() else "Authoring Tesseract pas encore exécuté pour cette version.",
            manifest=str(authoring_manifest),
            manifest_exists=authoring_manifest.is_file(),
        ))
        checks.append(_check(
            "tesseract_render",
            "PASS" if source_export else "WARN",
            "Rendu source Tesseract disponible." if source_export else "Rendu source Tesseract pas encore produit.",
            source_export=str(source_export) if source_export else None,
        ))
    else:
        checks.extend([
            _check("tesseract_bootstrap", "WARN", "Version publiée requise avant bootstrap."),
            _check("authoring_execution", "WARN", "Version publiée requise avant authoring."),
            _check("tesseract_render", "WARN", "Version publiée requise avant rendu Tesseract."),
        ])

    project_ok = not missing_dirs
    media_ok = bool(videos)
    can_start_editing = bool(project_ok and media_ok and master_ok)
    can_bootstrap = bool(can_start_editing and selected and plan_ok and tess.ready)
    can_author = bool(
        can_bootstrap
        and project_file is not None
        and project_file.is_file()
        and document_schema is not None
        and document_schema.is_file()
    )
    can_deliver = bool(source_export and ffmpeg and ffprobe)

    if not media_ok:
        next_action = "Ajouter puis scanner au moins un rush vidéo réel."
    elif not selected:
        next_action = "Monter 30–60 s dans PISTE Studio puis publier une version timeline."
    elif not plan_ok:
        next_action = "Corriger les médias ou la timeline jusqu'à obtenir un plan d'authoring exploitable."
    elif not tess.ready:
        next_action = "Configurer Tesseract et épingler la version attendue, puis relancer le check."
    elif not (project_file and project_file.is_file() and document_schema and document_schema.is_file()):
        next_action = f'Exécuter : piste-studio tesseract bootstrap --root "{root}" --name {selected_edit} --version {selected_version} --execute'
    elif not (authoring_manifest and authoring_manifest.is_file()):
        next_action = f'Exécuter : piste-studio tesseract author --root "{root}" --name {selected_edit} --version {selected_version} --execute'
    elif not source_export:
        next_action = f'Produire le rendu source : piste-studio tesseract export --root "{root}" --name {selected_edit} --version {selected_version} --resolution 1080p --fps 24 --format mp4'
    elif not ffmpeg or not ffprobe:
        next_action = "Installer ffmpeg et ffprobe avant le Delivery Center."
    else:
        next_action = "Ouvrir le Delivery Center, lancer le préflight puis produire le premier livrable réel."

    blocked = [item for item in checks if item["status"] == "BLOCKED"]
    if can_deliver:
        pipeline_status = "READY_FOR_DELIVERY"
    elif blocked:
        pipeline_status = "BLOCKED"
    else:
        pipeline_status = "IN_PROGRESS"

    return {
        "version": READINESS_VERSION,
        "project_root": str(root),
        "project_name": project_doc.get("project", {}).get("name"),
        "selection": {
            "edit_name": selected_edit,
            "version": selected_version,
        },
        "pipeline_status": pipeline_status,
        "capabilities": {
            "can_start_editing": can_start_editing,
            "can_bootstrap": can_bootstrap,
            "can_author": can_author,
            "can_deliver": can_deliver,
        },
        "next_action": next_action,
        "checks": checks,
    }
