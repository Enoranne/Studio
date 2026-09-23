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
from .editorial import (
    add_marker,
    delete_editorial_range,
    delete_marker,
    list_editorial_ranges,
    list_markers,
    set_editorial_range,
    suggest_alternatives,
)
from .media_intelligence import (
    MediaIntelligenceError,
    analyze_catalog,
    analyze_media,
    detect_media_tools,
    get_media_analysis,
    list_media_analysis,
    media_similarity,
)
from .semantic_vision import (
    SemanticVisionError,
    analyze_semantic_catalog,
    analyze_semantic_media,
    detect_semantic_vision,
    list_semantic_profiles,
    list_semantic_proposals,
    propose_semantic_tags,
    resolve_semantic_proposal,
)
from .audio_intelligence import (
    AudioIntelligenceError,
    analyze_audio,
    analyze_audio_catalog,
    apply_crossfade,
    apply_envelope,
    apply_gain_adjustment,
    clipping_risk_report,
    detect_audio_tools,
    get_audio_analysis,
    list_audio_analysis,
    normalization_proposal,
    propose_crossfade,
    propose_ducking,
)
from .audio_delivery import (
    AudioDeliveryError,
    AUDIO_DELIVERY_VERSION,
    delivery_presets,
    report_path as audio_report_path,
    run_master_check,
)


def _media_payload(root: Path) -> list[dict]:
    out = []
    ranges_by_media: dict[int, list[dict]] = {}
    for r in list_editorial_ranges(root):
        ranges_by_media.setdefault(int(r["media_id"]), []).append(r)
    analyses = list_media_analysis(root)
    semantic_profiles = list_semantic_profiles(root)
    audio_analyses = list_audio_analysis(root)
    for item in fetch_media_with_metadata(root):
        row = dict(item)
        p = (root / row["relative_path"]).resolve()
        row["filename"] = p.name
        row["exists"] = p.exists() and p.is_file()
        row["stream_url"] = f"/api/media/{row['id']}" if row["exists"] else None
        row["editorial_ranges"] = ranges_by_media.get(int(row["id"]), [])
        analysis = analyses.get(int(row["id"]))
        row["analysis"] = analysis
        row["semantic_profile"] = semantic_profiles.get(int(row["id"]))
        row["audio_loudness"] = audio_analyses.get(int(row["id"]))
        filmstrip_rel = analysis.get("filmstrip_path") if analysis else None
        row["filmstrip_url"] = (
            f"/api/media/{row['id']}/filmstrip"
            if filmstrip_rel and (root / filmstrip_rel).exists()
            else None
        )
        out.append(row)
    return out


