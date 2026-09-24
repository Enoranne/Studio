from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

from .timeline import load_timeline, validate_timeline, save_timeline
from .versioning import slugify


class HistoryError(ValueError):
    pass


HISTORY_SCHEMA_VERSION = 2
HISTORY_ACTORS = {"user", "agent", "system"}


def _history_dir(root: Path, edit_name: str) -> Path:
    return root / "edits" / slugify(edit_name) / "history"


def _index_path(root: Path, edit_name: str) -> Path:
    return _history_dir(root, edit_name) / "index.json"


def _entry_number(entry: dict) -> int:
    raw = str(entry.get("id") or "")
    if not raw.startswith("H"):
        return 0
    try:
        return int(raw[1:])
    except ValueError:
        return 0


def _normalise_actor(value: object) -> str:
    actor = str(value or "user").strip().lower()
    if actor not in HISTORY_ACTORS:
        raise HistoryError("actor doit être user, agent ou system.")
    return actor


def _normalise_affected(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        value = [value]
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        item_text = str(item or "").strip()
        if not item_text or item_text in seen:
            continue
        seen.add(item_text)
        out.append(item_text[:160])
    return out[:100]


def _read_index(root: Path, edit_name: str) -> dict:
    path = _index_path(root, edit_name)
    if not path.exists():
        return {
            "schema_version": HISTORY_SCHEMA_VERSION,
            "cursor": 0,
            "next_sequence": 1,
            "entries": [],
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise HistoryError("Index historique invalide : entries doit être une liste.")

    cursor = int(data.get("cursor", len(entries)))
    cursor = max(0, min(cursor, len(entries)))
    highest = max((_entry_number(entry) for entry in entries), default=0)
    next_sequence = max(
        highest + 1,
        int(data.get("next_sequence", highest + 1) or highest + 1),
    )
    return {
        **data,
        "schema_version": HISTORY_SCHEMA_VERSION,
        "cursor": cursor,
        "next_sequence": next_sequence,
        "entries": entries,
    }


def _write_index(root: Path, edit_name: str, data: dict) -> None:
    path = _index_path(root, edit_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _snapshot_path(root: Path, edit_name: str, filename: str) -> Path:
    directory = _history_dir(root, edit_name)
    path = directory / filename
    if path.parent != directory:
        raise HistoryError("Chemin de snapshot historique invalide.")
    return path


def _write_snapshot(
    root: Path,
    edit_name: str,
    filename: str,
    timeline: dict,
) -> None:
    directory = _history_dir(root, edit_name)
    directory.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(root, edit_name, filename)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _read_snapshot(
    root: Path,
    edit_name: str,
    filename: str | None,
) -> dict:
    if not filename:
        raise HistoryError("Snapshot historique non renseigné.")
    path = _snapshot_path(root, edit_name, filename)
    if not path.exists():
        raise HistoryError(f"Snapshot introuvable : {filename}")
    return json.loads(path.read_text(encoding="utf-8"))


def _next_history_id(idx: dict) -> tuple[str, int]:
    number = int(idx.get("next_sequence", 1) or 1)
    return f"H{number:06d}", number + 1


def _truncate_redo_branch(idx: dict) -> list[dict]:
    cursor = int(idx["cursor"])
    return list(idx["entries"][:cursor])


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _created_at(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def history_status(root: Path, edit_name: str = "teaser_30") -> dict:
    idx = _read_index(root, edit_name)
    cursor = int(idx["cursor"])
    entries = idx["entries"]
    return {
        "schema_version": int(idx.get("schema_version", HISTORY_SCHEMA_VERSION)),
        "cursor": cursor,
        "count": len(entries),
        "can_undo": cursor > 0,
        "can_redo": cursor < len(entries),
        "last": entries[cursor - 1] if cursor > 0 else None,
        "next": entries[cursor] if cursor < len(entries) else None,
    }


def create_checkpoint(
    root: Path,
    timeline: dict,
    *,
    edit_name: str | None = None,
    reason: str = "edit",
    actor: str = "user",
    operation: str = "checkpoint",
    transaction_id: str | None = None,
    affected: object = None,
) -> dict:
    """Create a legacy-compatible before-state safety checkpoint.

    V0.30 keeps this API for callers that do not yet provide an after-state.
    New transactional edit paths should prefer record_transaction.
    """
    clean = validate_timeline(root, timeline)
    edit = slugify(edit_name or clean["edit_name"])
    idx = _read_index(root, edit)
    entries = _truncate_redo_branch(idx)
    hid, next_sequence = _next_history_id(idx)
    snapshot_name = f"{hid}.json"
    _write_snapshot(root, edit, snapshot_name, clean)

    entry = {
        "id": hid,
        "kind": "checkpoint",
        "reason": str(reason or "edit")[:160],
        "actor": _normalise_actor(actor),
        "operation": str(operation or "checkpoint")[:160],
        "transaction_id": str(transaction_id or uuid4())[:160],
        "affected": _normalise_affected(affected),
        "created_at": _iso_now(),
        "snapshot": snapshot_name,
        "before_snapshot": snapshot_name,
    }
    entries.append(entry)
    idx = {
        **idx,
        "schema_version": HISTORY_SCHEMA_VERSION,
        "cursor": len(entries),
        "next_sequence": next_sequence,
        "entries": entries,
    }
    _write_index(root, edit, idx)
    return {"checkpoint": entry, **history_status(root, edit)}


def record_transaction(
    root: Path,
    before: dict,
    after: dict,
    *,
    edit_name: str | None = None,
    reason: str = "edit",
    actor: str = "user",
    operation: str = "edit",
    transaction_id: str | None = None,
    affected: object = None,
    coalesce_key: str | None = None,
    coalesce_window_ms: int = 500,
) -> dict:
    """Record one reversible edit and persist its after-state."""
    clean_before = validate_timeline(root, before)
    clean_after = validate_timeline(root, after)
    edit = slugify(
        edit_name
        or clean_after.get("edit_name")
        or clean_before["edit_name"]
    )
    if (
        slugify(clean_before["edit_name"]) != edit
        or slugify(clean_after["edit_name"]) != edit
    ):
        raise HistoryError("before et after doivent appartenir au même edit.")

    actor_name = _normalise_actor(actor)
    operation_name = str(operation or "edit").strip()[:160] or "edit"
    reason_text = str(reason or operation_name).strip()[:160] or operation_name
    affected_items = _normalise_affected(affected)
    key = str(coalesce_key or "").strip()[:160] or None
    window_ms = max(0, int(coalesce_window_ms))

    idx = _read_index(root, edit)
    had_redo_branch = int(idx["cursor"]) < len(idx["entries"])
    entries = _truncate_redo_branch(idx)
    now = datetime.now(timezone.utc)

    previous = entries[-1] if entries else None
    previous_time = (
        _created_at(previous.get("updated_at") or previous.get("created_at"))
        if previous
        else None
    )
    can_coalesce = bool(
        not had_redo_branch
        and key
        and previous
        and previous.get("kind") == "transaction"
        and previous.get("coalesce_key") == key
        and previous.get("actor") == actor_name
        and previous.get("operation") == operation_name
        and previous_time is not None
        and (now - previous_time).total_seconds() * 1000 <= window_ms
    )

    if can_coalesce:
        hid = str(previous["id"])
        after_name = str(
            previous.get("after_snapshot") or f"{hid}.after.json"
        )
        _write_snapshot(root, edit, after_name, clean_after)
        previous["after_snapshot"] = after_name
        previous["reason"] = reason_text
        previous["affected"] = (
            affected_items or list(previous.get("affected") or [])
        )
        previous["updated_at"] = now.isoformat()
        previous["coalesced_count"] = (
            int(previous.get("coalesced_count", 1)) + 1
        )
        entry = previous
        next_sequence = int(idx.get("next_sequence", 1))
    else:
        hid, next_sequence = _next_history_id(idx)
        before_name = f"{hid}.before.json"
        after_name = f"{hid}.after.json"
        _write_snapshot(root, edit, before_name, clean_before)
        _write_snapshot(root, edit, after_name, clean_after)
        entry = {
            "id": hid,
            "kind": "transaction",
            "reason": reason_text,
            "actor": actor_name,
            "operation": operation_name,
            "transaction_id": str(transaction_id or uuid4())[:160],
            "affected": affected_items,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "snapshot": before_name,
            "before_snapshot": before_name,
            "after_snapshot": after_name,
            "coalesce_key": key,
            "coalesced_count": 1,
        }
        entries.append(entry)

    idx = {
        **idx,
        "schema_version": HISTORY_SCHEMA_VERSION,
        "cursor": len(entries),
        "next_sequence": next_sequence,
        "entries": entries,
    }
    _write_index(root, edit, idx)
    save_timeline(root, clean_after)
    return {
        "transaction": entry,
        "checkpoint": entry,
        **history_status(root, edit),
    }


def undo_checkpoint(root: Path, edit_name: str = "teaser_30") -> dict:
    edit = slugify(edit_name)
    idx = _read_index(root, edit)
    cursor = int(idx["cursor"])
    if cursor <= 0:
        raise HistoryError("Aucun checkpoint à restaurer.")

    entry = idx["entries"][cursor - 1]
    before_name = entry.get("before_snapshot") or entry.get("snapshot")
    timeline = _read_snapshot(root, edit, before_name)

    # V0.14-V0.29 checkpoints did not store an after-state. Capture the
    # current persisted timeline the first time one is undone so Redo works.
    if not entry.get("after_snapshot"):
        current = load_timeline(root, edit)
        if isinstance(current, dict):
            clean_current = validate_timeline(root, current)
            after_name = f"{entry['id']}.redo.json"
            _write_snapshot(root, edit, after_name, clean_current)
            entry["after_snapshot"] = after_name

    save_timeline(root, timeline)
    idx["schema_version"] = HISTORY_SCHEMA_VERSION
    idx["cursor"] = cursor - 1
    _write_index(root, edit, idx)
    status = history_status(root, edit)
    return {
        "restored": entry,
        "undone": entry,
        "timeline": timeline,
        **status,
    }


def redo_checkpoint(root: Path, edit_name: str = "teaser_30") -> dict:
    edit = slugify(edit_name)
    idx = _read_index(root, edit)
    cursor = int(idx["cursor"])
    entries = idx["entries"]
    if cursor >= len(entries):
        raise HistoryError("Aucun checkpoint à rétablir.")

    entry = entries[cursor]
    after_name = entry.get("after_snapshot")
    if not after_name:
        raise HistoryError(
            "Redo indisponible pour ce checkpoint historique : "
            "état après édition absent."
        )

    timeline = _read_snapshot(root, edit, after_name)
    save_timeline(root, timeline)
    idx["schema_version"] = HISTORY_SCHEMA_VERSION
    idx["cursor"] = cursor + 1
    _write_index(root, edit, idx)
    status = history_status(root, edit)
    return {
        "redone": entry,
        "timeline": timeline,
        **status,
    }
