from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from .config import read_yaml
from .timeline import load_timeline


FACETS = {"character", "prop", "decor", "look"}
SEMANTIC_OPERATIONS = {
    "semantic",
    "semantic_tag",
    "semantic_tag_accept",
    "tag",
}


class CanonConflictError(ValueError):
    pass


def _token(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    return re.sub(r"[\s_\-]+", "-", text).strip("-")


def normalize_semantic_tag(tag: str) -> tuple[str, str, str]:
    clean = str(tag or "").strip().lower()
    if ":" not in clean:
        raise CanonConflictError(
            "Tag sémantique structuré requis, ex. prop:fisher."
        )
    facet, value = clean.split(":", 1)
    facet = facet.strip().lower()
    value_token = _token(value)
    if facet not in FACETS or not value_token:
        raise CanonConflictError(
            "Facet invalide : character, prop, decor ou look."
        )
    return facet, value_token, f"{facet}:{value_token}"


def _structured_rule_tags(values: object) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return set()
    out: set[str] = set()
    for value in values:
        try:
            _facet, _token_value, normalized = normalize_semantic_tag(str(value))
        except CanonConflictError:
            continue
        out.add(normalized)
    return out


def canonical_semantic_index(canon: dict) -> dict:
    semantic = canon.get("semantic") or {}
    allowed = _structured_rule_tags(semantic.get("allowed_tags"))
    forbidden = _structured_rule_tags(semantic.get("forbidden_tags"))
    closed_facets = {
        str(value).strip().lower()
        for value in (semantic.get("closed_facets") or [])
        if str(value).strip().lower() in FACETS
    }
    sources: dict[str, list[str]] = {}

    def add(tag: str, source: str) -> None:
        allowed.add(tag)
        sources.setdefault(tag, []).append(source)

    for section, facet in (
        ("characters", "character"),
        ("props", "prop"),
        ("decors", "decor"),
    ):
        entries = canon.get(section) or {}
        if isinstance(entries, dict):
            for key in entries:
                value = _token(key)
                if value:
                    add(f"{facet}:{value}", f"canon.{section}.{key}")

    visual = canon.get("visual") or {}
    for value in visual.get("look") or []:
        token = _token(value)
        if token:
            add(f"look:{token}", f"canon.visual.look:{value}")
    for value in visual.get("avoid") or []:
        raw = str(value).strip()
        if ":" in raw:
            try:
                _facet, _value, normalized = normalize_semantic_tag(raw)
                forbidden.add(normalized)
                continue
            except CanonConflictError:
                pass
        token = _token(value)
        if token:
            forbidden.add(f"look:{token}")

    for tag in _structured_rule_tags(semantic.get("allowed_tags")):
        sources.setdefault(tag, []).append("canon.semantic.allowed_tags")
    forbidden_sources = {
        tag: ["canon.semantic.forbidden_tags"]
        for tag in _structured_rule_tags(semantic.get("forbidden_tags"))
    }
    for value in visual.get("avoid") or []:
        raw = str(value).strip()
        try:
            normalized = (
                normalize_semantic_tag(raw)[2]
                if ":" in raw
                else f"look:{_token(raw)}"
            )
        except CanonConflictError:
            continue
        if normalized:
            forbidden_sources.setdefault(
                normalized, []
            ).append(f"canon.visual.avoid:{value}")

    return {
        "allowed_tags": sorted(allowed),
        "forbidden_tags": sorted(forbidden),
        "closed_facets": sorted(closed_facets),
        "allowed_sources": sources,
        "forbidden_sources": forbidden_sources,
    }


def _semantic_lock_findings(
    root: Path,
    *,
    media_id: int,
    tag: str,
    edit_name: str,
    context_clip_id: str | None = None,
) -> list[dict]:
    timeline = load_timeline(root, edit_name) or {}
    if context_clip_id is not None:
        clips = [
            clip
            for clip in timeline.get("clips", [])
            if str(clip.get("id") or "") == str(context_clip_id)
        ]
    else:
        clips = [
            clip
            for clip in timeline.get("clips", [])
            if int(clip.get("mediaDbId") or -1) == int(media_id)
        ]
    if not clips:
        return []

    locks_doc = read_yaml(root / "locks.yaml") or {}
    findings: list[dict] = []
    exact_operation = f"tag:{tag}".lower()
    facet_operation = f"semantic:{tag.split(':', 1)[0]}".lower()
    for lock in locks_doc.get("locks", []):
        level = str(lock.get("level") or "OPEN").upper()
        if level not in {"HARD", "SOFT"}:
            continue
        forbidden = {
            str(value).strip().lower()
            for value in lock.get("forbidden", [])
        }
        semantic_applies = (
            not forbidden
            or bool(forbidden & SEMANTIC_OPERATIONS)
            or exact_operation in forbidden
            or facet_operation in forbidden
        )
        if not semantic_applies:
            continue
        lock_start = float(lock.get("start") or 0.0)
        lock_end = float(lock.get("end") or 0.0)
        for clip in clips:
            clip_start = float(clip.get("start") or 0.0)
            clip_end = clip_start + float(clip.get("duration") or 0.0)
            if max(lock_start, clip_start) >= min(lock_end, clip_end):
                continue
            findings.append({
                "kind": "HARD_LOCK" if level == "HARD" else "SOFT_LOCK",
                "severity": "BLOCKING" if level == "HARD" else "WARNING",
                "message": (
                    (
                        "La position du plan évalué intersecte "
                        if context_clip_id is not None
                        else "Le média est utilisé dans "
                    )
                    + f"{level} LOCK "
                    + f"« {lock.get('name') or 'zone'} » "
                    + f"[{lock_start:.2f}s–{lock_end:.2f}s] "
                    + "qui couvre les opérations sémantiques."
                ),
                "source": "locks.yaml",
                "lock_name": lock.get("name"),
                "lock_level": level,
                "clip_id": clip.get("id"),
                "range": [lock_start, lock_end],
            })
            break
    return findings


def assess_semantic_tag_against_canon(
    root: Path,
    *,
    media_id: int,
    tag: str,
    edit_name: str = "teaser_30",
    context_clip_id: str | None = None,
) -> dict:
    facet, value, normalized = normalize_semantic_tag(tag)
    canon = read_yaml(root / "canon.yaml") or {}
    index = canonical_semantic_index(canon)
    findings: list[dict] = []

    if normalized in index["forbidden_tags"]:
        findings.append({
            "kind": "CANON_CONFLICT",
            "severity": "BLOCKING",
            "message": f"« {normalized} » est explicitement interdit par le Canon.",
            "source": ", ".join(
                index["forbidden_sources"].get(normalized)
                or ["canon.semantic.forbidden_tags"]
            ),
        })
    elif normalized in index["allowed_tags"]:
        findings.append({
            "kind": "CANON_ALIGNMENT",
            "severity": "INFO",
            "message": f"« {normalized} » correspond à une entrée explicite du Canon.",
            "source": ", ".join(
                index["allowed_sources"].get(normalized)
                or ["canon.semantic.allowed_tags"]
            ),
        })
    elif facet in index["closed_facets"]:
        known = [
            item for item in index["allowed_tags"]
            if item.startswith(f"{facet}:")
        ]
        findings.append({
            "kind": "CANON_CONFLICT",
            "severity": "BLOCKING",
            "message": (
                f"Le facet « {facet} » est fermé dans le Canon et "
                f"« {normalized} » n’appartient pas à sa liste autorisée."
            ),
            "source": "canon.semantic.closed_facets",
            "allowed_for_facet": known,
        })
    else:
        findings.append({
            "kind": "CANON_UNVERIFIED",
            "severity": "INFO",
            "message": (
                f"Le Canon ne confirme ni n’interdit explicitement "
                f"« {normalized} »."
            ),
            "source": "canon.yaml",
        })

    findings.extend(
        _semantic_lock_findings(
            root,
            media_id=media_id,
            tag=normalized,
            edit_name=edit_name,
            context_clip_id=context_clip_id,
        )
    )

    blocking = [
        item for item in findings
        if item.get("severity") == "BLOCKING"
    ]
    warnings = [
        item for item in findings
        if item.get("severity") == "WARNING"
    ]
    has_conflict = any(
        item.get("kind") == "CANON_CONFLICT"
        for item in findings
    )
    has_hard_lock = any(
        item.get("kind") == "HARD_LOCK"
        for item in findings
    )
    has_alignment = any(
        item.get("kind") == "CANON_ALIGNMENT"
        for item in findings
    )
    if has_conflict:
        status = "CONFLICT"
    elif has_hard_lock:
        status = "HARD_LOCK"
    elif warnings:
        status = "REVIEW"
    elif has_alignment:
        status = "ALIGNED"
    else:
        status = "UNVERIFIED"

    return {
        "status": status,
        "tag": normalized,
        "facet": facet,
        "value": value,
        "requires_explicit_acknowledgement": bool(blocking),
        "findings": findings,
        "canon_index": {
            "closed_facets": index["closed_facets"],
            "known_allowed_for_facet": [
                item for item in index["allowed_tags"]
                if item.startswith(f"{facet}:")
            ],
        },
        "policy": {
            "absence_is_not_conflict": True,
            "automatic_rejection": False,
            "automatic_acceptance": False,
            "hard_lock_never_silently_overridden": True,
        },
    }
