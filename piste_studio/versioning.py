from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import shutil

from .db import connect
from .config import write_yaml, read_yaml
from .metadata import fetch_media_with_metadata


@dataclass(frozen=True)
class VersionRecord:
    edit_name: str
    version_number: int
    version_label: str
    directory: Path
    manifest_path: Path
    brief_path: Path | None = None
    patch_path: Path | None = None


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        raise ValueError("Nom d'edit invalide.")
    return value


def _next_version_number(root: Path, edit_name: str) -> int:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT MAX(version_number) AS n FROM edit_versions WHERE edit_name=?",
            (edit_name,),
        ).fetchone()
        return int(row["n"] or 0) + 1
    finally:
        conn.close()


def _register(root: Path, rec: VersionRecord, kind: str, parent: str | None) -> None:
    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            """
            INSERT INTO edit_versions(
              edit_name, version_number, version_label, parent_version_label,
              kind, manifest_path, brief_path, patch_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.edit_name,
                rec.version_number,
                rec.version_label,
                parent,
                kind,
                str(rec.manifest_path.relative_to(root)),
                str(rec.brief_path.relative_to(root)) if rec.brief_path else None,
                str(rec.patch_path.relative_to(root)) if rec.patch_path else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def create_brief_version(root: Path, edit_name: str, brief: dict, decisions: dict) -> VersionRecord:
    edit_name = slugify(edit_name)
    number = _next_version_number(root, edit_name)
    label = f"V{number:03d}"
    directory = root / "edits" / edit_name / label
    directory.mkdir(parents=True, exist_ok=False)

    brief_path = directory / "brief.yaml"
    decisions_path = directory / "decisions.json"
    manifest_path = directory / "manifest.json"

    write_yaml(brief_path, brief)
    decisions_path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "edit_name": edit_name,
        "version": label,
        "version_number": number,
        "parent_version": None,
        "kind": "brief",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            "brief": "brief.yaml",
            "decisions": "decisions.json",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    rec = VersionRecord(edit_name, number, label, directory, manifest_path, brief_path, None)
    _register(root, rec, "brief", None)
    return rec


def create_patch_version(root: Path, edit_name: str, base_version: str, patch: dict) -> VersionRecord:
    edit_name = slugify(edit_name)
    base_dir = root / "edits" / edit_name / base_version
    if not base_dir.exists():
        raise ValueError(f"Version de base introuvable : {edit_name}/{base_version}")

    number = _next_version_number(root, edit_name)
    label = f"V{number:03d}"
    directory = root / "edits" / edit_name / label
    directory.mkdir(parents=True, exist_ok=False)

    brief_src = base_dir / "brief.yaml"
    brief_path: Path | None = None
    if brief_src.exists():
        brief_path = directory / "brief.yaml"
        shutil.copy2(brief_src, brief_path)

    patch_path = directory / "patch.json"
    manifest_path = directory / "manifest.json"
    patch_path.write_text(json.dumps(patch, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "edit_name": edit_name,
        "version": label,
        "version_number": number,
        "parent_version": base_version,
        "kind": "patch",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            "brief": "brief.yaml" if brief_path else None,
            "patch": "patch.json",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    rec = VersionRecord(edit_name, number, label, directory, manifest_path, brief_path, patch_path)
    _register(root, rec, "patch", base_version)
    return rec


def list_versions(root: Path, edit_name: str | None = None) -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        if edit_name:
            edit_name = slugify(edit_name)
            rows = conn.execute(
                "SELECT * FROM edit_versions WHERE edit_name=? ORDER BY version_number",
                (edit_name,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM edit_versions ORDER BY edit_name, version_number"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def create_timeline_version(root: Path, timeline: dict) -> VersionRecord:
    """Freeze the current validated working timeline into a new immutable edit version.

    A compact brief.yaml is emitted for the Tesseract bridge. The authoritative edit
    state remains timeline.json; brief.yaml exists so older bridge/bootstrap code can
    still derive duration, canvas and referenced media safely.
    """
    root = root.expanduser().resolve()
    from .timeline import validate_timeline
    clean = validate_timeline(root, timeline)
    edit_name = slugify(clean.get("edit_name") or "teaser_30")
    number = _next_version_number(root, edit_name)
    label = f"V{number:03d}"
    directory = root / "edits" / edit_name / label
    directory.mkdir(parents=True, exist_ok=False)

    rows = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    referenced: list[dict] = []
    seen: set[int] = set()
    for clip in clean.get("clips", []):
        media_id = clip.get("mediaDbId") or clip.get("audioDbId")
        if media_id is None:
            continue
        media_id = int(media_id)
        if media_id in seen:
            continue
        item = rows.get(media_id)
        if item is None:
            continue
        seen.add(media_id)
        referenced.append({
            "id": media_id,
            "path": item["relative_path"],
            "relative_path": item["relative_path"],
            "kind": item["kind"],
            "duration_seconds": item.get("duration_seconds"),
            "title": item.get("title"),
        })

    canon = read_yaml(root / "canon.yaml") or {}
    aspect_ratio = str(canon.get("visual", {}).get("aspect_ratio") or "16:9")
    video_beats: list[dict] = []
    for clip in sorted(clean.get("clips", []), key=lambda c: (float(c.get("start", 0)), str(c.get("id", "")))):
        if not clip.get("mediaDbId"):
            continue
        item = rows.get(int(clip["mediaDbId"]))
        if not item or item.get("kind") != "video":
            continue
        start = float(clip["start"])
        duration = float(clip["duration"])
        video_beats.append({
            "name": str(clip.get("label") or clip["id"]),
            "clip_id": clip["id"],
            "start": start,
            "end": start + duration,
            "duration": duration,
            "primary_media_id": int(clip["mediaDbId"]),
            "primary_media_path": item["relative_path"],
            "source_start_seconds": float(clip.get("sourceStart", 0) or 0),
            "volume": 0.0 if next((t for t in clean["tracks"] if t["id"] == clip["track"]), {}).get("muted") else float(clip.get("videoVolume", 1.0) or 1.0),
            "fit": str(clip.get("fit") or "contain"),
        })

    brief = {
        "schema_version": 3,
        "source": "ui_timeline",
        "deliverable": {
            "type": "timeline_edit",
            "duration_seconds": float(clean["duration_seconds"]),
            "aspect_ratio": aspect_ratio,
        },
        "candidate_pool": referenced,
        "suggested_beats": video_beats,
        "timeline_file": "timeline.json",
        "editorial_instructions": [
            "timeline.json is the authoritative edit state for this version.",
            "Never modify source media or the protected master.",
            "Preserve clip sourceRange and activeRange exactly unless Tesseract validation requires a shorter tail.",
        ],
    }

    timeline_path = directory / "timeline.json"
    brief_path = directory / "brief.yaml"
    manifest_path = directory / "manifest.json"
    timeline_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    write_yaml(brief_path, brief)
    manifest = {
        "schema_version": 2,
        "edit_name": edit_name,
        "version": label,
        "version_number": number,
        "parent_version": None,
        "kind": "timeline",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {"brief": "brief.yaml", "timeline": "timeline.json"},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    rec = VersionRecord(edit_name, number, label, directory, manifest_path, brief_path, None)
    _register(root, rec, "timeline", None)
    return rec
