from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import math

from .db import connect
from .timebase import seconds_to_ticks, ticks_to_seconds
from .versioning import slugify


class TimelineError(ValueError):
    pass


AUDIO_ROLES = {"dialogue", "vo", "music", "ambience", "sfx"}
TITLE_FONT_FAMILIES = {"sans", "serif", "mono"}
TITLE_ALIGNS = {"left", "center", "right"}
TITLE_PRESETS = {"center", "lower_third", "top", "custom"}
TITLE_ROLES = {"overlay", "final_card"}


def _clean_hex_color(value: object, fallback: str, field: str) -> str:
    clean = str(value or fallback).strip()
    if len(clean) != 7 or not clean.startswith("#"):
        raise TimelineError(f"{field} doit utiliser #RRGGBB.")
    try:
        int(clean[1:], 16)
    except ValueError as exc:
        raise TimelineError(f"{field} doit utiliser #RRGGBB.") from exc
    return clean.upper()


def _clean_title_clip(raw: dict, cid: str, clip_duration: float) -> dict:
    text = str(raw.get("text") or raw.get("label") or "").strip()
    if not text:
        raise TimelineError(f"Texte de titre vide pour {cid}.")
    if len(text) > 500:
        raise TimelineError(f"Texte de titre trop long pour {cid} (500 caractères max).")

    preset = str(raw.get("titlePreset") or "center").strip().lower()
    if preset not in TITLE_PRESETS:
        raise TimelineError(f"titlePreset invalide pour {cid}.")
    family = str(raw.get("fontFamily") or "sans").strip().lower()
    if family not in TITLE_FONT_FAMILIES:
        raise TimelineError(f"fontFamily invalide pour {cid}.")
    align = str(raw.get("textAlign") or "center").strip().lower()
    if align not in TITLE_ALIGNS:
        raise TimelineError(f"textAlign invalide pour {cid}.")

    role = str(raw.get("titleRole") or "overlay").strip().lower()
    if role not in TITLE_ROLES:
        raise TimelineError(f"titleRole invalide pour {cid}.")

    defaults = {
        "center": (0.5, 0.5),
        "lower_third": (0.5, 0.82),
        "top": (0.5, 0.16),
        "custom": (0.5, 0.5),
    }
    default_x, default_y = defaults[preset]
    x = float(raw.get("positionX", default_x))
    y = float(raw.get("positionY", default_y))
    width = float(raw.get("boxWidth", 0.8))
    size = float(raw.get("fontSize", 64))
    weight = int(raw.get("fontWeight", 700))
    opacity = float(raw.get("opacity", 1.0))
    background_opacity = float(raw.get("backgroundOpacity", 0.0))
    padding = float(raw.get("padding", 0.02))
    corner_radius = float(raw.get("cornerRadius", 0.0))
    canvas_background_opacity = float(
        raw.get("canvasBackgroundOpacity", 1.0 if role == "final_card" else 0.0)
    )
    black_tail = float(raw.get("blackTailSeconds", 0.0))

    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise TimelineError(f"positionX/positionY hors plage 0..1 pour {cid}.")
    if not 0.1 <= width <= 1:
        raise TimelineError(f"boxWidth hors plage 0.1..1 pour {cid}.")
    if not 12 <= size <= 240:
        raise TimelineError(f"fontSize hors plage 12..240 pour {cid}.")
    if not 100 <= weight <= 900 or weight % 100:
        raise TimelineError(f"fontWeight doit être 100..900 par pas de 100 pour {cid}.")
    if not 0 <= opacity <= 1:
        raise TimelineError(f"opacity hors plage 0..1 pour {cid}.")
    if not 0 <= background_opacity <= 1:
        raise TimelineError(f"backgroundOpacity hors plage 0..1 pour {cid}.")
    if not 0 <= padding <= 0.2:
        raise TimelineError(f"padding hors plage 0..0.2 pour {cid}.")
    if not 0 <= corner_radius <= 0.2:
        raise TimelineError(f"cornerRadius hors plage 0..0.2 pour {cid}.")
    if not 0 <= canvas_background_opacity <= 1:
        raise TimelineError(
            f"canvasBackgroundOpacity hors plage 0..1 pour {cid}."
        )
    if black_tail < 0 or black_tail >= clip_duration:
        raise TimelineError(
            f"blackTailSeconds doit être >= 0 et < durée du clip pour {cid}."
        )

    return {
        "text": text,
        "titlePreset": preset,
        "fontFamily": family,
        "fontSize": round(size, 2),
        "fontWeight": weight,
        "textAlign": align,
        "positionX": round(x, 4),
        "positionY": round(y, 4),
        "boxWidth": round(width, 4),
        "color": _clean_hex_color(raw.get("color"), "#FFFFFF", "color"),
        "backgroundColor": _clean_hex_color(
            raw.get("backgroundColor"), "#000000", "backgroundColor"
        ),
        "backgroundOpacity": round(background_opacity, 4),
        "opacity": round(opacity, 4),
        "padding": round(padding, 4),
        "cornerRadius": round(corner_radius, 4),
        "titleRole": role,
        "canvasBackgroundColor": _clean_hex_color(
            raw.get("canvasBackgroundColor"),
            "#000000",
            "canvasBackgroundColor",
        ),
        "canvasBackgroundOpacity": round(canvas_background_opacity, 4),
        "blackTailSeconds": round(black_tail, 4),
    }


