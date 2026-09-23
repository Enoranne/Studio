from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from .db import connect
from .versioning import slugify


class TimelineError(ValueError):
    pass


def working_timeline_path(root: Path, edit_name: str = "teaser_30") -> Path:
    edit = slugify(edit_name)
    return root / "edits" / edit / "working" / "timeline.json"


def load_timeline(root: Path, edit_name: str = "teaser_30") -> dict | None:
    path = working_timeline_path(root, edit_name)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def _media_duration_map(root: Path) -> dict[int, float | None]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            "SELECT m.id, mm.duration_seconds FROM media m "
            "LEFT JOIN media_metadata mm ON mm.media_id=m.id"
        ).fetchall()
        return {
            int(r["id"]): (
                float(r["duration_seconds"])
                if r["duration_seconds"] is not None
                else None
            )
            for r in rows
        }
    finally:
        conn.close()


def _clean_storyline(payload: dict) -> dict:
    raw = payload.get("storyline") or {}
    mode = str(raw.get("mode") or "free").strip().lower()
    if mode not in {"free", "magnetic"}:
        raise TimelineError("storyline.mode doit être free ou magnetic.")
    start = float(raw.get("start", 0) or 0)
    if start < 0:
        raise TimelineError("storyline.start doit être >= 0.")
    return {"mode": mode, "start": round(start, 6)}


def _validate_connections(clean_clips: list[dict]) -> None:
    by_id = {c["id"]: c for c in clean_clips}
    for child in clean_clips:
        parent_id = child.get("parentClipId")
        if not parent_id:
            child.pop("anchorOffset", None)
            child.pop("connectionMode", None)
            continue
        parent = by_id.get(str(parent_id))
        if parent is None:
            raise TimelineError(
                f"Parent de connexion introuvable pour {child['id']}: {parent_id}"
            )
        if child["track"] == "video":
            raise TimelineError(
                f"Un clip STORY ne peut pas être connecté comme enfant: {child['id']}"
            )
        if parent["track"] != "video":
            raise TimelineError(
                f"Le parent de {child['id']} doit appartenir à la STORYLINE."
            )
        mode = str(child.get("connectionMode") or "follow").strip().lower()
        if mode != "follow":
            raise TimelineError(
                f"connectionMode invalide pour {child['id']}: {mode}"
            )
        offset = child.get("anchorOffset")
        if offset is None:
            offset = float(child["start"]) - float(parent["start"])
        offset = float(offset)
        expected = float(parent["start"]) + offset
        if abs(float(child["start"]) - expected) > 1e-4:
            raise TimelineError(
                f"Connexion incohérente pour {child['id']}: "
                f"start={child['start']} mais parent+offset={expected:.6f}"
            )
        child["parentClipId"] = parent["id"]
        child["anchorOffset"] = round(offset, 6)
        child["connectionMode"] = "follow"


def _validate_magnetic_storyline(clean_clips: list[dict], storyline: dict) -> None:
    if storyline["mode"] != "magnetic":
        return
    story = sorted(
        (c for c in clean_clips if c["track"] == "video"),
        key=lambda c: (c["start"], c["id"]),
    )
    cursor = float(storyline["start"])
    for clip in story:
        if abs(float(clip["start"]) - cursor) > 1e-4:
            raise TimelineError(
                f"Storyline magnétique non contiguë à {clip['id']}: "
                f"{clip['start']} au lieu de {cursor:.6f}"
            )
        cursor += float(clip["duration"])


