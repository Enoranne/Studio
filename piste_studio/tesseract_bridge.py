from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import json
import os
import re
import shutil
import subprocess

from .config import read_yaml, write_yaml
from .project import load_project, verify_master


class TesseractBridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class TesseractConfig:
    cli_path: str | None = None
    expected_version: str | None = None
    telemetry: bool = False


@dataclass(frozen=True)
class TesseractStatus:
    found: bool
    executable: str | None
    detected_version: str | None
    expected_version: str | None
    version_ok: bool
    ready: bool
    message: str


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: list[str]
    cwd: str
    mutates: bool
    description: str


def config_path(root: Path) -> Path:
    return root / "tesseract.yaml"


def load_tesseract_config(root: Path) -> TesseractConfig:
    path = config_path(root)
    if not path.exists():
        return TesseractConfig()
    doc = read_yaml(path) or {}
    t = doc.get("tesseract", {})
    return TesseractConfig(
        cli_path=t.get("cli_path"),
        expected_version=str(t["expected_version"]) if t.get("expected_version") is not None else None,
        telemetry=bool(t.get("telemetry", False)),
    )


def save_tesseract_config(root: Path, *, cli_path: str | None, expected_version: str | None, telemetry: bool = False) -> Path:
    load_project(root)
    path = config_path(root)
    doc = {
        "schema_version": 1,
        "tesseract": {
            "cli_path": cli_path,
            "expected_version": expected_version,
            "telemetry": bool(telemetry),
            "policy": {
                "require_version_pin": True,
                "never_modify_master": True,
                "preserve_stable_ids": True,
                "use_atomic_apply": True,
            },
        },
    }
    write_yaml(path, doc)
    return path


