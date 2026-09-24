from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from .readiness import build_production_readiness


PRODUCTION_RUN_VERSION = "0.24.1"


def _criterion(name: str, ok: bool, message: str, **details) -> dict:
    out = {"id": name, "status": "PASS" if ok else "MISSING", "message": message}
    out.update(details)
    return out


def build_production_run_report(
    root: Path,
    *,
    edit_name: str = "teaser_30",
    version: str | None = None,
) -> dict:
    root = root.expanduser().resolve()
    readiness = build_production_readiness(
        root,
        edit_name=edit_name,
        version=version,
    )
    selected = readiness.get("selection") or {}
    selected_edit = selected.get("edit_name")
    selected_version = selected.get("version")
    criteria: list[dict] = []
    timeline = None

    if selected_edit and selected_version:
        timeline_path = root / "edits" / selected_edit / selected_version / "timeline.json"
        if timeline_path.is_file():
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))

    clips = list((timeline or {}).get("clips") or [])
    tracks = {str(x.get("id")): x for x in (timeline or {}).get("tracks") or []}
    video_clips = [c for c in clips if str(tracks.get(str(c.get("track")), {}).get("kind", c.get("track", ""))).lower() == "video"]
    audio_clips = [c for c in clips if str(tracks.get(str(c.get("track")), {}).get("kind", c.get("track", ""))).lower() == "audio"]
    titles = [c for c in clips if str(c.get("track")) == "titles"]
    final_cards = [c for c in titles if c.get("titleRole") == "final_card"]
    connected = [c for c in clips if c.get("parentClipId")]
    fades = [c for c in audio_clips if float(c.get("fadeIn", 0) or 0) > 0 or float(c.get("fadeOut", 0) or 0) > 0]
    automated = [c for c in audio_clips if len(c.get("volumeEnvelope") or []) >= 2]

    criteria.extend([
        _criterion("published_timeline", bool(timeline), "Une version timeline publiée est disponible." if timeline else "Publier une version timeline avant la recette réelle."),
        _criterion("real_video_sequence", len(video_clips) >= 5, f"{len(video_clips)} plan(s) vidéo publié(s).", count=len(video_clips), target=5),
        _criterion("audio_present", len(audio_clips) >= 1, f"{len(audio_clips)} clip(s) audio publié(s).", count=len(audio_clips), target=1),
        _criterion("audio_fade", len(fades) >= 1, f"{len(fades)} clip(s) audio avec fade.", count=len(fades), target=1),
        _criterion("audio_automation", len(automated) >= 1, f"{len(automated)} clip(s) audio avec automation.", count=len(automated), target=1),
        _criterion("title_overlay", len(titles) >= 1, f"{len(titles)} titre(s)/overlay(s).", count=len(titles), target=1),
        _criterion("final_card", len(final_cards) >= 1, f"{len(final_cards)} carton(s) final(aux).", count=len(final_cards), target=1),
        _criterion("storyline_connection", len(connected) >= 1, f"{len(connected)} élément(s) connecté(s) à la Storyline.", count=len(connected), target=1),
    ])

    delivery_reports: list[dict] = []
    if selected_edit and selected_version:
        report_dir = root / "reports" / "delivery"
        prefix = f"{selected_edit}_{selected_version}_"
        if report_dir.is_dir():
            for path in sorted(report_dir.glob(f"{prefix}*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                output_rel = data.get("output_relative_path")
                output_ok = bool(output_rel and (root / str(output_rel)).is_file())
                conformance = data.get("conformance") or {}
                delivery_reports.append({
                    "report": path.relative_to(root).as_posix(),
                    "output_relative_path": output_rel,
                    "output_exists": output_ok,
                    "conformance": conformance,
                })

    conforming = [
        item for item in delivery_reports
        if item["output_exists"] and str(item["conformance"].get("status") or "") == "PASS"
    ]
    criteria.append(_criterion(
        "delivery_artifact",
        bool(conforming),
        "Au moins un livrable final conforme est présent." if conforming else "Aucun livrable final conforme n'est encore présent.",
        reports=delivery_reports,
    ))

    machine_complete = all(x["status"] == "PASS" for x in criteria)
    if machine_complete and readiness.get("capabilities", {}).get("can_deliver"):
        status = "AWAITING_HUMAN_REVIEW"
        next_action = "Visionner le livrable final en entier, noter les frictions P0–P3 et valider ou refuser la recette."
    elif readiness.get("pipeline_status") == "BLOCKED":
        status = "BLOCKED"
        next_action = readiness.get("next_action")
    else:
        status = "IN_PROGRESS"
        missing = [x["id"] for x in criteria if x["status"] != "PASS"]
        next_action = readiness.get("next_action") or ("Compléter : " + ", ".join(missing))

    return {
        "version": PRODUCTION_RUN_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "edit_name": selected_edit or edit_name,
        "published_version": selected_version,
        "status": status,
        "machine_complete": machine_complete,
        "human_review_required": True,
        "criteria": criteria,
        "readiness": readiness,
        "next_action": next_action,
        "policy": {
            "never_auto_pass_human_review": True,
            "source_media_immutable": True,
            "master_immutable": True,
            "real_media_required": True,
        },
    }


def save_production_run_report(
    root: Path,
    *,
    edit_name: str = "teaser_30",
    version: str | None = None,
) -> Path:
    root = root.expanduser().resolve()
    report = build_production_run_report(root, edit_name=edit_name, version=version)
    folder = root / "reports" / "production"
    folder.mkdir(parents=True, exist_ok=True)
    version_label = report.get("published_version") or "WORKING"
    path = folder / f"{report['edit_name']}_{version_label}_production-run.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