def _linear_to_db(value: float) -> float:
    value = float(value)
    if value <= 0:
        return -60.0
    return max(-60.0, min(12.0, 20.0 * math.log10(value)))


def _db_to_linear(value: float) -> float:
    value = max(-60.0, min(12.0, float(value)))
    return 10.0 ** (value / 20.0)


def _clean_volume_envelope(raw: object, clip_duration: float, cid: str) -> list[dict]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise TimelineError(f"volumeEnvelope doit être une liste pour {cid}.")
    points: list[dict] = []
    seen: set[float] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise TimelineError(f"Point d’enveloppe invalide pour {cid}.")
        time = round(float(item.get("time", 0)), 6)
        gain_db = round(float(item.get("gainDb", 0)), 3)
        if time < 0 or time > clip_duration + 1e-6:
            raise TimelineError(f"Point d’enveloppe hors clip pour {cid}.")
        if gain_db < -60 or gain_db > 12:
            raise TimelineError(f"Gain d’enveloppe hors plage -60..12 dB pour {cid}.")
        if time in seen:
            raise TimelineError(f"Deux points d’enveloppe au même instant pour {cid}.")
        seen.add(time)
        points.append({"time": time, "gainDb": gain_db})
    points.sort(key=lambda x: x["time"])
    return points


def working_timeline_path(root: Path, edit_name: str = "teaser_30") -> Path:
    edit = slugify(edit_name)
    return root / "edits" / edit / "working" / "timeline.json"


def load_timeline(root: Path, edit_name: str = "teaser_30") -> dict | None:
    path = working_timeline_path(root, edit_name)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
    return max(
        seconds_to_ticks(a_start),
        seconds_to_ticks(b_start),
    ) < min(
        seconds_to_ticks(a_end),
        seconds_to_ticks(b_end),
    )


def _crossfade_overlap_allowed(a: dict, b: dict) -> bool:
    if (
        a.get("audioDbId") is None
        and a.get("audioId") is None
    ) or (
        b.get("audioDbId") is None
        and b.get("audioId") is None
    ):
        return False
    if str(a.get("crossfadeWith") or "") != str(b.get("id") or ""):
        return False
    if str(b.get("crossfadeWith") or "") != str(a.get("id") or ""):
        return False
    try:
        da = float(a.get("crossfadeDuration") or 0)
        db = float(b.get("crossfadeDuration") or 0)
    except (TypeError, ValueError):
        return False
    if da <= 0 or db <= 0 or abs(da - db) > 1e-4:
        return False
    overlap = min(
        float(a["start"]) + float(a["duration"]),
        float(b["start"]) + float(b["duration"]),
    ) - max(float(a["start"]), float(b["start"]))
    return overlap > 0 and overlap <= da + 1e-4


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
    start_ticks = seconds_to_ticks(raw.get("start", 0) or 0)
    if start_ticks < 0:
        raise TimelineError("storyline.start doit être >= 0.")
    return {"mode": mode, "start": ticks_to_seconds(start_ticks)}


def _validate_connections(clean_clips: list[dict]) -> None:
    by_id = {c["id"]: c for c in clean_clips}
    for child in clean_clips:
        parent_id = child.get("parentClipId")
        if not parent_id:
            child.pop("anchorOffset", None)
            child.pop("connectionPointOffset", None)
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
        parent_start = seconds_to_ticks(parent["start"])
        parent_duration = seconds_to_ticks(parent["duration"])
        offset = child.get("anchorOffset")
        if offset is None:
            offset_ticks = seconds_to_ticks(child["start"]) - parent_start
        else:
            offset_ticks = seconds_to_ticks(offset)
        expected = parent_start + offset_ticks
        child_start = seconds_to_ticks(child["start"])
        if child_start != expected:
            raise TimelineError(
                f"Connexion incohérente pour {child['id']}: "
                f"start={child['start']} mais parent+offset="
                f"{ticks_to_seconds(expected):.6f}"
            )
        point_offset = child.get("connectionPointOffset")
        if point_offset is None:
            point_offset_ticks = min(
                max(offset_ticks, 0),
                parent_duration,
            )
        else:
            point_offset_ticks = seconds_to_ticks(point_offset)
        if point_offset_ticks < 0 or point_offset_ticks > parent_duration:
            raise TimelineError(
                f"connectionPointOffset hors plan parent pour {child['id']}."
            )

        child["parentClipId"] = parent["id"]
        child["anchorOffset"] = ticks_to_seconds(offset_ticks)
        child["connectionPointOffset"] = ticks_to_seconds(
            min(max(point_offset_ticks, 0), parent_duration)
        )
        child["connectionMode"] = "follow"


