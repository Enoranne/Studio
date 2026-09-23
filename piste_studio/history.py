from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from .timeline import validate_timeline, save_timeline
from .versioning import slugify


class HistoryError(ValueError):
    pass


def _history_dir(root: Path, edit_name: str) -> Path:
    return root / "edits" / slugify(edit_name) / "history"


def _index_path(root: Path, edit_name: str) -> Path:
    return _history_dir(root, edit_name) / "index.json"


def _read_index(root: Path, edit_name: str) -> dict:
    path = _index_path(root, edit_name)
    if not path.exists():
        return {"schema_version": 1, "cursor": 0, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("schema_version", 1)
    data.setdefault("cursor", len(data.get("entries", [])))
    data.setdefault("entries", [])
    return data


def _write_index(root: Path, edit_name: str, data: dict) -> None:
    path = _index_path(root, edit_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def history_status(root: Path, edit_name: str = "teaser_30") -> dict:
    idx = _read_index(root, edit_name)
    cursor = int(idx["cursor"])
    entries = idx["entries"]
    return {
        "cursor": cursor,
        "count": len(entries),
        "can_undo": cursor > 0,
        "last": entries[cursor - 1] if cursor > 0 else None,
    }


def create_checkpoint(
    root: Path,
    timeline: dict,
    *,
    edit_name: str | None = None,
    reason: str = "edit",
) -> dict:
    clean = validate_timeline(root, timeline)
    edit = slugify(edit_name or clean["edit_name"])
    idx = _read_index(root, edit)
    cursor = int(idx["cursor"])
    entries = list(idx["entries"][:cursor])

    number = max(
        [int(str(x.get("id", "H000000"))[1:]) for x in entries if str(x.get("id", "")).startswith("H")]
        or [0]
    ) + 1
    hid = f"H{number:06d}"
    directory = _history_dir(root, edit)
    directory.mkdir(parents=True, exist_ok=True)
    snapshot_path = directory / f"{hid}.json"
    snapshot_path.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    entry = {
        "id": hid,
        "reason": str(reason or "edit")[:160],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": snapshot_path.name,
    }
    entries.append(entry)
    idx = {
        "schema_version": 1,
        "cursor": len(entries),
        "entries": entries,
    }
    _write_index(root, edit, idx)
    return {"checkpoint": entry, **history_status(root, edit)}


def undo_checkpoint(root: Path, edit_name: str = "teaser_30") -> dict:
    edit = slugify(edit_name)
    idx = _read_index(root, edit)
    cursor = int(idx["cursor"])
    if cursor <= 0:
        raise HistoryError("Aucun checkpoint à restaurer.")
    entry = idx["entries"][cursor - 1]
    snapshot_path = _history_dir(root, edit) / entry["snapshot"]
    if not snapshot_path.exists():
        raise HistoryError(f"Snapshot introuvable : {entry['snapshot']}")
    timeline = json.loads(snapshot_path.read_text(encoding="utf-8"))
    save_timeline(root, timeline)
    idx["cursor"] = cursor - 1
    _write_index(root, edit, idx)
    return {
        "restored": entry,
        "timeline": timeline,
        **history_status(root, edit),
    }
