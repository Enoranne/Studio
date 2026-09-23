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
        rows = conn.execute("SELECT m.id, mm.duration_seconds FROM media m LEFT JOIN media_metadata mm ON mm.media_id=m.id").fetchall()
        return {int(r["id"]): (float(r["duration_seconds"]) if r["duration_seconds"] is not None else None) for r in rows}
    finally:
        conn.close()


def validate_timeline(root: Path, payload: dict) -> dict:
    duration = float(payload.get("duration_seconds", 0))
    if duration <= 0 or duration > 3600:
        raise TimelineError("duration_seconds doit être > 0 et <= 3600.")
    tracks = payload.get("tracks")
    clips = payload.get("clips")
    if not isinstance(tracks, list) or not tracks: raise TimelineError("La timeline doit contenir au moins une piste.")
    if not isinstance(clips, list): raise TimelineError("clips doit être une liste.")
    track_ids=set(); clean_tracks=[]
    for t in tracks:
        tid=str(t.get("id","")).strip()
        if not tid or tid in track_ids: raise TimelineError("Identifiants de pistes invalides ou dupliqués.")
        track_ids.add(tid)
        clean_tracks.append({"id":tid,"name":str(t.get("name") or tid).strip(),"kind":str(t.get("kind") or "generic").strip(),"muted":bool(t.get("muted",False)),"locked":bool(t.get("locked",False))})
    durations=_media_duration_map(root); clip_ids=set(); clean_clips=[]
    for c in clips:
        cid=str(c.get("id","")).strip()
        if not cid or cid in clip_ids: raise TimelineError("Identifiants de clips invalides ou dupliqués.")
        clip_ids.add(cid); track=str(c.get("track","")).strip()
        if track not in track_ids: raise TimelineError(f"Piste inconnue pour {cid}: {track}")
        start=float(c.get("start",0)); clip_duration=float(c.get("duration",0))
        if start < 0 or clip_duration <= 0 or start+clip_duration > duration+1e-6: raise TimelineError(f"Plage temporelle invalide pour {cid}.")
        source_start=float(c.get("sourceStart",0) or 0)
        if source_start < 0: raise TimelineError(f"sourceStart invalide pour {cid}.")
        media_db_id=c.get("mediaDbId") or c.get("audioDbId")
        if media_db_id is not None:
            media_db_id=int(media_db_id)
            if media_db_id not in durations: raise TimelineError(f"Média catalogue introuvable pour {cid}: {media_db_id}")
            src_duration=durations[media_db_id]
            if src_duration is not None and source_start+clip_duration > src_duration+1e-6: raise TimelineError(f"{cid} dépasse la durée de sa source média.")
        gain=float(c.get("gain",1) if c.get("gain") is not None else 1); fade_in=float(c.get("fadeIn",0) or 0); fade_out=float(c.get("fadeOut",0) or 0)
        if gain < 0 or gain > 1: raise TimelineError(f"Gain hors plage 0..1 pour {cid}.")
        if fade_in < 0 or fade_out < 0 or fade_in+fade_out > clip_duration+1e-6: raise TimelineError(f"Fades invalides pour {cid}.")
        clean=dict(c); clean.update({"id":cid,"track":track,"start":round(start,6),"duration":round(clip_duration,6),"sourceStart":round(source_start,6)})
        if media_db_id is not None:
            if c.get("mediaDbId") is not None: clean["mediaDbId"]=media_db_id
            if c.get("audioDbId") is not None: clean["audioDbId"]=media_db_id
        clean_clips.append(clean)
    by_track={}
    for c in clean_clips: by_track.setdefault(c["track"],[]).append(c)
    for tid,items in by_track.items():
        items.sort(key=lambda x:(x["start"],x["id"]))
        for a,b in zip(items,items[1:]):
            if _overlap(a["start"],a["start"]+a["duration"],b["start"],b["start"]+b["duration"]): raise TimelineError(f"Collision sur la piste {tid}: {a['id']} / {b['id']}")
    return {"schema_version":1,"edit_name":slugify(str(payload.get("edit_name") or "teaser_30")),"duration_seconds":duration,"tracks":clean_tracks,"clips":clean_clips,"updated_at":datetime.now(timezone.utc).isoformat()}


def save_timeline(root: Path, payload: dict) -> Path:
    doc=validate_timeline(root,payload); path=working_timeline_path(root,doc["edit_name"]); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(".json.tmp"); tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(path); return path