def create_app(project_root: Path, ui_path: Path | None = None) -> FastAPI:
    root = project_root.expanduser().resolve()
    load_project(root)
    ui_file = (ui_path or (Path(__file__).resolve().parent / "ui" / "index.html")).resolve()
    if not ui_file.exists():
        raise RuntimeError(f"UI introuvable : {ui_file}")

    app = FastAPI(title="PISTE Studio Local App", version="0.21")
    app.state.project_root = root

    @app.get("/")
    def index():
        return FileResponse(ui_file, media_type="text/html")

    @app.get("/ui/{filename}")
    def ui_asset(filename: str):
        if filename not in {"style.css", "state.js", "editor.js", "ux-browser.js", "ux-timeline.js", "ux-magnetic.js", "ux-shell.js", "ux-polish.js", "ux-editorial.js", "ux-media-intelligence.js", "ux-semantic-vision.js", "ux-audio-mix.js", "ux-audio-intelligence.js", "ux-audio-delivery.js", "backend.js"}:
            raise HTTPException(404, "Ressource UI introuvable.")
        path = ui_file.parent / filename
        if not path.exists():
            raise HTTPException(404, "Ressource UI absente du package.")
        media_type = "text/css" if filename.endswith(".css") else "text/javascript"
        return FileResponse(path, media_type=media_type)

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": "0.21", "project_root": str(root)}

    @app.get("/api/state")
    def state(edit_name: str = "teaser_30"):
        paths, project = load_project(root)
        master_ok, master_message = verify_master(root) if project.get("project", {}).get("master") else (None, "Aucun master enregistré.")
        try:
            tesseract = asdict(detect_tesseract(root))
        except Exception as exc:
            tesseract = {"ready": False, "message": f"Diagnostic Tesseract indisponible : {exc}"}
        return {
            "app_version": "0.20",
            "project": project,
            "canon": read_yaml(paths.canon_yaml) or {},
            "locks": read_yaml(paths.locks_yaml) or {"locks": []},
            "media": _media_payload(root),
            "versions": list_versions(root),
            "timeline": load_timeline(root, edit_name),
            "history": history_status(root, edit_name),
            "markers": list_markers(root, edit_name),
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

    @app.post("/api/media/{media_id}/ranges")
    def editorial_range_set(media_id: int, payload: dict = Body(...)):
        try:
            row = set_editorial_range(
                root,
                media_id,
                kind=str(payload.get("kind") or ""),
                source_in=float(payload.get("source_in", 0)),
                source_out=float(payload.get("source_out", 0)),
                note=payload.get("note"),
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {
            "ok": True,
            "range": row,
            "ranges": list_editorial_ranges(root, media_id),
        }

    @app.delete("/api/editorial/ranges/{range_id}")
    def editorial_range_delete(range_id: int):
        if not delete_editorial_range(root, range_id):
            raise HTTPException(404, "Plage éditoriale introuvable.")
        return {"ok": True}

    @app.get("/api/markers")
    def editorial_markers(edit_name: str = "teaser_30"):
        return {"markers": list_markers(root, edit_name)}

    @app.post("/api/markers")
    def editorial_marker_add(payload: dict = Body(...)):
        try:
            row = add_marker(
                root,
                edit_name=str(payload.get("edit_name") or "teaser_30"),
                time_seconds=float(payload.get("time_seconds", 0)),
                label=str(payload.get("label") or ""),
                kind=str(payload.get("kind") or "note"),
                note=payload.get("note"),
                media_id=payload.get("media_id"),
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": True, "marker": row}

    @app.delete("/api/markers/{marker_id}")
    def editorial_marker_delete(marker_id: int):
        if not delete_marker(root, marker_id):
            raise HTTPException(404, "Marqueur introuvable.")
        return {"ok": True}

    @app.get("/api/editorial/suggest/{media_id}")
    def editorial_suggest(
        media_id: int,
        limit: int = 5,
        max_spoiler: int | None = None,
    ):
        try:
            return suggest_alternatives(
                root,
                media_id,
                limit=limit,
                max_spoiler=max_spoiler,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/media/intelligence/status")
    def media_intelligence_status():
        tools = detect_media_tools()
        return {
            "ready": tools.ready,
            "ffmpeg": bool(tools.ffmpeg),
            "ffprobe": bool(tools.ffprobe),
            "analyzer_version": "0.17-local-1",
        }

    @app.post("/api/media/analyze")
    def media_analyze_catalog(payload: dict = Body(default_factory=dict)):
        return analyze_catalog(
            root,
            force=bool(payload.get("force", False)),
            make_filmstrips=bool(payload.get("filmstrips", True)),
        )

    @app.post("/api/media/{media_id}/analyze")
    def media_analyze_one(media_id: int, payload: dict = Body(default_factory=dict)):
        try:
            return analyze_media(
                root,
                media_id,
                make_filmstrip=bool(payload.get("filmstrip", True)),
                force=bool(payload.get("force", False)),
            )
        except MediaIntelligenceError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/media/{media_id}/similar")
    def media_similar(media_id: int):
        try:
            return {"media_id": media_id, "similar": media_similarity(root, media_id)}
        except MediaIntelligenceError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/media/{media_id}/filmstrip")
    def media_filmstrip(media_id: int):
        analysis = get_media_analysis(root, media_id)
        if not analysis or not analysis.get("filmstrip_path"):
            raise HTTPException(404, "Filmstrip non généré.")
        path = (root / analysis["filmstrip_path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise HTTPException(400, "Chemin filmstrip hors projet.") from exc
        if not path.exists() or not path.is_file():
            raise HTTPException(404, "Filmstrip absent du cache.")
        return FileResponse(path, media_type="image/jpeg")

    @app.get("/api/vision/status")
    def semantic_vision_status():
        return asdict(detect_semantic_vision())

    @app.post("/api/vision/analyze")
    def semantic_vision_analyze_catalog(payload: dict = Body(default_factory=dict)):
        try:
            return analyze_semantic_catalog(
                root,
                allow_model_download=bool(
                    payload.get("allow_model_download", False)
                ),
            )
        except SemanticVisionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/vision/analyze/{media_id}")
    def semantic_vision_analyze_media(
        media_id: int,
        payload: dict = Body(default_factory=dict),
    ):
        try:
            return analyze_semantic_media(
                root,
                media_id,
                allow_model_download=bool(
                    payload.get("allow_model_download", False)
                ),
                force_frames=bool(payload.get("force_frames", False)),
            )
        except SemanticVisionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/vision/proposals/{media_id}")
    def semantic_vision_proposals(media_id: int):
        try:
            return {
                "media_id": media_id,
                "policy": {
                    "human_validation_required": True,
                    "automatic_tag_write": False,
                    "automatic_storyline_change": False,
                },
                "proposals": list_semantic_proposals(root, media_id),
            }
        except SemanticVisionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/vision/propose/{media_id}")
    def semantic_vision_propose(
        media_id: int,
        payload: dict = Body(default_factory=dict),
    ):
        try:
            return propose_semantic_tags(
                root,
                media_id,
                reset_rejected=bool(
                    payload.get("reset_rejected", False)
                ),
            )
        except SemanticVisionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/vision/proposals/{proposal_id}/resolve")
    def semantic_vision_resolve(
        proposal_id: int,
        payload: dict = Body(...),
    ):
        if "accept" not in payload:
            raise HTTPException(422, "accept est requis.")
        try:
            return {
                "proposal": resolve_semantic_proposal(
                    root,
                    proposal_id,
                    accept=bool(payload["accept"]),
                ),
                "media": _media_payload(root),
            }
        except SemanticVisionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/audio/intelligence/status")
    def audio_intelligence_status():
        tools = detect_audio_tools()
        return {"ready": tools.ready, "ffmpeg": bool(tools.ffmpeg), "analyzer_version": "0.20-loudness-1"}

    @app.post("/api/audio/analyze")
    def audio_analyze_catalog(payload: dict = Body(default_factory=dict)):
        return analyze_audio_catalog(
            root,
            force=bool(payload.get("force", False)),
            detect_silences=bool(payload.get("silences", True)),
        )

    @app.post("/api/audio/{media_id}/analyze")
    def audio_analyze_one(media_id: int, payload: dict = Body(default_factory=dict)):
        try:
            return analyze_audio(
                root,
                media_id,
                force=bool(payload.get("force", False)),
                detect_silences=bool(payload.get("silences", True)),
            )
        except AudioIntelligenceError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/audio/normalize/propose")
    def audio_normalize_propose(payload: dict = Body(...)):
        try:
            return normalization_proposal(
                root,
                int(payload["media_id"]),
                target_lufs=float(payload.get("target_lufs", -16.0)),
                true_peak_ceiling=float(payload.get("true_peak_ceiling", -1.5)),
            )
        except (AudioIntelligenceError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/audio/normalize/apply")
    def audio_normalize_apply(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        if not isinstance(timeline, dict):
            raise HTTPException(422, "timeline doit être un objet.")
        try:
            after = apply_gain_adjustment(
                timeline,
                str(payload["clip_id"]),
                float(payload["gain_adjustment_db"]),
            )
            clean = validate_timeline(root, after)
            create_checkpoint(
                root,
                timeline,
                edit_name=str(timeline.get("edit_name") or "teaser_30"),
                reason=f"Normalisation audio · {payload['clip_id']}",
            )
            save_timeline(root, clean)
            return {"ok": True, "timeline": clean}
        except (AudioIntelligenceError, TimelineError, HistoryError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/audio/clipping")
    def audio_clipping(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        if not isinstance(timeline, dict):
            raise HTTPException(422, "timeline doit être un objet.")
        try:
            clean = validate_timeline(root, timeline)
            return clipping_risk_report(
                root,
                clean,
                true_peak_ceiling=float(payload.get("true_peak_ceiling", -1.0)),
            )
        except (AudioIntelligenceError, TimelineError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/audio/ducking/propose")
    def audio_ducking_propose(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        if not isinstance(timeline, dict):
            raise HTTPException(422, "timeline doit être un objet.")
        try:
            clean = validate_timeline(root, timeline)
            return propose_ducking(
                clean,
                str(payload["music_clip_id"]),
                reduction_db=float(payload.get("reduction_db", 8.0)),
                attack_seconds=float(payload.get("attack_seconds", 0.25)),
                release_seconds=float(payload.get("release_seconds", 0.5)),
            )
        except (AudioIntelligenceError, TimelineError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/audio/ducking/apply")
    def audio_ducking_apply(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        if not isinstance(timeline, dict):
            raise HTTPException(422, "timeline doit être un objet.")
        try:
            after = apply_envelope(
                timeline,
                str(payload["music_clip_id"]),
                list(payload.get("envelope") or []),
            )
            clean = validate_timeline(root, after)
            create_checkpoint(
                root,
                timeline,
                edit_name=str(timeline.get("edit_name") or "teaser_30"),
                reason=f"Ducking audio · {payload['music_clip_id']}",
            )
            save_timeline(root, clean)
            return {"ok": True, "timeline": clean}
        except (AudioIntelligenceError, TimelineError, HistoryError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/audio/crossfade/propose")
    def audio_crossfade_propose(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        if not isinstance(timeline, dict):
            raise HTTPException(422, "timeline doit être un objet.")
        try:
            clean = validate_timeline(root, timeline)
            return propose_crossfade(
                clean,
                str(payload["left_clip_id"]),
                str(payload["right_clip_id"]),
                duration_seconds=float(payload.get("duration_seconds", 0.5)),
            )
        except (AudioIntelligenceError, TimelineError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/audio/crossfade/apply")
    def audio_crossfade_apply(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        proposal = payload.get("proposal")
        if not isinstance(timeline, dict) or not isinstance(proposal, dict):
            raise HTTPException(422, "timeline et proposal sont requis.")
        try:
            after = apply_crossfade(timeline, proposal)
            clean = validate_timeline(root, after)
            create_checkpoint(
                root,
                timeline,
                edit_name=str(timeline.get("edit_name") or "teaser_30"),
                reason=f"Crossfade audio · {proposal.get('left_clip_id')} / {proposal.get('right_clip_id')}",
            )
            save_timeline(root, clean)
            return {"ok": True, "timeline": clean}
        except (AudioIntelligenceError, TimelineError, HistoryError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/audio/delivery/presets")
    def audio_delivery_presets():
        return {
            "version": AUDIO_DELIVERY_VERSION,
            "presets": delivery_presets(),
            "policy": {
                "reference_presets_not_universal_standards": True,
                "limiter_requires_explicit_choice": True,
            },
        }

    @app.post("/api/audio/master/check")
    def audio_master_check(payload: dict = Body(...)):
        timeline = payload.get("timeline")
        if not isinstance(timeline, dict):
            raise HTTPException(422, "timeline doit être un objet.")
        try:
            clean = validate_timeline(root, timeline)
            report = run_master_check(
                root,
                clean,
                preset_id=str(payload.get("preset_id") or "online_reference"),
                target_lufs=(
                    float(payload["target_lufs"])
                    if payload.get("target_lufs") is not None
                    else None
                ),
                true_peak_ceiling=(
                    float(payload["true_peak_ceiling"])
                    if payload.get("true_peak_ceiling") is not None
                    else None
                ),
                loudness_tolerance_lu=(
                    float(payload["loudness_tolerance_lu"])
                    if payload.get("loudness_tolerance_lu") is not None
                    else None
                ),
                limiter=bool(payload.get("limiter", False)),
            )
            report["report_url"] = f"/api/audio/master/reports/{report['report_name']}"
            return report
        except (AudioDeliveryError, TimelineError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/audio/master/reports/{report_name}")
    def audio_master_report(report_name: str):
        try:
            path = audio_report_path(root, report_name)
        except AudioDeliveryError as exc:
            raise HTTPException(404, str(exc)) from exc
        return FileResponse(path, media_type="application/json", filename=path.name)

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
