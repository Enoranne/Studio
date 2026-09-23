from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .db import connect
from .metadata import fetch_media_with_metadata


RANGE_KINDS = {"favorite", "reject"}
MARKER_KINDS = {"note", "decision", "beat", "warning"}


def _validate_range(source_in: float, source_out: float) -> tuple[float, float]:
    start = float(source_in)
    end = float(source_out)
    if start < 0 or end <= start:
        raise ValueError("Plage éditoriale invalide.")
    return round(start, 6), round(end, 6)


def list_editorial_ranges(root: Path, media_id: int | None = None) -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        if media_id is None:
            rows = conn.execute(
                "SELECT * FROM editorial_ranges ORDER BY media_id, source_in, id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM editorial_ranges WHERE media_id=? "
                "ORDER BY source_in, id",
                (int(media_id),),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def set_editorial_range(
    root: Path,
    media_id: int,
    *,
    kind: str,
    source_in: float,
    source_out: float,
    note: str | None = None,
) -> dict:
    kind = str(kind).strip().lower()
    if kind not in RANGE_KINDS:
        raise ValueError("kind doit être favorite ou reject.")
    start, end = _validate_range(source_in, source_out)

    conn = connect(root / "media.sqlite")
    try:
        media = conn.execute(
            "SELECT id FROM media WHERE id=?", (int(media_id),)
        ).fetchone()
        if media is None:
            raise ValueError(f"Média introuvable : id={media_id}")

        duration = conn.execute(
            "SELECT duration_seconds FROM media_metadata WHERE media_id=?",
            (int(media_id),),
        ).fetchone()
        if (
            duration
            and duration["duration_seconds"] is not None
            and end > float(duration["duration_seconds"]) + 1e-6
        ):
            raise ValueError("La plage éditoriale dépasse la durée du média.")

        opposite = "reject" if kind == "favorite" else "favorite"
        conn.execute(
            """
            DELETE FROM editorial_ranges
            WHERE media_id=? AND kind=?
              AND MAX(source_in, ?) < MIN(source_out, ?)
            """,
            (int(media_id), opposite, start, end),
        )
        conn.execute(
            """
            INSERT INTO editorial_ranges(media_id, kind, source_in, source_out, note)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(media_id, kind, source_in, source_out) DO UPDATE SET
              note=excluded.note,
              updated_at=CURRENT_TIMESTAMP
            """,
            (int(media_id), kind, start, end, note),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT * FROM editorial_ranges
            WHERE media_id=? AND kind=? AND source_in=? AND source_out=?
            """,
            (int(media_id), kind, start, end),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def delete_editorial_range(root: Path, range_id: int) -> bool:
    conn = connect(root / "media.sqlite")
    try:
        cur = conn.execute(
            "DELETE FROM editorial_ranges WHERE id=?", (int(range_id),)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_markers(root: Path, edit_name: str = "teaser_30") -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            """
            SELECT * FROM editorial_markers
            WHERE edit_name=?
            ORDER BY time_seconds, id
            """,
            (str(edit_name),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_marker(
    root: Path,
    *,
    edit_name: str,
    time_seconds: float,
    label: str,
    kind: str = "note",
    note: str | None = None,
    media_id: int | None = None,
) -> dict:
    time_seconds = float(time_seconds)
    if time_seconds < 0:
        raise ValueError("time_seconds doit être >= 0.")
    label = str(label).strip()
    if not label:
        raise ValueError("Le marqueur doit avoir un libellé.")
    kind = str(kind or "note").strip().lower()
    if kind not in MARKER_KINDS:
        raise ValueError(
            "kind doit être note, decision, beat ou warning."
        )

    conn = connect(root / "media.sqlite")
    try:
        if media_id is not None:
            row = conn.execute(
                "SELECT id FROM media WHERE id=?", (int(media_id),)
            ).fetchone()
            if row is None:
                raise ValueError(f"Média introuvable : id={media_id}")
        cur = conn.execute(
            """
            INSERT INTO editorial_markers(
              edit_name, time_seconds, kind, label, note, media_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(edit_name),
                round(time_seconds, 6),
                kind,
                label,
                note,
                int(media_id) if media_id is not None else None,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM editorial_markers WHERE id=?",
            (cur.lastrowid,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def delete_marker(root: Path, marker_id: int) -> bool:
    conn = connect(root / "media.sqlite")
    try:
        cur = conn.execute(
            "DELETE FROM editorial_markers WHERE id=?", (int(marker_id),)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _tag_set(item: dict) -> set[str]:
    return {
        str(tag).strip().lower()
        for tag in (item.get("tags") or [])
        if str(tag).strip()
    }


def _ranges_by_media(ranges: Iterable[dict]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for row in ranges:
        out.setdefault(int(row["media_id"]), []).append(dict(row))
    return out


def suggest_alternatives(
    root: Path,
    media_id: int,
    *,
    limit: int = 5,
    max_spoiler: int | None = None,
) -> dict:
    items = fetch_media_with_metadata(root)
    by_id = {int(item["id"]): item for item in items}
    reference = by_id.get(int(media_id))
    if reference is None:
        raise ValueError(f"Média introuvable : id={media_id}")
    if reference.get("kind") != "video":
        raise ValueError("Le Source Selector travaille sur les médias vidéo.")

    ranges = _ranges_by_media(list_editorial_ranges(root))
    ref_tags = _tag_set(reference)
    ref_spoiler = int(reference.get("spoiler_level") or 0)
    if max_spoiler is None:
        max_spoiler = ref_spoiler
    max_spoiler = int(max_spoiler)
    if not 0 <= max_spoiler <= 3:
        raise ValueError("max_spoiler doit être compris entre 0 et 3.")

    suggestions: list[dict] = []
    for item in items:
        item_id = int(item["id"])
        if item_id == int(media_id) or item.get("kind") != "video":
            continue
        spoiler = int(item.get("spoiler_level") or 0)
        if spoiler > max_spoiler:
            continue

        item_ranges = ranges.get(item_id, [])
        favorites = [r for r in item_ranges if r["kind"] == "favorite"]
        rejects = [r for r in item_ranges if r["kind"] == "reject"]
        tags = _tag_set(item)
        shared = sorted(ref_tags & tags)

        score = 0.0
        reasons: list[str] = []
        if shared:
            score += min(5, len(shared)) * 2.0
            reasons.append("Tags communs : " + ", ".join(shared[:5]))
        if bool(item.get("canonical")):
            score += 4.0
            reasons.append("Média canonique")
        if bool(item.get("trailer_safe")):
            score += 2.0
            reasons.append("Trailer-safe")
        rating = int(item.get("rating") or 0)
        if rating:
            score += rating * 0.75
            reasons.append(f"Rating {rating}/5")
        if favorites:
            score += 4.5
            reasons.append("Contient une plage Favorite")
        if rejects and not favorites:
            score -= 3.0
            reasons.append("Contient une plage Reject")
        if spoiler == ref_spoiler:
            score += 1.0
            reasons.append("Même niveau de spoiler")
        elif spoiler < ref_spoiler:
            score += 1.5
            reasons.append("Niveau de spoiler plus faible")
        if item.get("status") in {"APPROVED", "CANONICAL", "SAFETY"}:
            score += 1.5
            reasons.append(f"Statut {item['status']}")

        if not reasons:
            reasons.append("Alternative vidéo disponible")

        if favorites:
            best = sorted(
                favorites,
                key=lambda r: (
                    -(float(r["source_out"]) - float(r["source_in"])),
                    float(r["source_in"]),
                ),
            )[0]
            source_in = float(best["source_in"])
            source_out = float(best["source_out"])
            range_reason = "Plage Favorite persistée"
        else:
            duration = float(item.get("duration_seconds") or 0)
            source_in = 0.0
            source_out = min(duration, 5.0) if duration > 0 else 5.0
            range_reason = "Fenêtre de prévisualisation par défaut"

        suggestions.append(
            {
                "media_id": item_id,
                "title": item.get("title") or Path(item["relative_path"]).stem,
                "relative_path": item["relative_path"],
                "score": round(score, 3),
                "reasons": reasons,
                "source_in": round(source_in, 3),
                "source_out": round(source_out, 3),
                "range_reason": range_reason,
                "canonical": bool(item.get("canonical")),
                "trailer_safe": bool(item.get("trailer_safe")),
                "spoiler_level": spoiler,
                "rating": rating,
                "tags": sorted(tags),
            }
        )

    suggestions.sort(
        key=lambda x: (-x["score"], x["spoiler_level"], x["media_id"])
    )
    return {
        "reference_media_id": int(media_id),
        "max_spoiler": max_spoiler,
        "policy": {
            "human_validation_required": True,
            "automatic_replacement": False,
            "ranking_signals": [
                "shared_tags",
                "canonical",
                "trailer_safe",
                "rating",
                "favorite_ranges",
                "reject_ranges",
                "spoiler_level",
                "status",
            ],
        },
        "suggestions": suggestions[: max(1, min(int(limit), 20))],
    }