def validate_timeline(root: Path, payload: dict) -> dict:
    duration = float(payload.get("duration_seconds", 0))
    if duration <= 0 or duration > 3600:
        raise TimelineError("duration_seconds doit être > 0 et <= 3600.")

    tracks = payload.get("tracks")
    clips = payload.get("clips")
    if not isinstance(tracks, list) or not tracks:
        raise TimelineError("La timeline doit contenir au moins une piste.")
    if not isinstance(clips, list):
        raise TimelineError("clips doit être une liste.")

    storyline = _clean_storyline(payload)
    if storyline["start"] > duration:
        raise TimelineError("storyline.start dépasse la durée de la timeline.")

    track_ids: set[str] = set()
    clean_tracks: list[dict] = []
    for t in tracks:
        tid = str(t.get("id", "")).strip()
        if not tid or tid in track_ids:
            raise TimelineError("Identifiants de pistes invalides ou dupliqués.")
        track_ids.add(tid)
        clean_tracks.append(
            {
                "id": tid,
                "name": str(t.get("name") or tid).strip(),
                "kind": str(t.get("kind") or "generic").strip(),
                "muted": bool(t.get("muted", False)),
                "locked": bool(t.get("locked", False)),
            }
        )

    durations = _media_duration_map(root)
    clip_ids: set[str] = set()
    clean_clips: list[dict] = []
    for c in clips:
        cid = str(c.get("id", "")).strip()
        if not cid or cid in clip_ids:
            raise TimelineError("Identifiants de clips invalides ou dupliqués.")
        clip_ids.add(cid)
        track = str(c.get("track", "")).strip()
        if track not in track_ids:
            raise TimelineError(f"Piste inconnue pour {cid}: {track}")

        start = float(c.get("start", 0))
        clip_duration = float(c.get("duration", 0))
        if (
            start < 0
            or clip_duration <= 0
            or start + clip_duration > duration + 1e-6
        ):
            raise TimelineError(f"Plage temporelle invalide pour {cid}.")

        source_start = float(c.get("sourceStart", 0) or 0)
        if source_start < 0:
            raise TimelineError(f"sourceStart invalide pour {cid}.")

        media_db_id = c.get("mediaDbId") or c.get("audioDbId")
        if media_db_id is not None:
            media_db_id = int(media_db_id)
            if media_db_id not in durations:
                raise TimelineError(
                    f"Média catalogue introuvable pour {cid}: {media_db_id}"
                )
            src_duration = durations[media_db_id]
            if (
                src_duration is not None
                and source_start + clip_duration > src_duration + 1e-6
            ):
                raise TimelineError(
                    f"{cid} dépasse la durée de sa source média."
                )

        gain = float(c.get("gain", 1) if c.get("gain") is not None else 1)
        fade_in = float(c.get("fadeIn", 0) or 0)
        fade_out = float(c.get("fadeOut", 0) or 0)
        if gain < 0 or gain > 1:
            raise TimelineError(f"Gain hors plage 0..1 pour {cid}.")
        if (
            fade_in < 0
            or fade_out < 0
            or fade_in + fade_out > clip_duration + 1e-6
        ):
            raise TimelineError(f"Fades invalides pour {cid}.")

        clean = dict(c)
        clean.update(
            {
                "id": cid,
                "track": track,
                "start": round(start, 6),
                "duration": round(clip_duration, 6),
                "sourceStart": round(source_start, 6),
            }
        )
        if media_db_id is not None:
            if c.get("mediaDbId") is not None:
                clean["mediaDbId"] = media_db_id
            if c.get("audioDbId") is not None:
                clean["audioDbId"] = media_db_id
        clean_clips.append(clean)

    _validate_connections(clean_clips)
    _validate_magnetic_storyline(clean_clips, storyline)

    by_track: dict[str, list[dict]] = {}
    for c in clean_clips:
        by_track.setdefault(c["track"], []).append(c)
    for tid, items in by_track.items():
        items.sort(key=lambda x: (x["start"], x["id"]))
        for a, b in zip(items, items[1:]):
            if _overlap(
                a["start"],
                a["start"] + a["duration"],
                b["start"],
                b["start"] + b["duration"],
            ):
                raise TimelineError(
                    f"Collision sur la piste {tid}: {a['id']} / {b['id']}"
                )

    return {
        "schema_version": 2,
        "edit_name": slugify(str(payload.get("edit_name") or "teaser_30")),
        "duration_seconds": duration,
        "storyline": storyline,
        "tracks": clean_tracks,
        "clips": clean_clips,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_timeline(root: Path, payload: dict) -> Path:
    doc = validate_timeline(root, payload)
    path = working_timeline_path(root, doc["edit_name"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
    return path
