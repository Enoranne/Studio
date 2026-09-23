from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import argparse
import threading
import webbrowser

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
import uvicorn

from .config import read_yaml
from .locks import check_operation
from .media import scan_media
from .metadata import fetch_media_with_metadata
from .project import load_project, verify_master
from .tesseract_bridge import detect_tesseract, execute_bootstrap, execute_preview, execute_filmstrip, execute_export, TesseractBridgeError
from .authoring import execute_authoring
from .timeline import TimelineError, load_timeline, save_timeline, validate_timeline
from .versioning import list_versions, create_timeline_version
from .storyline import StorylineError, validate_locked_change
from .history import HistoryError, create_checkpoint, history_status, undo_checkpoint


def _media_payload(root: Path) -> list[dict]:
    out = []
    for item in fetch_media_with_metadata(root):
        row = dict(item)
        p = (root / row["relative_path"]).resolve()
        row["filename"] = p.name
        row["exists"] = p.exists() and p.is_file()
        row["stream_url"] = f"/api/media/{row['id']}" if row["exists"] else None
        out.append(row)
    return out


def create_app(project_root: Path, ui_path: Path | None = None) -> FastAPI:
    root = project_root.expanduser().resolve()
    load_project(root)
    ui_file = (ui_path or (Path(__file__).resolve().parent / "ui" / "index.html")).resolve()
    if not ui_file.exists():
        raise RuntimeError(f"UI introuvable : {ui_file}")

    app = FastAPI(title="PISTE Studio Local App", version="0.15")
    app.state.project_root = root

    @app.get("/")
    def index():
        return FileResponse(ui_file, media_type="text/html")

    @app.get("/ui/{filename}")
    def ui_asset(filename: str):
        if filename not in {"style.css", "state.js", "editor.js", "ux-browser.js", "ux-timeline.js", "ux-magnetic.js", "ux-shell.js", "ux-polish.js", "backend.js"}:
            raise HTTPException(404, "Ressource UI introuvable.")
        path = ui_file.parent / filename
        if not path.exists():
            raise HTTPException(404, "Ressource UI absente du package.")
        media_type = "text/css" if filename.endswith(".css") else "text/javascript"
        return FileResponse(path, media_type=media_type)

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": "0.15", "project_root": str(root)}

    @app.get("/api/state")
    def state(edit_name: str = "teaser_30"):
        paths, project = load_project(root)
        master_ok, master_message = verify_master(root) if project.get("project", {}).get("master") else (None, "Aucun master enregistré.")
        try:
            tesseract = asdict(detect_tesseract(root))
        except Exception as exc:
            tesseract = {"ready": False, "message": f"Diagnostic Tesseract indisponible : {exc}"}
        return {
            "app_version": "0.15",
            "project": project,
            "canon": read_yaml(paths.canon_yaml) or {},
            "locks": read_yaml(paths.locks_yaml) or {"locks": []},
            "media": _media_payload(root),
            "versions": list_versions(root),
            "timeline": load_timeline(root, edit_name),
            "history": history_status(root, edit_name),
            "master": {"ok": master_ok, "message": master_message},
            "tesseract": tesseract,
        }

    @app.post("/api/scan")
    def scan():
        result = scan_media(root)
        return {"scan": result, "media": _media_payload(root)}

    @app.get("/api/media/{media_id}")
    def media_file(media_id: int):
        rows = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
        item = rows.get(media_id)
        if item is None:
            raise HTTPException(404, "Média introuvable.")
        path = (root / item["relative_path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise HTTPException(400, "Chemin média hors projet.") from exc
        if not path.exists() or not path.is_file():
            raise HTTPException(404, "Fichier média absent.")
        return FileResponse(path)

    @app.get("/api/timeline")
    def get_timeline(edit_name: str = "teaser_30"):
        return {"timeline": load_timeline(root, edit_name)}

    @app.post("/api/timeline")
    def put_timeline(payload: dict = Body(...)):
        try:
            path = save_timeline(root, payload)
        except TimelineError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": True, "path": str(path.relative_to(root)), "timeline": load_timeline(root, payload.get("edit_name") or "teaser_30")}

    @app.post("/api/storyline/validate")
    def storyline_validate(payload: dict = Body(...)):
        before = payload.get("before")
        after = payload.get("after")
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise HTTPException(422, "before et after doivent être des timelines.")
        try:
            clean = validate_timeline(root, after)
            validate_locked_change(root, before, clean)
        except (TimelineError, StorylineError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": True, "timeline": clean}

    @app.get("/api/history")
    def get_history(edit_name: str = "teaser_30"):
        return history_status(root, edit_name)

    @app.post("/api/history/checkpoint")
    def history_checkpoint(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        if not isinstance(timeline, dict):
            raise HTTPException(422, "timeline doit être un objet.")
        try:
            return create_checkpoint(
                root,
                timeline,
                edit_name=str(payload.get("edit_name") or timeline.get("edit_name") or "teaser_30"),
                reason=str(payload.get("reason") or "edit"),
            )
        except (TimelineError, HistoryError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/history/undo")
    def history_undo(payload: dict = Body(default_factory=dict)):
        try:
            return undo_checkpoint(
                root,
                str(payload.get("edit_name") or "teaser_30"),
            )
        except (TimelineError, HistoryError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/locks/check")
    def lock_check(payload: dict = Body(...)):
        try:
            decision = check_operation(
                root,
                operation=str(payload.get("operation") or "edit"),
                start=payload.get("start"),
                end=payload.get("end"),
                target=str(payload.get("target") or "timeline"),
                explicit_soft_unlock=bool(payload.get("explicit_soft_unlock", False)),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return asdict(decision)

    @app.get("/api/tesseract/status")
    def tesseract_status():
        return asdict(detect_tesseract(root))

    @app.post("/api/publish")
    def publish_timeline(payload: dict = Body(default_factory=dict)):
        edit_name = str(payload.get("edit_name") or "teaser_30")
        timeline = load_timeline(root, edit_name)
        if timeline is None:
            raise HTTPException(404, "Aucune timeline de travail enregistrée pour cet edit.")
        try:
            rec = create_timeline_version(root, timeline)
        except (TimelineError, ValueError, FileExistsError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {
            "ok": True,
            "edit_name": rec.edit_name,
            "version": rec.version_label,
            "version_number": rec.version_number,
            "directory": str(rec.directory.relative_to(root)),
            "versions": list_versions(root, rec.edit_name),
        }

    @app.post("/api/tesseract/{version}/bootstrap")
    def tesseract_bootstrap(version: str, payload: dict = Body(default_factory=dict)):
        edit_name = str(payload.get("edit_name") or "teaser_30")
        execute = bool(payload.get("execute", False))
        try:
            return execute_bootstrap(root, edit_name, version, dry_run=not execute)
        except (TesseractBridgeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/tesseract/{version}/author")
    def tesseract_author(version: str, payload: dict = Body(default_factory=dict)):
        edit_name = str(payload.get("edit_name") or "teaser_30")
        execute = bool(payload.get("execute", False))
        try:
            return execute_authoring(root, edit_name, version, dry_run=not execute)
        except (TesseractBridgeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/tesseract/{version}/preview")
    def tesseract_preview(version: str, payload: dict = Body(default_factory=dict)):
        edit_name = str(payload.get("edit_name") or "teaser_30")
        time_seconds = float(payload.get("time_seconds", 1.0))
        try:
            path = execute_preview(root, edit_name, version, time_seconds=time_seconds)
        except (TesseractBridgeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": True, "path": str(path.relative_to(root))}

    @app.post("/api/tesseract/{version}/filmstrip")
    def tesseract_filmstrip(version: str, payload: dict = Body(default_factory=dict)):
        edit_name = str(payload.get("edit_name") or "teaser_30")
        timeline = load_timeline(root, edit_name) or {}
        duration_ms = int(float(payload.get("duration_seconds", timeline.get("duration_seconds", 30))) * 1000)
        interval_ms = int(payload.get("interval_ms", 500))
        try:
            path = execute_filmstrip(root, edit_name, version, duration_ms=duration_ms, interval_ms=interval_ms)
        except (TesseractBridgeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": True, "path": str(path.relative_to(root))}

    @app.post("/api/tesseract/{version}/export")
    def tesseract_export(version: str, payload: dict = Body(default_factory=dict)):
        edit_name = str(payload.get("edit_name") or "teaser_30")
        try:
            path = execute_export(
                root, edit_name, version,
                resolution=str(payload.get("resolution") or "1080p"),
                fps=int(payload.get("fps") or 24),
                format_name=str(payload.get("format") or "mp4"),
            )
        except (TesseractBridgeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": True, "path": str(path.relative_to(root))}

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PISTE Studio local UI server")
    parser.add_argument("--project", required=True, help="Dossier d'un projet PISTE Studio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="Ne pas ouvrir automatiquement le navigateur")
    args = parser.parse_args(argv)

    root = Path(args.project).expanduser().resolve()
    app = create_app(root)
    url = f"http://{args.host}:{args.port}/"
    if not args.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
