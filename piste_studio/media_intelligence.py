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

ANALYZER_VERSION = "0.17-local-1"
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class MediaIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class ToolStatus:
    ffmpeg: str | None
    ffprobe: str | None

    @property
    def ready(self) -> bool:
        return bool(self.ffmpeg and self.ffprobe)


def detect_media_tools() -> ToolStatus:
    return ToolStatus(
        ffmpeg=shutil.which("ffmpeg"),
        ffprobe=shutil.which("ffprobe"),
    )


def _run(args: list[str], *, binary: bool = False) -> bytes | str:
    try:
        proc = subprocess.run(
            args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise MediaIntelligenceError(
            f"Outil média introuvable : {args[0]}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode("utf-8", "replace").strip()
        raise MediaIntelligenceError(
            message or f"Commande média en échec : {args[0]}"
        ) from exc
    if binary:
        return proc.stdout
    return proc.stdout.decode("utf-8", "replace")


def _media_row(root: Path, media_id: int) -> dict:
    items = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    item = items.get(int(media_id))
    if item is None:
        raise MediaIntelligenceError(f"Média introuvable : id={media_id}")
    return item


def _media_path(root: Path, item: dict) -> Path:
    path = (root / item["relative_path"]).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise MediaIntelligenceError("Chemin média hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise MediaIntelligenceError(
            f"Fichier média absent : {item['relative_path']}"
        )
    return path


def _parse_fraction(value: str | None) -> float | None:
    if not value:
        return None
    try:
        if "/" in value:
            a, b = value.split("/", 1)
            bval = float(b)
            return float(a) / bval if bval else None
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def probe_media(path: Path) -> dict:
    tools = detect_media_tools()
    if not tools.ffprobe:
        raise MediaIntelligenceError("ffprobe n’est pas disponible.")
    raw = _run([
        tools.ffprobe,
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-of", "json",
        str(path),
    ])
    data = json.loads(str(raw))
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    fmt = data.get("format") or {}
    duration = None
    for candidate in (
        video.get("duration"),
        fmt.get("duration"),
        audio.get("duration"),
    ):
        try:
            if candidate is not None:
                duration = float(candidate)
                break
        except (TypeError, ValueError):
            pass
    return {
        "duration_seconds": duration,
        "width": int(video["width"]) if video.get("width") else None,
        "height": int(video["height"]) if video.get("height") else None,
        "fps": _parse_fraction(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "video_codec": video.get("codec_name"),
        "pixel_format": video.get("pix_fmt"),
        "audio_codec": audio.get("codec_name"),
        "audio_channels": int(audio["channels"]) if audio.get("channels") else None,
        "sample_rate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
        "format_name": fmt.get("format_name"),
        "bit_rate": int(fmt["bit_rate"]) if str(fmt.get("bit_rate") or "").isdigit() else None,
    }


def _average_hash(frame: bytes) -> str:
    if not frame:
        return ""
    avg = sum(frame) / len(frame)
    bits = "".join("1" if px >= avg else "0" for px in frame)
    value = int(bits, 2)
    width = math.ceil(len(bits) / 4)
    return f"{value:0{width}x}"


def visual_signature(
    path: Path,
    *,
    duration_seconds: float,
    samples: int = 6,
    width: int = 16,
    height: int = 9,
) -> list[str]:
    tools = detect_media_tools()
    if not tools.ffmpeg:
        raise MediaIntelligenceError("ffmpeg n’est pas disponible.")
    duration = max(float(duration_seconds or 0), 0.1)
    samples = max(1, min(int(samples), 12))
    fps = samples / duration
    raw = _run([
        tools.ffmpeg,
        "-v", "error",
        "-i", str(path),
        "-vf", f"fps={fps:.8f},scale={width}:{height},format=gray",
        "-frames:v", str(samples),
        "-f", "rawvideo",
        "pipe:1",
    ], binary=True)
    assert isinstance(raw, bytes)
    frame_size = width * height
    frames = [
        raw[i:i + frame_size]
        for i in range(0, len(raw), frame_size)
        if len(raw[i:i + frame_size]) == frame_size
    ]
    return [_average_hash(frame) for frame in frames]


def generate_filmstrip(
    root: Path,
    media_id: int,
    *,
    frames: int = 6,
    width: int = 180,
    force: bool = False,
) -> Path:
    item = _media_row(root, media_id)
    if item.get("kind") != "video":
        raise MediaIntelligenceError("Le filmstrip est réservé aux vidéos.")
    path = _media_path(root, item)
    tools = detect_media_tools()
    if not tools.ffmpeg:
        raise MediaIntelligenceError("ffmpeg n’est pas disponible.")

    analysis = get_media_analysis(root, media_id)
    technical = analysis.get("technical", {}) if analysis else {}
    duration = (
        float(item.get("duration_seconds") or 0)
        or float(technical.get("duration_seconds") or 0)
    )
    if duration <= 0:
        duration = float(probe_media(path).get("duration_seconds") or 0)
    if duration <= 0:
        raise MediaIntelligenceError("Durée vidéo indéterminable.")

    frames = max(3, min(int(frames), 12))
    width = max(80, min(int(width), 480))
    cache = root / "cache" / "filmstrips"
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / f"media_{int(media_id):06d}_{frames}x{width}.jpg"
    if out.exists() and not force:
        return out

    fps = frames / max(duration, 0.1)
    _run([
        tools.ffmpeg,
        "-y",
        "-v", "error",
        "-i", str(path),
        "-vf",
        f"fps={fps:.8f},scale={width}:-2:flags=lanczos,tile={frames}x1",
        "-frames:v", "1",
        "-q:v", "3",
        str(out),
    ])
    if not out.exists():
        raise MediaIntelligenceError("Le filmstrip n’a pas été généré.")
    return out


def _write_analysis(
    root: Path,
    media_id: int,
    *,
    status: str,
    technical: dict,
    signature: list[str],
    filmstrip_path: str | None,
) -> dict:
    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            """
            INSERT INTO media_analysis(
              media_id, analyzer_version, status, technical_json,
              visual_signature_json, filmstrip_path
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(media_id) DO UPDATE SET
              analyzer_version=excluded.analyzer_version,
              status=excluded.status,
              technical_json=excluded.technical_json,
              visual_signature_json=excluded.visual_signature_json,
              filmstrip_path=excluded.filmstrip_path,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                int(media_id),
                ANALYZER_VERSION,
                status,
                json.dumps(technical, ensure_ascii=False),
                json.dumps(signature, ensure_ascii=False),
                filmstrip_path,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_media_analysis(root, media_id) or {}


def analyze_media(
    root: Path,
    media_id: int,
    *,
    make_filmstrip: bool = True,
    force: bool = False,
) -> dict:
    item = _media_row(root, media_id)
    if item.get("kind") != "video":
        raise MediaIntelligenceError("L’analyse V0.17 cible les médias vidéo.")
    existing = get_media_analysis(root, media_id)
    if (
        existing
        and existing.get("analyzer_version") == ANALYZER_VERSION
        and existing.get("status") == "READY"
        and not force
    ):
        strip_ok = True
        if make_filmstrip:
            rel = existing.get("filmstrip_path")
            strip_ok = bool(rel and (root / rel).exists())
        if strip_ok:
            return existing

    path = _media_path(root, item)
    tools = detect_media_tools()
    if not tools.ready:
        return _write_analysis(
            root,
            media_id,
            status="TOOLS_UNAVAILABLE",
            technical={
                "ffmpeg_available": bool(tools.ffmpeg),
                "ffprobe_available": bool(tools.ffprobe),
            },
            signature=[],
            filmstrip_path=None,
        )

    technical = probe_media(path)
    duration = float(
        technical.get("duration_seconds")
        or item.get("duration_seconds")
        or 0
    )
    signature = (
        visual_signature(path, duration_seconds=duration)
        if duration > 0
        else []
    )
    filmstrip_rel = None
    if make_filmstrip and duration > 0:
        strip = generate_filmstrip(
            root, media_id, force=force
        )
        filmstrip_rel = strip.relative_to(root).as_posix()
    technical["filename_tokens"] = filename_tokens(item["relative_path"])
    return _write_analysis(
        root,
        media_id,
        status="READY",
        technical=technical,
        signature=signature,
        filmstrip_path=filmstrip_rel,
    )


def analyze_catalog(
    root: Path,
    *,
    force: bool = False,
    make_filmstrips: bool = True,
) -> dict:
    videos = [
        x for x in fetch_media_with_metadata(root)
        if x.get("kind") == "video"
    ]
    ready = 0
    unavailable = 0
    failed: list[dict] = []
    for item in videos:
        try:
            result = analyze_media(
                root,
                int(item["id"]),
                make_filmstrip=make_filmstrips,
                force=force,
            )
            if result.get("status") == "READY":
                ready += 1
            else:
                unavailable += 1
        except Exception as exc:
            failed.append({"media_id": int(item["id"]), "error": str(exc)})
    return {
        "total": len(videos),
        "ready": ready,
        "unavailable": unavailable,
        "failed": failed,
        "tools": {
            "ffmpeg": bool(detect_media_tools().ffmpeg),
            "ffprobe": bool(detect_media_tools().ffprobe),
        },
    }


def get_media_analysis(root: Path, media_id: int) -> dict | None:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT * FROM media_analysis WHERE media_id=?",
            (int(media_id),),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    out = dict(row)
    for source, target, fallback in (
        ("technical_json", "technical", {}),
        ("visual_signature_json", "visual_signature", []),
    ):
        try:
            out[target] = json.loads(out.pop(source))
        except Exception:
            out[target] = fallback
    return out


def list_media_analysis(root: Path) -> dict[int, dict]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            "SELECT * FROM media_analysis ORDER BY media_id"
        ).fetchall()
    finally:
        conn.close()
    result = {}
    for row in rows:
        out = dict(row)
        try:
            out["technical"] = json.loads(out.pop("technical_json"))
        except Exception:
            out["technical"] = {}
        try:
            out["visual_signature"] = json.loads(
                out.pop("visual_signature_json")
            )
        except Exception:
            out["visual_signature"] = []
        result[int(out["media_id"])] = out
    return result


def filename_tokens(path: str) -> list[str]:
    stem = Path(path).stem.lower()
    ignored = {"mp4", "mov", "take", "shot", "rush", "clip", "video"}
    return sorted(
        {
            token
            for token in _TOKEN_RE.findall(stem)
            if len(token) >= 2 and token not in ignored and not token.isdigit()
        }
    )


def _hex_hamming(a: str, b: str) -> float | None:
    if not a or not b or len(a) != len(b):
        return None
    try:
        av = int(a, 16)
        bv = int(b, 16)
    except ValueError:
        return None
    bits = len(a) * 4
    return 1.0 - ((av ^ bv).bit_count() / bits)


def signature_similarity(a: list[str], b: list[str]) -> float | None:
    if not a or not b:
        return None
    count = min(len(a), len(b))
    if count <= 0:
        return None
    scores = [
        _hex_hamming(a[i], b[i])
        for i in range(count)
    ]
    scores = [x for x in scores if x is not None]
    if not scores:
        return None
    return sum(scores) / len(scores)


def media_similarity(root: Path, media_id: int) -> list[dict]:
    items = fetch_media_with_metadata(root)
    by_id = {int(x["id"]): x for x in items}
    ref = by_id.get(int(media_id))
    if ref is None:
        raise MediaIntelligenceError(f"Média introuvable : id={media_id}")
    analyses = list_media_analysis(root)
    ref_analysis = analyses.get(int(media_id), {})
    ref_sig = ref_analysis.get("visual_signature") or []
    ref_tokens = set(
        (ref_analysis.get("technical") or {}).get("filename_tokens")
        or filename_tokens(ref["relative_path"])
    )
    ref_duration = float(ref.get("duration_seconds") or 0)

    out: list[dict] = []
    for item in items:
        iid = int(item["id"])
        if iid == int(media_id) or item.get("kind") != "video":
            continue
        analysis = analyses.get(iid, {})
        sig = analysis.get("visual_signature") or []
        visual = signature_similarity(ref_sig, sig)
        tokens = set(
            (analysis.get("technical") or {}).get("filename_tokens")
            or filename_tokens(item["relative_path"])
        )
        union = ref_tokens | tokens
        filename_score = (
            len(ref_tokens & tokens) / len(union) if union else 0.0
        )
        dur = float(item.get("duration_seconds") or 0)
        duration_score = (
            max(0.0, 1.0 - abs(ref_duration - dur) / max(ref_duration, dur))
            if ref_duration > 0 and dur > 0
            else 0.0
        )

        if visual is not None:
            score = 0.72 * visual + 0.18 * filename_score + 0.10 * duration_score
            evidence = ["empreinte visuelle"]
        else:
            score = 0.65 * filename_score + 0.35 * duration_score
            evidence = ["nom/durée"]

        if filename_score > 0:
            evidence.append("tokens de fichier")
        if duration_score > 0.85:
            evidence.append("durée proche")
        out.append({
            "media_id": iid,
            "similarity": round(score, 4),
            "visual_similarity": (
                round(visual, 4) if visual is not None else None
            ),
            "filename_similarity": round(filename_score, 4),
            "duration_similarity": round(duration_score, 4),
            "evidence": evidence,
        })
    out.sort(key=lambda x: (-x["similarity"], x["media_id"]))
    return out