def _validate_magnetic_storyline(clean_clips: list[dict], storyline: dict) -> None:
    if storyline["mode"] != "magnetic":
        return
    story = sorted(
        (c for c in clean_clips if c["track"] == "video"),
        key=lambda c: (c["start"], c["id"]),
    )
    cursor = seconds_to_ticks(storyline["start"])
    for clip in story:
        clip_start = seconds_to_ticks(clip["start"])
        if clip_start != cursor:
            raise TimelineError(
                f"Storyline magnétique non contiguë à {clip['id']}: "
                f"{clip['start']} au lieu de {ticks_to_seconds(cursor):.6f}"
            )
        cursor += seconds_to_ticks(clip["duration"])


def validate_timeline(root: Path, payload: dict) -> dict:
    timeline_duration_ticks = seconds_to_ticks(
        payload.get("duration_seconds", 0)
    )
    if (
        timeline_duration_ticks <= 0
        or timeline_duration_ticks > seconds_to_ticks(3600)
    ):
        raise TimelineError("duration_seconds doit être > 0 et <= 3600.")
    duration = ticks_to_seconds(timeline_duration_ticks)

    tracks = payload.get("tracks")
    clips = payload.get("clips")
    if not isinstance(tracks, list) or not tracks:
        raise TimelineError("La timeline doit contenir au moins une piste.")
    if not isinstance(clips, list):
        raise TimelineError("clips doit être une liste.")

    storyline = _clean_storyline(payload)
    if seconds_to_ticks(storyline["start"]) > timeline_duration_ticks:
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
                "solo": bool(t.get("solo", False)),
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

        start_ticks = seconds_to_ticks(c.get("start", 0))
        clip_duration_ticks = seconds_to_ticks(c.get("duration", 0))
        if (
            start_ticks < 0
            or clip_duration_ticks <= 0
            or start_ticks + clip_duration_ticks > timeline_duration_ticks
        ):
            raise TimelineError(f"Plage temporelle invalide pour {cid}.")
        start = ticks_to_seconds(start_ticks)
        clip_duration = ticks_to_seconds(clip_duration_ticks)

        source_start_ticks = seconds_to_ticks(c.get("sourceStart", 0) or 0)
        if source_start_ticks < 0:
            raise TimelineError(f"sourceStart invalide pour {cid}.")
        source_start = ticks_to_seconds(source_start_ticks)

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
                and source_start_ticks + clip_duration_ticks
                > seconds_to_ticks(src_duration)
            ):
                raise TimelineError(
                    f"{cid} dépasse la durée de sa source média."
                )

        gain = float(c.get("gain", 1) if c.get("gain") is not None else 1)
        gain_db = (
            float(c["gainDb"])
            if c.get("gainDb") is not None
            else _linear_to_db(gain)
        )
        pan = float(c.get("pan", 0) or 0)
        fade_in = float(c.get("fadeIn", 0) or 0)
        fade_out = float(c.get("fadeOut", 0) or 0)
        role = str(
            c.get("audioRole")
            or (
                track
                if track in AUDIO_ROLES
                else "sfx"
            )
        ).strip().lower()
        if gain_db < -60 or gain_db > 12:
            raise TimelineError(f"Gain hors plage -60..12 dB pour {cid}.")
        if pan < -1 or pan > 1:
            raise TimelineError(f"Pan hors plage -1..1 pour {cid}.")
        if (
            fade_in < 0
            or fade_out < 0
            or fade_in + fade_out > clip_duration + 1e-6
        ):
            raise TimelineError(f"Fades invalides pour {cid}.")
        if c.get("audioDbId") is not None or c.get("audioId") is not None:
            if role not in AUDIO_ROLES:
                raise TimelineError(
                    f"Rôle audio invalide pour {cid}: {role}"
                )
            volume_envelope = _clean_volume_envelope(
                c.get("volumeEnvelope"),
                clip_duration,
                cid,
            )
        else:
            volume_envelope = []

        clean = dict(c)
        clean.update(
            {
                "id": cid,
                "track": track,
                "start": start,
                "duration": clip_duration,
                "sourceStart": source_start,
            }
        )
        if media_db_id is not None:
            if c.get("mediaDbId") is not None:
                clean["mediaDbId"] = media_db_id
            if c.get("audioDbId") is not None:
                clean["audioDbId"] = media_db_id
        if c.get("audioDbId") is not None or c.get("audioId") is not None:
            clean["gainDb"] = round(gain_db, 3)
            clean["gain"] = round(_db_to_linear(gain_db), 6)
            clean["pan"] = round(pan, 4)
            clean["audioRole"] = role
            clean["fadeIn"] = round(fade_in, 6)
            clean["fadeOut"] = round(fade_out, 6)
            clean["volumeEnvelope"] = volume_envelope
        if str(track).lower() == "titles" or str(
            next((t["kind"] for t in clean_tracks if t["id"] == track), "")
        ).lower() in {"title", "titles"}:
            clean.update(_clean_title_clip(c, cid, clip_duration))
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
                if _crossfade_overlap_allowed(a, b):
                    continue
                raise TimelineError(
                    f"Collision sur la piste {tid}: {a['id']} / {b['id']}"
                )

    return {
        "schema_version": 6,
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