def _candidate_cli_paths(config: TesseractConfig) -> Iterable[Path]:
    if config.cli_path:
        yield Path(config.cli_path).expanduser()

    home = Path.home()
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            yield Path(local) / "Tesseract" / "bin" / "tsrct.cmd"
    elif sys_platform() == "darwin":
        yield home / "Library" / "Application Support" / "Tesseract" / "bin" / "tsrct"
    else:
        data_home = Path(os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share")))
        yield data_home / "Tesseract" / "bin" / "tsrct"

    on_path = shutil.which("tsrct")
    if on_path:
        yield Path(on_path)


def sys_platform() -> str:
    import sys
    return sys.platform


def _parse_version(text: str) -> str | None:
    m = re.search(r"(?:^|\s)v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)", text.strip())
    return m.group(1) if m else None


def detect_tesseract(root: Path) -> TesseractStatus:
    load_project(root)
    cfg = load_tesseract_config(root)

    expected = cfg.expected_version
    seen: set[str] = set()
    for candidate in _candidate_cli_paths(cfg):
        p = candidate.expanduser()
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if not p.exists() or not p.is_file():
            continue
        try:
            cp = subprocess.run(
                [str(p), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return TesseractStatus(True, str(p), None, expected, False, False, f"CLI trouvé mais inexécutable : {exc}")
        output = (cp.stdout or "") + "\n" + (cp.stderr or "")
        version = _parse_version(output)
        if cp.returncode != 0:
            return TesseractStatus(True, str(p), version, expected, False, False, f"CLI trouvé mais --version échoue (code {cp.returncode}).")
        if not version:
            return TesseractStatus(True, str(p), None, expected, False, False, "CLI trouvé mais version illisible.")
        if not expected:
            return TesseractStatus(True, str(p), version, None, False, False, "CLI détecté, mais aucune version attendue n'est épinglée dans tesseract.yaml.")
        ok = version == expected
        return TesseractStatus(
            True,
            str(p),
            version,
            expected,
            ok,
            ok,
            "Tesseract prêt." if ok else f"Version incompatible : détectée {version}, attendue {expected}.",
        )

    return TesseractStatus(False, None, None, expected, False, False, "CLI Tesseract introuvable. Configurez son chemin ou installez-le séparément.")


def _latest_version_dir(root: Path, edit_name: str, version: str) -> Path:
    path = root / "edits" / edit_name / version
    if not path.exists():
        raise TesseractBridgeError(f"Version PISTE Studio introuvable : {edit_name}/{version}")
    return path


def _safe_media_paths_from_brief(root: Path, brief: dict) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for item in brief.get("candidate_pool", []):
        rel = item.get("relative_path") or item.get("path")
        if not rel:
            continue
        p = (root / rel).resolve()
        try:
            p.relative_to(root.resolve())
        except ValueError as exc:
            raise TesseractBridgeError(f"Média hors projet refusé : {p}") from exc
        if p.exists() and p.is_file() and p not in seen:
            seen.add(p)
            paths.append(p)
    return paths


def build_execution_plan(root: Path, edit_name: str, version: str) -> dict:
    root = root.expanduser().resolve()
    load_project(root)
    ok, msg = verify_master(root)
    project_doc = read_yaml(root / "project.yaml")
    if project_doc.get("project", {}).get("master") is not None and not ok:
        raise TesseractBridgeError(f"Master non conforme : {msg}")

    cfg = load_tesseract_config(root)
    status = detect_tesseract(root)
    version_dir = _latest_version_dir(root, edit_name, version)
    brief_path = version_dir / "brief.yaml"
    if not brief_path.exists():
        raise TesseractBridgeError(f"Brief introuvable : {brief_path}")
    brief = read_yaml(brief_path)

    work = version_dir / ".tesseract-work"
    previews = version_dir / "Previews"
    project_file = version_dir / f"{edit_name}_{version}.tsrct"
    output_file = version_dir / f"{edit_name}_{version}.mp4"
    cli = status.executable or cfg.cli_path or "tsrct"

    commands: list[CommandSpec] = []
    commands.append(CommandSpec("version", [cli, "--version"], str(version_dir), False, "Vérifier la version du CLI."))
    commands.append(CommandSpec("project_help", [cli, "project", "--help"], str(version_dir), False, "Vérifier les commandes projet exposées."))
    commands.append(CommandSpec("export_help", [cli, "export", "--help"], str(version_dir), False, "Vérifier les options d'export exposées."))
    commands.append(CommandSpec("create", [cli, "project", "create", "--project", str(project_file)], str(version_dir), True, "Créer un document Tesseract vide dans la version, jamais dans master/."))
    commands.append(CommandSpec("inspect", [cli, "project", "inspect", "--project", str(project_file), "--pretty"], str(version_dir), False, "Inspecter le projet et obtenir les IDs stables."))
    commands.append(CommandSpec("schema_actions", [cli, "project", "schema"], str(version_dir), False, "Récupérer le schéma des actions réellement supportées."))
    commands.append(CommandSpec("schema_document", [cli, "project", "schema", "--document"], str(version_dir), False, "Récupérer le schéma du document réellement supporté."))

    for media_path in _safe_media_paths_from_brief(root, brief):
        if media_path.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}:
            commands.append(CommandSpec(
                "import_video",
                [cli, "project", "import-video", "--project", str(project_file), "--file", str(media_path)],
                str(version_dir),
                True,
                f"Importer la vidéo {media_path.name} dans le .tsrct.",
            ))

    deliverable = brief.get("deliverable", {}) if isinstance(brief.get("deliverable"), dict) else {}
    brief_duration = float(deliverable.get("duration_seconds", brief.get("duration_seconds", 30)))
    commands.extend([
        CommandSpec("preview", [cli, "preview", "--project", str(project_file), "--time", "1", "--output", str(work / "layout.png")], str(version_dir), False, "Générer une frame de contrôle."),
        CommandSpec("filmstrip", [cli, "filmstrip", "--project", str(project_file), "--start-ms", "0", "--duration-ms", str(int(brief_duration * 1000)), "--interval-ms", "500", "--output", str(previews / "Filmstrip.png")], str(version_dir), False, "Générer une planche de contrôle du montage."),
        CommandSpec("export", [cli, "export", "--project", str(project_file), "--fps", "24", "--resolution", "1080p", "--output", str(output_file)], str(version_dir), True, "Exporter le rendu de travail."),
    ])

    return {
        "schema_version": 1,
        "bridge": "PISTE Studio Tesseract Bridge V0.04",
        "edit_name": edit_name,
        "version": version,
        "tesseract_status": asdict(status),
        "policy": {
            "dry_run_default": True,
            "requires_ready_cli_for_execution": True,
            "master_is_never_an_output": True,
            "authoring_requires_installed_schema": True,
            "no_manual_tsrct_archive_edit": True,
        },
        "paths": {
            "version_dir": str(version_dir),
            "project": str(project_file),
            "work": str(work),
            "previews": str(previews),
            "output": str(output_file),
        },
        "commands": [asdict(c) for c in commands],
    }


def save_execution_plan(root: Path, edit_name: str, version: str) -> Path:
    plan = build_execution_plan(root, edit_name, version)
    version_dir = _latest_version_dir(root.expanduser().resolve(), edit_name, version)
    path = version_dir / "tesseract-plan.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _env_for_config(cfg: TesseractConfig) -> dict[str, str]:
    env = os.environ.copy()
    if not cfg.telemetry:
        env.setdefault("TESSERACT_TELEMETRY", "0")
    return env


def execute_bootstrap(root: Path, edit_name: str, version: str, *, dry_run: bool = True) -> dict:
    root = root.expanduser().resolve()
    plan = build_execution_plan(root, edit_name, version)
    status = TesseractStatus(**plan["tesseract_status"])
    if dry_run:
        save_execution_plan(root, edit_name, version)
        return {"dry_run": True, "executed": [], "plan": plan}
    if not status.ready:
        raise TesseractBridgeError(status.message)

    cfg = load_tesseract_config(root)
    paths = plan["paths"]
    Path(paths["work"]).mkdir(parents=True, exist_ok=True)
    Path(paths["previews"]).mkdir(parents=True, exist_ok=True)

    allowed_names = {"version", "project_help", "export_help", "create", "inspect", "schema_actions", "schema_document"}
    executed = []
    for cmd in plan["commands"]:
        if cmd["name"] not in allowed_names:
            continue
        if cmd["name"] == "create" and Path(paths["project"]).exists():
            raise TesseractBridgeError(f"Refus d'écraser un projet Tesseract existant : {paths['project']}")
        cp = subprocess.run(cmd["argv"], cwd=cmd["cwd"], capture_output=True, text=True, env=_env_for_config(cfg), check=False)
        record = {
            "name": cmd["name"],
            "returncode": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
        }
        executed.append(record)
        if cp.returncode != 0:
            raise TesseractBridgeError(f"Commande Tesseract échouée ({cmd['name']}): {cp.stderr.strip() or cp.stdout.strip()}")
        if cmd["name"] == "inspect":
            (Path(paths["work"]) / "project.json").write_text(cp.stdout, encoding="utf-8")
        elif cmd["name"] == "schema_actions":
            (Path(paths["work"]) / "project-action.schema.json").write_text(cp.stdout, encoding="utf-8")
        elif cmd["name"] == "schema_document":
            (Path(paths["work"]) / "document.schema.json").write_text(cp.stdout, encoding="utf-8")

    save_execution_plan(root, edit_name, version)
    return {"dry_run": False, "executed": executed, "plan": plan}


def _ready_context(root: Path, edit_name: str, version: str) -> tuple[TesseractConfig, TesseractStatus, dict]:
    root = root.expanduser().resolve()
    load_project(root)
    status = detect_tesseract(root)
    if not status.ready:
        raise TesseractBridgeError(status.message)
    cfg = load_tesseract_config(root)
    plan = build_execution_plan(root, edit_name, version)
    return cfg, status, plan


def execute_preview(root: Path, edit_name: str, version: str, *, time_seconds: float = 1.0, output_name: str = "Preview.png") -> Path:
    cfg, status, plan = _ready_context(root, edit_name, version)
    project_file = Path(plan["paths"]["project"])
    if not project_file.exists():
        raise TesseractBridgeError("Projet Tesseract absent : exécutez d'abord le bootstrap.")
    out = Path(plan["paths"]["previews"]) / output_name
    out.parent.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(
        [status.executable, "preview", "--project", str(project_file), "--time", str(time_seconds), "--output", str(out)],
        cwd=plan["paths"]["version_dir"], capture_output=True, text=True, env=_env_for_config(cfg), check=False,
    )
    if cp.returncode != 0:
        raise TesseractBridgeError(f"Preview Tesseract échouée : {cp.stderr.strip() or cp.stdout.strip()}")
    if not out.exists():
        raise TesseractBridgeError(f"Preview attendue non produite : {out}")
    return out


def execute_filmstrip(root: Path, edit_name: str, version: str, *, start_ms: int = 0, duration_ms: int = 3000, interval_ms: int = 250, output_name: str = "Filmstrip.png") -> Path:
    cfg, status, plan = _ready_context(root, edit_name, version)
    project_file = Path(plan["paths"]["project"])
    if not project_file.exists():
        raise TesseractBridgeError("Projet Tesseract absent : exécutez d'abord le bootstrap.")
    out = Path(plan["paths"]["previews"]) / output_name
    out.parent.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(
        [status.executable, "filmstrip", "--project", str(project_file), "--start-ms", str(start_ms),
         "--duration-ms", str(duration_ms), "--interval-ms", str(interval_ms), "--output", str(out)],
        cwd=plan["paths"]["version_dir"], capture_output=True, text=True, env=_env_for_config(cfg), check=False,
    )
    if cp.returncode != 0:
        raise TesseractBridgeError(f"Filmstrip Tesseract échoué : {cp.stderr.strip() or cp.stdout.strip()}")
    if not out.exists():
        raise TesseractBridgeError(f"Filmstrip attendu non produit : {out}")
    return out


def execute_export(root: Path, edit_name: str, version: str, *, output_name: str | None = None, resolution: str = "1080p", fps: int = 24, format_name: str = "mp4") -> Path:
    if resolution not in {"720p", "1080p", "4k"}:
        raise TesseractBridgeError("Résolution invalide : 720p, 1080p ou 4k attendu.")
    if fps not in {24, 30, 60}:
        raise TesseractBridgeError("FPS invalide : 24, 30 ou 60 attendu.")
    if format_name not in {"mp4", "prores"}:
        raise TesseractBridgeError("Format invalide : mp4 ou prores attendu.")
    cfg, status, plan = _ready_context(root, edit_name, version)
    project_file = Path(plan["paths"]["project"])
    if not project_file.exists():
        raise TesseractBridgeError("Projet Tesseract absent : exécutez d'abord le bootstrap.")
    suffix = ".mov" if format_name == "prores" else ".mp4"
    out = Path(plan["paths"]["version_dir"]) / (output_name or f"{edit_name}_{version}{suffix}")
    cp = subprocess.run(
        [status.executable, "export", "--project", str(project_file), "--resolution", resolution,
         "--fps", str(fps), "--format", format_name, "--output", str(out)],
        cwd=plan["paths"]["version_dir"], capture_output=True, text=True, env=_env_for_config(cfg), check=False,
    )
    if cp.returncode != 0:
        raise TesseractBridgeError(f"Export Tesseract échoué : {cp.stderr.strip() or cp.stdout.strip()}")
    if not out.exists():
        raise TesseractBridgeError(f"Export attendu non produit : {out}")
    return out


def execute_patch_actions(root: Path, edit_name: str, version: str, actions_file: Path) -> Path:
    root = root.expanduser().resolve()
    cfg, status, plan = _ready_context(root, edit_name, version)
    version_dir = Path(plan["paths"]["version_dir"])
    manifest_path = version_dir / "manifest.json"
    patch_path = version_dir / "patch.json"
    if not manifest_path.exists() or not patch_path.exists():
        raise TesseractBridgeError("La version ciblée n'est pas une révision PATCH complète.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("kind") != "patch":
        raise TesseractBridgeError(f"{edit_name}/{version} n'est pas une version PATCH.")
    parent = manifest.get("parent_version")
    if not parent:
        raise TesseractBridgeError("PATCH sans parent_version.")
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    if patch.get("lock_validation", {}).get("decision") != "ALLOWED":
        raise TesseractBridgeError("Le PATCH n'a pas une validation ALLOWED.")

    actions_file = actions_file.expanduser().resolve()
    if not actions_file.exists():
        raise TesseractBridgeError(f"Fichier d'actions introuvable : {actions_file}")
    try:
        actions = json.loads(actions_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TesseractBridgeError(f"JSON d'actions invalide : {exc}") from exc
    if not isinstance(actions, list):
        raise TesseractBridgeError("Le fichier d'actions doit contenir un tableau JSON.")

    parent_dir = _latest_version_dir(root, edit_name, parent)
    parent_project = parent_dir / f"{edit_name}_{parent}.tsrct"
    child_project = version_dir / f"{edit_name}_{version}.tsrct"
    if not parent_project.exists():
        raise TesseractBridgeError(f"Projet parent absent : {parent_project}")
    if child_project.exists():
        raise TesseractBridgeError(f"Refus d'écraser le projet de révision existant : {child_project}")

    work = version_dir / ".tesseract-work"
    work.mkdir(parents=True, exist_ok=True)
    stored_actions = work / "patch-actions.json"
    shutil.copy2(actions_file, stored_actions)
    shutil.copy2(parent_project, child_project)

    cp = subprocess.run(
        [status.executable, "project", "apply", "--project", str(child_project), "--actions", str(stored_actions)],
        cwd=str(version_dir), capture_output=True, text=True, env=_env_for_config(cfg), check=False,
    )
    if cp.returncode != 0:
        child_project.unlink(missing_ok=True)
        raise TesseractBridgeError(f"PATCH Tesseract refusé : {cp.stderr.strip() or cp.stdout.strip()}")

    inspect = subprocess.run(
        [status.executable, "project", "inspect", "--project", str(child_project), "--pretty"],
        cwd=str(version_dir), capture_output=True, text=True, env=_env_for_config(cfg), check=False,
    )
    if inspect.returncode != 0:
        child_project.unlink(missing_ok=True)
        raise TesseractBridgeError(f"Inspection post-PATCH échouée : {inspect.stderr.strip() or inspect.stdout.strip()}")
    (work / "project.after-patch.json").write_text(inspect.stdout, encoding="utf-8")

    patch["execution"] = {
        "status": "APPLIED_TESSERACT",
        "actions_file": str(stored_actions.relative_to(version_dir)),
        "detected_version": status.detected_version,
    }
    patch_path.write_text(json.dumps(patch, ensure_ascii=False, indent=2), encoding="utf-8")
    return child_project
