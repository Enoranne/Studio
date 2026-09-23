from __future__ import annotations

from pathlib import Path
import json
import hashlib
import math
import re
import shutil
import subprocess
from datetime import datetime, timezone

from .audio_intelligence import detect_audio_tools, measure_loudness
from .metadata import fetch_media_with_metadata


AUDIO_DELIVERY_VERSION = "0.21-master-2"
DEFAULT_TARGET_LUFS = -16.0
DEFAULT_TRUE_PEAK_CEILING = -1.0
DEFAULT_LOUDNESS_TOLERANCE = 1.0


class AudioDeliveryError(ValueError):
    pass


def delivery_presets() -> list[dict]:
    """Reference presets only; none is presented as a universal delivery standard."""
    return [
        {
            "id": "online_reference",
            "label": "Online stéréo · repère",
            "target_lufs": -16.0,
            "true_peak_ceiling": -1.0,
            "loudness_tolerance_lu": 1.0,
            "reference_only": True,
        },
        {
            "id": "broadcast_reference",
            "label": "Broadcast · repère -23 LUFS",
            "target_lufs": -23.0,
            "true_peak_ceiling": -1.0,
            "loudness_tolerance_lu": 1.0,
            "reference_only": True,
        },
        {
            "id": "custom",
            "label": "Personnalisé",
            "target_lufs": DEFAULT_TARGET_LUFS,
            "true_peak_ceiling": DEFAULT_TRUE_PEAK_CEILING,
            "loudness_tolerance_lu": DEFAULT_LOUDNESS_TOLERANCE,
            "reference_only": True,
        },
    ]


def resolve_delivery_settings(
    *,
    preset_id: str = "online_reference",
    target_lufs: float | None = None,
    true_peak_ceiling: float | None = None,
    loudness_tolerance_lu: float | None = None,
) -> dict:
    presets = {p["id"]: p for p in delivery_presets()}
    if preset_id not in presets:
        raise AudioDeliveryError(f"Preset audio inconnu : {preset_id}")
    preset = dict(presets[preset_id])
    if target_lufs is not None:
        preset["target_lufs"] = float(target_lufs)
    if true_peak_ceiling is not None:
        preset["true_peak_ceiling"] = float(true_peak_ceiling)
    if loudness_tolerance_lu is not None:
        preset["loudness_tolerance_lu"] = max(0.1, float(loudness_tolerance_lu))
    return preset


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "mix")).strip("._")
    return cleaned or "mix"


