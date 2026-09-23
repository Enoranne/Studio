from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import re
import shutil
import subprocess

from .db import connect
from .metadata import fetch_media_with_metadata

AUDIO_ANALYZER_VERSION = "0.20-loudness-1"
DEFAULT_TARGET_LUFS = -16.0
DEFAULT_TRUE_PEAK_CEILING = -1.5


class AudioIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class AudioToolStatus:
    ffmpeg: str | None

    @property
    def ready(self) -> bool:
        return bool(self.ffmpeg)


def detect_audio_tools() -> AudioToolStatus:
    return AudioToolStatus(ffmpeg=shutil.which("ffmpeg"))


def _media_row(root: Path, media_id: int) -> dict:
    rows = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    item = rows.get(int(media_id))
    if item is None:
        raise AudioIntelligenceError(f"Média introuvable : id={media_id}")
    if item.get("kind") != "audio":
        raise AudioIntelligenceError("L’analyse loudness cible les médias audio.")
    return item


def _media_path(root: Path, item: dict) -> Path:
    root = root.resolve()
    path = (root / item["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AudioIntelligenceError("Chemin média hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise AudioIntelligenceError(
            f"Fichier audio absent : {item['relative_path']}"
        )
    return path


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
        raise AudioIntelligenceError("ffmpeg n’est pas disponible.") from exc


def _extract_loudnorm_json(stderr: str) -> dict:
    candidates = re.findall(r"\{\s*\"input_i\".*?\}", stderr, flags=re.S)
    for raw in reversed(candidates):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "input_i" in parsed:
            return parsed
    raise AudioIntelligenceError("Résumé loudnorm ffmpeg introuvable.")


def _float_field(data: dict, key: str) -> float | None:
    value = data.get(key)
    try:
        if value in (None, "", "-inf", "inf", "nan"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def measure_loudness(
    path: Path,
    *,
    target_lufs: float = DEFAULT_TARGET_LUFS,
    true_peak_ceiling: float = DEFAULT_TRUE_PEAK_CEILING,
) -> dict:
    tools = detect_audio_tools()
    if not tools.ffmpeg:
        raise AudioIntelligenceError("ffmpeg n’est pas disponible.")
    proc = _run_ffmpeg([
        tools.ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        (
            f"loudnorm=I={float(target_lufs)}:"
            f"TP={float(true_peak_ceiling)}:LRA=11:print_format=json"
        ),
        "-f",
        "null",
        "-",
    ])
    if proc.returncode != 0:
        raise AudioIntelligenceError(
            proc.stderr.strip() or "Analyse loudness ffmpeg en échec."
        )
    raw = _extract_loudnorm_json(proc.stderr)
    return {
        "integrated_lufs": _float_field(raw, "input_i"),
        "true_peak_dbfs": _float_field(raw, "input_tp"),
        "loudness_range_lu": _float_field(raw, "input_lra"),
        "threshold_lufs": _float_field(raw, "input_thresh"),
        "raw": raw,
    }


_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?\d+(?:\.\d+)?)")
_SILENCE_END_RE = re.compile(
    r"silence_end:\s*(-?\d+(?:\.\d+)?)\s*\|\s*silence_duration:\s*(\d+(?:\.\d+)?)"
)


def detect_silence(
    path: Path,
    *,
    noise_db: float = -45.0,
    min_duration: float = 0.35,
) -> list[dict]:
    tools = detect_audio_tools()
    if not tools.ffmpeg:
        raise AudioIntelligenceError("ffmpeg n’est pas disponible.")
    proc = _run_ffmpeg([
        tools.ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        f"silencedetect=noise={float(noise_db)}dB:d={float(min_duration)}",
        "-f",
        "null",
        "-",
    ])
    if proc.returncode != 0:
        raise AudioIntelligenceError(
            proc.stderr.strip() or "Détection de silence ffmpeg en échec."
        )

    starts = [float(x) for x in _SILENCE_START_RE.findall(proc.stderr)]
    ends = [
        (float(end), float(duration))
        for end, duration in _SILENCE_END_RE.findall(proc.stderr)
    ]
    result = []
    for index, (end, duration) in enumerate(ends):
        start = starts[index] if index < len(starts) else max(0.0, end - duration)
        result.append({
            "start": round(max(0.0, start), 4),
            "end": round(max(0.0, end), 4),
            "duration": round(max(0.0, duration), 4),
        })
    return result


def _write_analysis(
    root: Path,
    media_id: int,
    *,
    status: str,
    integrated_lufs: float | None = None,
    true_peak_dbfs: float | None = None,
    loudness_range_lu: float | None = None,
    threshold_lufs: float | None = None,
    silence: list[dict] | None = None,
    raw: dict | None = None,
) -> dict:
    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            """
            INSERT INTO audio_loudness_analysis(
              media_id, analyzer_version, status, integrated_lufs,
              true_peak_dbfs, loudness_range_lu, threshold_lufs,
              silence_json, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(media_id) DO UPDATE SET
              analyzer_version=excluded.analyzer_version,
              status=excluded.status,
              integrated_lufs=excluded.integrated_lufs,
              true_peak_dbfs=excluded.true_peak_dbfs,
              loudness_range_lu=excluded.loudness_range_lu,
              threshold_lufs=excluded.threshold_lufs,
              silence_json=excluded.silence_json,
              raw_json=excluded.raw_json,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                int(media_id),
                AUDIO_ANALYZER_VERSION,
                status,
                integrated_lufs,
                true_peak_dbfs,
                loudness_range_lu,
                threshold_lufs,
                json.dumps(silence or [], ensure_ascii=False),
                json.dumps(raw or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_audio_analysis(root, media_id) or {}


def get_audio_analysis(root: Path, media_id: int) -> dict | None:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT * FROM audio_loudness_analysis WHERE media_id=?",
            (int(media_id),),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    out = dict(row)
    try:
        out["silence"] = json.loads(out.pop("silence_json"))
    except Exception:
        out["silence"] = []
    try:
        out["raw"] = json.loads(out.pop("raw_json"))
    except Exception:
        out["raw"] = {}
    return out


def list_audio_analysis(root: Path) -> dict[int, dict]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            "SELECT * FROM audio_loudness_analysis ORDER BY media_id"
        ).fetchall()
    finally:
        conn.close()
    return {
        int(row["media_id"]): get_audio_analysis(root, int(row["media_id"])) or {}
        for row in rows
    }


def analyze_audio(
    root: Path,
    media_id: int,
    *,
    force: bool = False,
    detect_silences: bool = True,
) -> dict:
    item = _media_row(root, media_id)
    existing = get_audio_analysis(root, media_id)
    if (
        existing
        and existing.get("analyzer_version") == AUDIO_ANALYZER_VERSION
        and existing.get("status") == "READY"
        and not force
    ):
        return existing

    tools = detect_audio_tools()
    if not tools.ready:
        return _write_analysis(
            root,
            media_id,
            status="TOOLS_UNAVAILABLE",
            raw={"ffmpeg_available": False},
        )

    path = _media_path(root, item)
    loudness = measure_loudness(path)
    silence = detect_silence(path) if detect_silences else []
    return _write_analysis(
        root,
        media_id,
        status="READY",
        integrated_lufs=loudness["integrated_lufs"],
        true_peak_dbfs=loudness["true_peak_dbfs"],
        loudness_range_lu=loudness["loudness_range_lu"],
        threshold_lufs=loudness["threshold_lufs"],
        silence=silence,
        raw=loudness["raw"],
    )


def analyze_audio_catalog(
    root: Path,
    *,
    force: bool = False,
    detect_silences: bool = True,
) -> dict:
    items = [
        x for x in fetch_media_with_metadata(root)
        if x.get("kind") == "audio"
    ]
    ready = 0
    unavailable = 0
    failed = []
    for item in items:
        try:
            result = analyze_audio(
                root,
                int(item["id"]),
                force=force,
                detect_silences=detect_silences,
            )
            if result.get("status") == "READY":
                ready += 1
            else:
                unavailable += 1
        except Exception as exc:
            failed.append({"media_id": int(item["id"]), "error": str(exc)})
    return {
        "total": len(items),
        "ready": ready,
        "unavailable": unavailable,
        "failed": failed,
        "ffmpeg": bool(detect_audio_tools().ffmpeg),
    }


def normalization_proposal(
    root: Path,
    media_id: int,
    *,
    target_lufs: float = DEFAULT_TARGET_LUFS,
    true_peak_ceiling: float = DEFAULT_TRUE_PEAK_CEILING,
) -> dict:
    analysis = get_audio_analysis(root, media_id)
    if not analysis or analysis.get("status") != "READY":
        raise AudioIntelligenceError(
            "Analyse loudness requise avant normalisation."
        )
    integrated = analysis.get("integrated_lufs")
    true_peak = analysis.get("true_peak_dbfs")
    if integrated is None:
        raise AudioIntelligenceError("LUFS intégré indisponible.")

    desired = float(target_lufs) - float(integrated)
    limited_by_peak = False
    adjustment = desired
    if true_peak is not None:
        peak_headroom = float(true_peak_ceiling) - float(true_peak)
        if adjustment > peak_headroom:
            adjustment = peak_headroom
            limited_by_peak = True
    adjustment = max(-24.0, min(12.0, adjustment))
    return {
        "media_id": int(media_id),
        "target_lufs": round(float(target_lufs), 2),
        "true_peak_ceiling": round(float(true_peak_ceiling), 2),
        "source_lufs": float(integrated),
        "source_true_peak_dbfs": (
            float(true_peak) if true_peak is not None else None
        ),
        "gain_adjustment_db": round(adjustment, 3),
        "estimated_lufs_after": round(float(integrated) + adjustment, 3),
        "estimated_true_peak_after": (
            round(float(true_peak) + adjustment, 3)
            if true_peak is not None else None
        ),
        "limited_by_true_peak": limited_by_peak,
        "policy": {
            "non_destructive": True,
            "human_validation_required": True,
            "automatic_render": False,
        },
    }


def _audio_clip(timeline: dict, clip_id: str) -> dict:
    clip = next(
        (x for x in timeline.get("clips", []) if str(x.get("id")) == str(clip_id)),
        None,
    )
    if clip is None:
        raise AudioIntelligenceError(f"Clip introuvable : {clip_id}")
    if clip.get("audioDbId") is None and clip.get("audioId") is None:
        raise AudioIntelligenceError(f"{clip_id} n’est pas un clip audio.")
    return clip


def _max_clip_gain_db(clip: dict) -> float:
    envelope = clip.get("volumeEnvelope") or []
    if envelope:
        return max(float(p.get("gainDb", -60)) for p in envelope)
    return float(clip.get("gainDb", 0) or 0)


def clipping_risk_report(
    root: Path,
    timeline: dict,
    *,
    true_peak_ceiling: float = -1.0,
) -> dict:
    analyses = list_audio_analysis(root)
    clips = []
    for clip in timeline.get("clips", []):
        media_id = clip.get("audioDbId")
        if media_id is None:
            continue
        analysis = analyses.get(int(media_id))
        if not analysis or analysis.get("status") != "READY":
            clips.append({
                "clip_id": clip.get("id"),
                "status": "UNKNOWN",
                "reason": "Analyse loudness absente.",
            })
            continue
        source_peak = analysis.get("true_peak_dbfs")
        if source_peak is None:
            clips.append({
                "clip_id": clip.get("id"),
                "status": "UNKNOWN",
                "reason": "True peak source indisponible.",
            })
            continue
        max_gain = _max_clip_gain_db(clip)
        estimate = float(source_peak) + max_gain
        clips.append({
            "clip_id": clip.get("id"),
            "status": "RISK" if estimate > true_peak_ceiling else "OK",
            "source_true_peak_dbfs": float(source_peak),
            "max_clip_gain_db": round(max_gain, 3),
            "estimated_true_peak_dbfs": round(estimate, 3),
            "ceiling_dbfs": float(true_peak_ceiling),
        })
    return {
        "method": "per_clip_estimate",
        "master_measurement": False,
        "true_peak_ceiling": float(true_peak_ceiling),
        "clips": clips,
        "risk_count": sum(1 for x in clips if x.get("status") == "RISK"),
    }


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        prev = merged[-1]
        if start <= prev[1] + 1e-6:
            prev[1] = max(prev[1], end)
        else:
            merged.append([start, end])
    return [(float(a), float(b)) for a, b in merged]


def propose_ducking(
    timeline: dict,
    music_clip_id: str,
    *,
    reduction_db: float = 8.0,
    attack_seconds: float = 0.25,
    release_seconds: float = 0.5,
) -> dict:
    music = _audio_clip(timeline, music_clip_id)
    role = str(music.get("audioRole") or music.get("track") or "").lower()
    if role != "music":
        raise AudioIntelligenceError(
            "Le ducking cible un clip de rôle MUSIC."
        )
    reduction = max(0.0, min(24.0, float(reduction_db)))
    attack = max(0.0, min(2.0, float(attack_seconds)))
    release = max(0.0, min(4.0, float(release_seconds)))
    mstart = float(music["start"])
    mend = mstart + float(music["duration"])
    blockers = []
    intervals = []
    for clip in timeline.get("clips", []):
        if clip.get("id") == music_clip_id:
            continue
        if clip.get("audioDbId") is None and clip.get("audioId") is None:
            continue
        crole = str(clip.get("audioRole") or clip.get("track") or "").lower()
        if crole not in {"vo", "dialogue"}:
            continue
        start = max(mstart, float(clip["start"]))
        end = min(mend, float(clip["start"]) + float(clip["duration"]))
        if start < end:
            intervals.append((start, end))
            blockers.append({
                "clip_id": clip.get("id"),
                "label": clip.get("label") or clip.get("id"),
                "role": crole,
                "start": round(start, 4),
                "end": round(end, 4),
            })
    merged = _merge_intervals(intervals)
    baseline = float(music.get("gainDb", 0) or 0)
    ducked = max(-60.0, baseline - reduction)

    points: dict[float, float] = {}
    for start, end in merged:
        local_attack = max(0.0, start - attack - mstart)
        local_start = max(0.0, start - mstart)
        local_end = min(float(music["duration"]), end - mstart)
        local_release = min(
            float(music["duration"]),
            end + release - mstart,
        )
        points[round(local_attack, 4)] = baseline
        points[round(local_start, 4)] = ducked
        points[round(local_end, 4)] = ducked
        points[round(local_release, 4)] = baseline

    envelope = [
        {"time": time, "gainDb": round(gain, 3)}
        for time, gain in sorted(points.items())
    ]
    return {
        "music_clip_id": str(music_clip_id),
        "baseline_gain_db": baseline,
        "reduction_db": reduction,
        "attack_seconds": attack,
        "release_seconds": release,
        "blockers": blockers,
        "speech_intervals": [
            {"start": round(a, 4), "end": round(b, 4)}
            for a, b in merged
        ],
        "suggested_envelope": envelope,
        "policy": {
            "human_validation_required": True,
            "automatic_apply": False,
            "storyline_timing_change": False,
        },
    }


def apply_envelope(
    timeline: dict,
    clip_id: str,
    envelope: list[dict],
) -> dict:
    out = json.loads(json.dumps(timeline))
    clip = _audio_clip(out, clip_id)
    clip["volumeEnvelope"] = [
        {
            "time": round(float(p["time"]), 6),
            "gainDb": round(float(p["gainDb"]), 3),
        }
        for p in envelope
    ]
    return out


def propose_crossfade(
    timeline: dict,
    left_clip_id: str,
    right_clip_id: str,
    *,
    duration_seconds: float = 0.5,
) -> dict:
    left = _audio_clip(timeline, left_clip_id)
    right = _audio_clip(timeline, right_clip_id)
    if str(left.get("track")) != str(right.get("track")):
        raise AudioIntelligenceError(
            "Le crossfade V0.20 cible deux clips de la même piste."
        )
    if float(left["start"]) > float(right["start"]):
        left, right = right, left
        left_clip_id, right_clip_id = right_clip_id, left_clip_id

    duration = max(
        0.05,
        min(
            float(duration_seconds),
            float(left["duration"]) / 2,
            float(right["duration"]) / 2,
        ),
    )
    left_end = float(left["start"]) + float(left["duration"])
    gap = float(right["start"]) - left_end
    if gap > 0.001:
        raise AudioIntelligenceError(
            "Les clips doivent être adjacents ou déjà se chevaucher."
        )
    new_right_start = (
        float(right["start"]) - duration
        if abs(gap) <= 0.001
        else float(right["start"])
    )
    overlap = min(
        left_end,
        new_right_start + float(right["duration"]),
    ) - max(float(left["start"]), new_right_start)
    cross = max(0.05, min(duration, overlap if overlap > 0 else duration))

    return {
        "left_clip_id": str(left_clip_id),
        "right_clip_id": str(right_clip_id),
        "duration_seconds": round(cross, 4),
        "right_start": round(new_right_start, 6),
        "left_fade_out": round(cross, 6),
        "right_fade_in": round(cross, 6),
        "policy": {
            "human_validation_required": True,
            "automatic_apply": False,
            "timing_change": abs(new_right_start - float(right["start"])) > 1e-6,
        },
    }


def apply_crossfade(timeline: dict, proposal: dict) -> dict:
    out = json.loads(json.dumps(timeline))
    left = _audio_clip(out, proposal["left_clip_id"])
    right = _audio_clip(out, proposal["right_clip_id"])
    duration = float(proposal["duration_seconds"])
    right["start"] = float(proposal["right_start"])
    left["fadeOut"] = duration
    right["fadeIn"] = duration
    left["crossfadeWith"] = str(right["id"])
    right["crossfadeWith"] = str(left["id"])
    left["crossfadeDuration"] = duration
    right["crossfadeDuration"] = duration
    return out
