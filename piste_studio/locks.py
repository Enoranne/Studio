from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import json

from .config import read_yaml, write_yaml
from .db import connect

VALID_LEVELS = {"HARD", "SOFT", "OPEN"}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    decision: str
    reason: str


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def add_lock(root: Path, name: str, start: float, end: float, level: str,
             forbidden: Iterable[str] | None = None) -> dict:
    if start < 0 or end <= start:
        raise ValueError("Intervalle invalide : start >= 0 et end > start requis.")
    level = level.upper()
    if level not in VALID_LEVELS:
        raise ValueError(f"Niveau invalide : {level}")

    path = root / "locks.yaml"
    doc = read_yaml(path) or {"schema_version": 1, "locks": []}
    lock = {
        "name": name,
        "start": float(start),
        "end": float(end),
        "level": level,
        "forbidden": sorted(set(forbidden or [])),
    }
    doc.setdefault("locks", []).append(lock)
    write_yaml(path, doc)
    return lock


def _log(root: Path, action: str, decision: str, reason: str, payload: dict) -> None:
    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            "INSERT INTO audit_log(action, decision, reason, payload_json) VALUES (?, ?, ?, ?)",
            (action, decision, reason, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def check_operation(
    root: Path,
    operation: str,
    start: float | None = None,
    end: float | None = None,
    target: str | None = None,
    explicit_soft_unlock: bool = False,
) -> Decision:
    operation = operation.strip().lower()
    target = (target or "timeline").strip().lower()
    payload = {
        "operation": operation,
        "target": target,
        "start": start,
        "end": end,
        "explicit_soft_unlock": explicit_soft_unlock,
    }

    if target == "master":
        result = Decision(False, "BLOCKED", "Le MASTER est protégé et ne peut jamais être modifié par PISTE Studio.")
        _log(root, operation, result.decision, result.reason, payload)
        return result

    if start is None and end is None:
        result = Decision(True, "ALLOWED", "Aucune plage temporelle ciblée ; aucune collision de lock détectable.")
        _log(root, operation, result.decision, result.reason, payload)
        return result

    if start is None or end is None or start < 0 or end <= start:
        raise ValueError("Pour une opération temporelle, fournir start >= 0 et end > start.")

    doc = read_yaml(root / "locks.yaml")
    for lock in doc.get("locks", []):
        if not _overlap(float(start), float(end), float(lock["start"]), float(lock["end"])):
            continue

        level = str(lock.get("level", "OPEN")).upper()
        forbidden = {str(x).lower() for x in lock.get("forbidden", [])}
        op_is_forbidden = not forbidden or operation in forbidden

        if level == "HARD" and op_is_forbidden:
            result = Decision(
                False,
                "BLOCKED",
                f"Intersection avec HARD LOCK '{lock['name']}' [{lock['start']}s–{lock['end']}s].",
            )
            _log(root, operation, result.decision, result.reason, payload)
            return result

        if level == "SOFT" and op_is_forbidden and not explicit_soft_unlock:
            result = Decision(
                False,
                "REQUIRES_EXPLICIT_UNLOCK",
                f"Intersection avec SOFT LOCK '{lock['name']}'. Autorisation explicite requise.",
            )
            _log(root, operation, result.decision, result.reason, payload)
            return result

    result = Decision(True, "ALLOWED", "Aucun lock applicable ne bloque cette opération.")
    _log(root, operation, result.decision, result.reason, payload)
    return result