def audio_mix_fingerprint(timeline: dict) -> str:
    """Hash only audio-delivery-relevant timeline state."""
    tracks = []
    for track in timeline.get("tracks", []):
        ident = str(track.get("id") or "")
        kind = str(track.get("kind") or ident).lower()
        if kind not in {"audio", "vo", "dialogue", "music", "ambience", "sfx"}:
            continue
        tracks.append({
            "id": ident,
            "kind": kind,
            "muted": bool(track.get("muted")),
            "solo": bool(track.get("solo")),
        })
    tracks.sort(key=lambda item: item["id"])

    clips = []
    for clip in timeline.get("clips", []):
        if clip.get("audioDbId") is None:
            continue
        envelope = [
            {
                "time": round(float(point.get("time") or 0.0), 6),
                "gainDb": round(float(point.get("gainDb") or 0.0), 6),
            }
            for point in (clip.get("volumeEnvelope") or [])
            if isinstance(point, dict)
        ]
        envelope.sort(key=lambda point: point["time"])
        clips.append({
            "id": str(clip.get("id") or ""),
            "track": str(clip.get("track") or ""),
            "audioDbId": int(clip["audioDbId"]),
            "start": round(float(clip.get("start") or 0.0), 6),
            "duration": round(float(clip.get("duration") or 0.0), 6),
            "sourceStart": round(float(clip.get("sourceStart") or 0.0), 6),
            "gainDb": round(float(clip.get("gainDb") or 0.0), 6),
            "pan": round(float(clip.get("pan") or 0.0), 6),
            "fadeIn": round(float(clip.get("fadeIn") or 0.0), 6),
            "fadeOut": round(float(clip.get("fadeOut") or 0.0), 6),
            "audioRole": str(clip.get("audioRole") or ""),
            "crossfadeWith": (
                str(clip.get("crossfadeWith"))
                if clip.get("crossfadeWith") is not None
                else None
            ),
            "crossfadeDuration": round(
                float(clip.get("crossfadeDuration") or 0.0),
                6,
            ),
            "volumeEnvelope": envelope,
        })
    clips.sort(key=lambda item: item["id"])

    payload = {
        "duration_seconds": round(float(timeline.get("duration_seconds") or 0.0), 6),
        "tracks": tracks,
        "clips": clips,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _audio_tracks(timeline: dict) -> dict[str, dict]:
    out = {}
    for track in timeline.get("tracks", []):
        ident = str(track.get("id") or "")
        kind = str(track.get("kind") or ident).lower()
        if kind in {"audio", "vo", "dialogue", "music", "ambience", "sfx"}:
            out[ident] = track
    return out


def _audible_audio_clips(timeline: dict) -> list[dict]:
    tracks = _audio_tracks(timeline)
    any_solo = any(bool(t.get("solo")) for t in tracks.values())
    clips = []
    for clip in timeline.get("clips", []):
        if clip.get("audioDbId") is None:
            continue
        track = tracks.get(str(clip.get("track")))
        if track is None:
            continue
        if bool(track.get("muted")):
            continue
        if any_solo and not bool(track.get("solo")):
            continue
        clips.append(clip)
    return clips


def _media_map(root: Path) -> dict[int, dict]:
    return {
        int(row["id"]): row
        for row in fetch_media_with_metadata(root)
        if row.get("kind") == "audio"
    }


def _media_path(root: Path, row: dict) -> Path:
    base = root.resolve()
    path = (base / str(row["relative_path"])).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise AudioDeliveryError("Chemin média audio hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise AudioDeliveryError(f"Fichier audio absent : {row['relative_path']}")
    return path


def _clamp_db(value: float) -> float:
    return max(-60.0, min(12.0, float(value)))


def _db_amp(value: float) -> float:
    return 10.0 ** (_clamp_db(value) / 20.0)


def _gain_expression(clip: dict) -> str:
    points = []
    duration = max(0.001, float(clip.get("duration") or 0.001))
    for raw in clip.get("volumeEnvelope") or []:
        if not isinstance(raw, dict):
            continue
        t = max(0.0, min(duration, float(raw.get("time") or 0.0)))
        points.append((t, _clamp_db(float(raw.get("gainDb") or 0.0))))
    points.sort(key=lambda item: item[0])
    if not points:
        return f"{_db_amp(float(clip.get('gainDb') or 0.0)):.9f}"

    compact: list[tuple[float, float]] = []
    for point in points:
        if compact and abs(point[0] - compact[-1][0]) < 1e-9:
            compact[-1] = point
        else:
            compact.append(point)
    points = compact

    def amp(db: float) -> str:
        return f"{_db_amp(db):.9f}"

    expr = amp(points[-1][1])
    for index in range(len(points) - 1, 0, -1):
        t0, db0 = points[index - 1]
        t1, db1 = points[index]
        span = max(1e-6, t1 - t0)
        slope = (db1 - db0) / span
        segment_db = f"({db0:.9f}+({slope:.9f})*(t-{t0:.9f}))"
        segment_amp = f"pow(10,{segment_db}/20)"
        expr = f"if(lte(t,{t1:.9f}),{segment_amp},{expr})"
    first_t, first_db = points[0]
    return f"if(lte(t,{first_t:.9f}),{amp(first_db)},{expr})"


def build_master_render_plan(root: Path, timeline: dict, *, limiter: bool = False, limiter_ceiling_db: float = -1.0) -> dict:
    clips = _audible_audio_clips(timeline)
    if not clips:
        raise AudioDeliveryError("Aucun clip audio audible à rendre.")

    media = _media_map(root)
    inputs: list[str] = []
    filter_parts: list[str] = []
    clip_plan: list[dict] = []

    for index, clip in enumerate(clips):
        media_id = int(clip["audioDbId"])
        row = media.get(media_id)
        if row is None:
            raise AudioDeliveryError(f"Média audio introuvable : id={media_id}")
        path = _media_path(root, row)
        inputs.append(str(path))

        duration = max(0.001, float(clip.get("duration") or 0.001))
        source_start = max(0.0, float(clip.get("sourceStart") or 0.0))
        timeline_start = max(0.0, float(clip.get("start") or 0.0))
        fade_in = max(0.0, min(duration, float(clip.get("fadeIn") or 0.0)))
        fade_out = max(0.0, min(duration, float(clip.get("fadeOut") or 0.0)))
        pan = max(-1.0, min(1.0, float(clip.get("pan") or 0.0)))

        chain = [
            f"[{index}:a]atrim=start={source_start:.6f}:duration={duration:.6f}",
            "asetpts=PTS-STARTPTS",
            "aresample=48000",
            "aformat=sample_fmts=fltp:channel_layouts=stereo",
            f"volume='{_gain_expression(clip)}':eval=frame",
        ]
        if fade_in > 0:
            chain.append(f"afade=t=in:st=0:d={fade_in:.6f}")
        if fade_out > 0:
            chain.append(f"afade=t=out:st={max(0.0, duration - fade_out):.6f}:d={fade_out:.6f}")
        if abs(pan) > 1e-6:
            left = 1.0 - max(0.0, pan)
            right = 1.0 + min(0.0, pan)
            chain.append(f"pan=stereo|c0={left:.6f}*c0|c1={right:.6f}*c1")
        delay_ms = max(0, round(timeline_start * 1000))
        chain.append(f"adelay={delay_ms}|{delay_ms}")
        filter_parts.append(",".join(chain) + f"[a{index}]")
        clip_plan.append({
            "clip_id": str(clip.get("id") or f"audio_{index}"),
            "media_id": media_id,
            "relative_path": str(row["relative_path"]),
            "start": timeline_start,
            "duration": duration,
            "source_start": source_start,
            "pan": pan,
            "fade_in": fade_in,
            "fade_out": fade_out,
            "automation_points": len(clip.get("volumeEnvelope") or []),
        })

    duration = max(
        float(timeline.get("duration_seconds") or 0.0),
        max(float(c.get("start") or 0.0) + float(c.get("duration") or 0.0) for c in clips),
    )
    labels = "".join(f"[a{i}]" for i in range(len(clips)))
    master_chain = (
        f"{labels}amix=inputs={len(clips)}:duration=longest:dropout_transition=0:normalize=0,"
        f"apad=pad_dur={duration:.6f},atrim=duration={duration:.6f}"
    )
    if limiter:
        ceiling_amp = min(1.0, max(0.0625, 10.0 ** (float(limiter_ceiling_db) / 20.0)))
        master_chain += f",alimiter=limit={ceiling_amp:.9f}:attack=5:release=50"
    master_chain += "[master]"
    filter_parts.append(master_chain)

    return {
        "inputs": inputs,
        "filter_complex": ";".join(filter_parts),
        "map": "[master]",
        "duration_seconds": duration,
        "clips": clip_plan,
        "limiter": bool(limiter),
        "limiter_ceiling_db": float(limiter_ceiling_db) if limiter else None,
    }


def _run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AudioDeliveryError("ffmpeg n’est pas disponible.") from exc


def render_master_mix(
    root: Path,
    timeline: dict,
    *,
    limiter: bool = False,
    limiter_ceiling_db: float = DEFAULT_TRUE_PEAK_CEILING,
) -> dict:
    tools = detect_audio_tools()
    if not tools.ffmpeg:
        raise AudioDeliveryError("ffmpeg n’est pas disponible.")
    plan = build_master_render_plan(
        root,
        timeline,
        limiter=limiter,
        limiter_ceiling_db=limiter_ceiling_db,
    )
    edit_name = _safe_name(str(timeline.get("edit_name") or "mix"))
    cache_dir = root / "cache" / "audio_delivery"
    cache_dir.mkdir(parents=True, exist_ok=True)
    output = cache_dir / f"{edit_name}_master_check.wav"

    args = [tools.ffmpeg, "-hide_banner", "-nostats", "-y"]
    for path in plan["inputs"]:
        args.extend(["-i", path])
    args.extend([
        "-filter_complex", plan["filter_complex"],
        "-map", plan["map"],
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s24le",
        str(output),
    ])
    proc = _run_ffmpeg(args)
    if proc.returncode != 0:
        raise AudioDeliveryError(proc.stderr.strip() or "Rendu master ffmpeg en échec.")
    if not output.exists():
        raise AudioDeliveryError("ffmpeg n’a pas produit le master temporaire attendu.")
    return {
        "path": output,
        "relative_path": output.relative_to(root).as_posix(),
        "plan": plan,
    }


def evaluate_master_measurement(
    measurement: dict,
    *,
    target_lufs: float,
    true_peak_ceiling: float,
    loudness_tolerance_lu: float,
) -> dict:
    integrated = measurement.get("integrated_lufs")
    peak = measurement.get("true_peak_dbfs")
    loudness_delta = None if integrated is None else float(integrated) - float(target_lufs)
    loudness_ok = integrated is not None and abs(loudness_delta) <= float(loudness_tolerance_lu)
    peak_ok = peak is not None and float(peak) <= float(true_peak_ceiling)
    status = "PASS" if loudness_ok and peak_ok else "WARN"
    reasons = []
    if integrated is None:
        reasons.append("LUFS intégré indisponible.")
    elif not loudness_ok:
        reasons.append(
            f"LUFS hors tolérance ({loudness_delta:+.2f} LU vs cible {target_lufs:.1f})."
        )
    if peak is None:
        reasons.append("True peak master indisponible.")
    elif not peak_ok:
        reasons.append(
            f"True peak {float(peak):.2f} dBTP au-dessus du ceiling {true_peak_ceiling:.2f} dBTP."
        )
    return {
        "status": status,
        "loudness_ok": bool(loudness_ok),
        "true_peak_ok": bool(peak_ok),
        "loudness_delta_lu": None if loudness_delta is None else round(loudness_delta, 3),
        "reasons": reasons,
    }


def run_master_check(
    root: Path,
    timeline: dict,
    *,
    preset_id: str = "online_reference",
    target_lufs: float | None = None,
    true_peak_ceiling: float | None = None,
    loudness_tolerance_lu: float | None = None,
    limiter: bool = False,
) -> dict:
    settings = resolve_delivery_settings(
        preset_id=preset_id,
        target_lufs=target_lufs,
        true_peak_ceiling=true_peak_ceiling,
        loudness_tolerance_lu=loudness_tolerance_lu,
    )
    rendered = render_master_mix(
        root,
        timeline,
        limiter=bool(limiter),
        limiter_ceiling_db=float(settings["true_peak_ceiling"]),
    )
    measurement = measure_loudness(
        rendered["path"],
        target_lufs=float(settings["target_lufs"]),
        true_peak_ceiling=float(settings["true_peak_ceiling"]),
    )
    evaluation = evaluate_master_measurement(
        measurement,
        target_lufs=float(settings["target_lufs"]),
        true_peak_ceiling=float(settings["true_peak_ceiling"]),
        loudness_tolerance_lu=float(settings["loudness_tolerance_lu"]),
    )
    edit_name = _safe_name(str(timeline.get("edit_name") or "mix"))
    report_dir = root / "reports" / "audio"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{edit_name}_master_check.json"
    report = {
        "version": AUDIO_DELIVERY_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "edit_name": str(timeline.get("edit_name") or "mix"),
        "preset": settings,
        "measurement": {
            "integrated_lufs": measurement.get("integrated_lufs"),
            "true_peak_dbfs": measurement.get("true_peak_dbfs"),
            "loudness_range_lu": measurement.get("loudness_range_lu"),
            "threshold_lufs": measurement.get("threshold_lufs"),
        },
        "evaluation": evaluation,
        "render": {
            "relative_path": rendered["relative_path"],
            "duration_seconds": rendered["plan"]["duration_seconds"],
            "clip_count": len(rendered["plan"]["clips"]),
            "limiter_enabled": bool(limiter),
        },
        "policy": {
            "measured_after_sum": True,
            "reference_presets_not_universal_standards": True,
            "automatic_normalization": False,
            "automatic_limiter": False,
            "limiter_requires_explicit_choice": True,
            "source_media_immutable": True,
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_relative_path"] = report_path.relative_to(root).as_posix()
    report["report_name"] = report_path.name
    return report


def report_path(root: Path, report_name: str) -> Path:
    name = Path(report_name).name
    if name != report_name or not name.endswith(".json"):
        raise AudioDeliveryError("Nom de rapport audio invalide.")
    path = (root / "reports" / "audio" / name).resolve()
    base = (root / "reports" / "audio").resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise AudioDeliveryError("Rapport hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise AudioDeliveryError("Rapport audio introuvable.")
    return path
