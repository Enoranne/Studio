from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import subprocess

from .audio_intelligence import measure_loudness
from .db import connect
from .timeline import load_timeline

MASTER_CRITIC_VERSION = "0.26-master-critic-1"
_BLACK_START_RE = re.compile(r"black_start:(-?\d+(?:\.\d+)?)")
_BLACK_END_RE = re.compile(
    r"black_end:(-?\d+(?:\.\d+)?).*?black_duration:(\d+(?:\.\d+)?)"
)


class MasterCriticError(ValueError):
    pass


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise MasterCriticError(
            f"Outil média introuvable : {args[0]}"
        ) from exc


def _resolve_source(root: Path, source_path: str) -> Path:
    root = root.resolve()
    path = Path(source_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise MasterCriticError(
            "Le rendu à critiquer doit rester dans le projet."
        ) from exc
    if not path.exists() or not path.is_file():
        raise MasterCriticError(f"Rendu introuvable : {source_path}")
    return path


def _probe(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise MasterCriticError("ffprobe n’est pas disponible.")
    proc = _run([
        ffprobe,
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-of", "json",
        str(path),
    ])
    if proc.returncode != 0:
        raise MasterCriticError(
            proc.stderr.strip() or "ffprobe du rendu en échec."
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise MasterCriticError("Réponse ffprobe invalide.") from exc

    streams = data.get("streams") or []
    video = next(
        (x for x in streams if x.get("codec_type") == "video"),
        {},
    )
    audio = next(
        (x for x in streams if x.get("codec_type") == "audio"),
        {},
    )
    fmt = data.get("format") or {}
    try:
        duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        duration = None

    return {
        "duration_seconds": duration,
        "width": int(video["width"]) if video.get("width") else None,
        "height": int(video["height"]) if video.get("height") else None,
        "video_codec": video.get("codec_name"),
        "pixel_format": video.get("pix_fmt"),
        "audio_codec": audio.get("codec_name"),
        "audio_channels": (
            int(audio["channels"]) if audio.get("channels") else None
        ),
        "sample_rate": (
            int(audio["sample_rate"])
            if str(audio.get("sample_rate") or "").isdigit()
            else None
        ),
        "has_video": bool(video),
        "has_audio": bool(audio),
    }


def _black_frames(path: Path) -> list[dict]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise MasterCriticError("ffmpeg n’est pas disponible.")
    proc = _run([
        ffmpeg,
        "-hide_banner", "-nostats",
        "-i", str(path),
        "-vf", "blackdetect=d=0.08:pix_th=0.10",
        "-an",
        "-f", "null", "-",
    ])
    text = proc.stderr or ""
    starts = [float(x) for x in _BLACK_START_RE.findall(text)]
    ends = [
        (float(end), float(duration))
        for end, duration in _BLACK_END_RE.findall(text)
    ]
    result = []
    for index, (end, duration) in enumerate(ends):
        start = (
            starts[index]
            if index < len(starts)
            else max(0.0, end - duration)
        )
        result.append({
            "start": round(start, 4),
            "end": round(end, 4),
            "duration": round(duration, 4),
        })
    return result


def _cut_boundaries(timeline: dict | None) -> list[float]:
    if not timeline:
        return []
    story = sorted(
        (
            x for x in timeline.get("clips", [])
            if x.get("track") == "video"
        ),
        key=lambda x: float(x.get("start", 0)),
    )
    return [
        round(float(item["start"]), 4)
        for item in story[1:]
    ]


def _store_report(
    root: Path,
    *,
    edit_name: str,
    version_label: str | None,
    source_path: Path,
    status: str,
    report: dict,
) -> int:
    conn = connect(root / "media.sqlite")
    try:
        cur = conn.execute(
            """
            INSERT INTO master_critic_reports(
              edit_name, version_label, source_path, status, report_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                edit_name,
                version_label,
                source_path.relative_to(root.resolve()).as_posix(),
                status,
                json.dumps(report, ensure_ascii=False),
            ),
        )
        report_id = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()
    return report_id


def get_master_critic_report(root: Path, report_id: int) -> dict:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT * FROM master_critic_reports WHERE id=?",
            (int(report_id),),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise MasterCriticError(
            f"Rapport critic introuvable : {report_id}"
        )
    out = dict(row)
    try:
        out["report"] = json.loads(out.pop("report_json"))
    except Exception:
        out["report"] = {}
    return out


def list_master_critic_reports(
    root: Path,
    *,
    edit_name: str | None = None,
) -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        if edit_name:
            rows = conn.execute(
                "SELECT * FROM master_critic_reports "
                "WHERE edit_name=? ORDER BY id DESC",
                (edit_name,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM master_critic_reports ORDER BY id DESC"
            ).fetchall()
    finally:
        conn.close()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["report"] = json.loads(item.pop("report_json"))
        except Exception:
            item["report"] = {}
        out.append(item)
    return out


def critique_render(
    root: Path,
    *,
    edit_name: str,
    source_path: str,
    version_label: str | None = None,
) -> dict:
    path = _resolve_source(root, source_path)
    technical = _probe(path)
    timeline = load_timeline(root, edit_name)
    expected_duration = (
        float(timeline.get("duration_seconds"))
        if timeline
        else None
    )
    black = _black_frames(path)

    audio = None
    if technical["has_audio"]:
        try:
            measured = measure_loudness(path)
            audio = {
                "integrated_lufs": measured.get("integrated_lufs"),
                "true_peak_dbfs": measured.get("true_peak_dbfs"),
                "loudness_range_lu": measured.get("loudness_range_lu"),
            }
        except Exception as exc:
            audio = {"error": str(exc)}

    findings = []
    severity = "PASS"
    if not technical["has_video"]:
        findings.append({
            "severity": "FAIL",
            "code": "NO_VIDEO",
            "message": "Aucun flux vidéo détecté.",
        })
        severity = "FAIL"
    if not technical["has_audio"]:
        findings.append({
            "severity": "WARN",
            "code": "NO_AUDIO",
            "message": "Aucun flux audio détecté dans le rendu.",
        })
        if severity != "FAIL":
            severity = "WARN"

    actual_duration = technical.get("duration_seconds")
    if (
        expected_duration is not None
        and actual_duration is not None
        and abs(actual_duration - expected_duration) > 0.25
    ):
        findings.append({
            "severity": "WARN",
            "code": "DURATION_MISMATCH",
            "message": (
                f"Durée rendue {actual_duration:.3f}s vs "
                f"timeline {expected_duration:.3f}s."
            ),
        })
        if severity != "FAIL":
            severity = "WARN"

    material_black = [
        item for item in black
        if item["duration"] >= 0.12
        and (
            actual_duration is None
            or (
                item["start"] > 0.15
                and item["end"] < actual_duration - 0.15
            )
        )
    ]
    if material_black:
        findings.append({
            "severity": "WARN",
            "code": "INTERNAL_BLACK",
            "message": (
                f"{len(material_black)} plage(s) noire(s) interne(s) "
                "à vérifier."
            ),
            "ranges": material_black,
        })
        if severity != "FAIL":
            severity = "WARN"

    if audio and audio.get("true_peak_dbfs") is not None:
        if float(audio["true_peak_dbfs"]) > -0.1:
            findings.append({
                "severity": "WARN",
                "code": "TRUE_PEAK_HIGH",
                "message": (
                    f"True peak élevé : "
                    f"{float(audio['true_peak_dbfs']):.2f} dBTP."
                ),
            })
            if severity != "FAIL":
                severity = "WARN"

    if not findings:
        findings.append({
            "severity": "PASS",
            "code": "TECHNICAL_PASS",
            "message": "Aucune anomalie technique automatique détectée.",
        })

    report = {
        "version": MASTER_CRITIC_VERSION,
        "edit_name": edit_name,
        "version_label": version_label,
        "source_path": path.relative_to(root.resolve()).as_posix(),
        "status": severity,
        "technical": technical,
        "audio": audio,
        "black_ranges": black,
        "expected_cut_boundaries": _cut_boundaries(timeline),
        "findings": findings,
        "human_review": {
            "required": True,
            "items": [
                "raccords visuels et direction du regard",
                "lisibilité des titres et sous-titres",
                "cohérence narrative",
                "équilibre subjectif musique/dialogue",
                "continuité personnages/accessoires/décors",
            ],
        },
        "policy": {
            "diagnostic_only": True,
            "automatic_edit": False,
            "automatic_storyline_change": False,
        },
    }
    report_id = _store_report(
        root,
        edit_name=edit_name,
        version_label=version_label,
        source_path=path,
        status=severity,
        report=report,
    )
    report["report_id"] = report_id
    return report
