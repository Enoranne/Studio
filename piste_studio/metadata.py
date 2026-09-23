from __future__ import annotations

from pathlib import Path
import json

from .db import connect


def set_media_metadata(
    root: Path,
    media_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    duration_seconds: float | None = None,
    rating: int | None = None,
    tags: list[str] | None = None,
) -> None:
    if duration_seconds is not None and duration_seconds < 0:
        raise ValueError("duration_seconds doit être positif ou nul.")
    if rating is not None and not 0 <= rating <= 5:
        raise ValueError("rating doit être compris entre 0 et 5.")

    conn = connect(root / "media.sqlite")
    try:
        media = conn.execute("SELECT id FROM media WHERE id=?", (media_id,)).fetchone()
        if media is None:
            raise ValueError(f"Média introuvable : id={media_id}")

        current = conn.execute(
            "SELECT * FROM media_metadata WHERE media_id=?", (media_id,)
        ).fetchone()

        values = {
            "title": current["title"] if current else None,
            "description": current["description"] if current else None,
            "duration_seconds": current["duration_seconds"] if current else None,
            "rating": current["rating"] if current else 0,
            "tags_json": current["tags_json"] if current else "[]",
        }
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if duration_seconds is not None:
            values["duration_seconds"] = float(duration_seconds)
        if rating is not None:
            values["rating"] = int(rating)
        if tags is not None:
            clean = sorted({t.strip().lower() for t in tags if t.strip()})
            values["tags_json"] = json.dumps(clean, ensure_ascii=False)

        conn.execute(
            """
            INSERT INTO media_metadata(media_id, title, description, duration_seconds, rating, tags_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(media_id) DO UPDATE SET
              title=excluded.title,
              description=excluded.description,
              duration_seconds=excluded.duration_seconds,
              rating=excluded.rating,
              tags_json=excluded.tags_json,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                media_id,
                values["title"],
                values["description"],
                values["duration_seconds"],
                values["rating"],
                values["tags_json"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_media_with_metadata(root: Path) -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            """
            SELECT m.*, mm.title, mm.description, mm.duration_seconds,
                   COALESCE(mm.rating, 0) AS rating,
                   COALESCE(mm.tags_json, '[]') AS tags_json
            FROM media m
            LEFT JOIN media_metadata mm ON mm.media_id = m.id
            ORDER BY m.id
            """
        ).fetchall()
    finally:
        conn.close()

    out: list[dict] = []
    for row in rows:
        d = dict(row)
        try:
            d["tags"] = json.loads(d.pop("tags_json"))
        except Exception:
            d["tags"] = []
        out.append(d)
    return out
