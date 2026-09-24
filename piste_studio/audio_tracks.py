from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import shutil
import subprocess

from .db import connect
from .metadata import fetch_media_with_metadata

AUDIO_TRACK_INTELLIGENCE_VERSION = "0.26-audio-track-1"
SILENCE_PEAK_DBFS = -60.0


class AudioTrackIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class AudioTrackTools:
    ffmpeg: str | None
    ffprobe: str | None

    @property
    def ready(self) -> bool:
        return bool(self.ffmpeg and self.ffprobe)


def detect_audio_track_tools() -> AudioTrackTools:
    return AudioTrackTools(
        ffmpeg=shutil.which("ffmpeg"),
        ffprobe=shutil.which("ffprobe"),
    )


def _media_item(root: Path, media_id: int) -> dict:
    rows = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    item = rows.get(int(media_id))
    if item is None:
        raise AudioTrackIntelligenceError(f"Média introuvable : id={media_id}")
    if item.get("kind") not in {"video", "audio"}:
        raise AudioTrackIntelligenceError(
            "L’analyse des pistes audio cible un média vidéo ou audio."
        )
    return item


def _media_path(root: Path, item: dict) -> Path:
    root = root.resolve()
    path = (root / item["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AudioTrackIntelligenceError("Chemin média hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise AudioTrackIntelligenceError(
            f"Fichier média absent : {item['relative_path']}"
        )
    return path


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
        raise AudioTrackIntelligenceError(
            f"Outil média introuvable : {args[0]}"
        ) from exc


def probe_audio_streams(path: Path) -> list[dict]:
    tools = detect_audio_track_tools()
    if not tools.ffprobe:
        raise AudioTrackIntelligenceError("ffprobe n’est pas disponible.")
    proc = _run([
        tools.ffprobe,
        "-v", "error",
        "-select_streams", "a",
        "-show_streams",
        "-of", "json",
        str(path),
    ])
    if proc.returncode != 0:
        raise AudioTrackIntelligenceError(
            proc.stderr.strip() or "ffprobe audio en échec."
        )
    try:
        streams = json.loads(proc.stdout).get("streams") or []
    except json.JSONDecodeError as exc:
        raise AudioTrackIntelligenceError("Réponse ffprobe invalide.") from exc

    out = []
    for track_index, stream in enumerate(streams):
        tags = stream.get("tags") or {}
        disposition = stream.get("disposition") or {}
        out.append({
            "track_index": track_index,
            "stream_index": int(stream.get("index", track_index)),
            "codec": stream.get("codec_name"),
            "channels": int(stream["channels"]) if stream.get("channels") else None,
            "channel_layout": stream.get("channel_layout"),
            "sample_rate": (
                int(stream["sample_rate"])
                if str(stream.get("sample_rate") or "").isdigit()
                else None
            ),
            "language": tags.get("language"),
            "title": tags.get("title"),
            "default": bool(disposition.get("default")),
            "forced": bool(disposition.get("forced")),
        })
    return out


_MEAN_RE = re.compile(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB")
_MAX_RE = re.compile(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB")
_SILENCE_END_RE = re.compile(
    r"silence_end:\s*(-?\d+(?:\.\d+)?)\s*\|\s*"
    r"silence_duration:\s*(\d+(?:\.\d+)?)"
)


def measure_audio_track(path: Path, track_index: int) -> dict:
    tools = detect_audio_track_tools()
    if not tools.ffmpeg:
        raise AudioTrackIntelligenceError("ffmpeg n’est pas disponible.")

    volume = _run([
        tools.ffmpeg,
        "-hide_banner", "-nostats",
        "-i", str(path),
        "-map", f"0:a:{int(track_index)}",
        "-af", "volumedetect",
        "-f", "null", "-",
    ])
    if volume.returncode != 0:
        raise AudioTrackIntelligenceError(
            volume.stderr.strip() or "Mesure de niveau audio en échec."
        )
    mean_match = _MEAN_RE.search(volume.stderr)
    max_match = _MAX_RE.search(volume.stderr)
    mean_dbfs = float(mean_match.group(1)) if mean_match else None
    peak_dbfs = float(max_match.group(1)) if max_match else None

    silence = _run([
        tools.ffmpeg,
        "-hide_banner", "-nostats",
        "-i", str(path),
        "-map", f"0:a:{int(track_index)}",
        "-af", "silencedetect=noise=-50dB:d=0.35",
        "-f", "null", "-",
    ])
    silent_seconds = 0.0
    if silence.returncode == 0:
        silent_seconds = sum(
            float(duration)
            for _end, duration in _SILENCE_END_RE.findall(silence.stderr)
        )

    return {
        "mean_dbfs": mean_dbfs,
        "peak_dbfs": peak_dbfs,
        "silent": peak_dbfs is None or peak_dbfs <= SILENCE_PEAK_DBFS,
        "detected_silence_seconds": round(silent_seconds, 4),
    }


def _selected_track(root: Path, media_id: int) -> int | None:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT track_index FROM audio_track_analysis "
            "WHERE media_id=? AND selected_for_transcription=1 "
            "ORDER BY track_index LIMIT 1",
            (int(media_id),),
        ).fetchone()
    finally:
        conn.close()
    return int(row["track_index"]) if row else None


def list_audio_tracks(root: Path, media_id: int) -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            "SELECT * FROM audio_track_analysis "
            "WHERE media_id=? ORDER BY track_index",
            (int(media_id),),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for row in rows:
        item = dict(row)
        item["default"] = bool(item.get("is_default"))
        item["silent"] = bool(item.get("silent"))
        item["selected_for_transcription"] = bool(
            item.get("selected_for_transcription")
        )
        item.pop("is_default", None)
        out.append(item)
    return out


def analyze_audio_tracks(
    root: Path,
    media_id: int,
    *,
    force: bool = False,
) -> dict:
    item = _media_item(root, media_id)
    existing = list_audio_tracks(root, media_id)
    if (
        existing
        and all(
            x.get("analyzer_version") == AUDIO_TRACK_INTELLIGENCE_VERSION
            and x.get("status") == "READY"
            for x in existing
        )
        and not force
    ):
        return {
            "media_id": int(media_id),
            "tracks": existing,
            "recommended_track_index": recommend_audio_track(existing),
            "cached": True,
        }

    tools = detect_audio_track_tools()
    if not tools.ready:
        return {
            "media_id": int(media_id),
            "tracks": [],
            "recommended_track_index": None,
            "cached": False,
            "status": "TOOLS_UNAVAILABLE",
        }

    path = _media_path(root, item)
    streams = probe_audio_streams(path)
    previous_selected = _selected_track(root, media_id)

    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            "DELETE FROM audio_track_analysis WHERE media_id=?",
            (int(media_id),),
        )
        for stream in streams:
            measurement = measure_audio_track(path, stream["track_index"])
            conn.execute(
                """
                INSERT INTO audio_track_analysis(
                  media_id, track_index, stream_index, analyzer_version, status,
                  codec, channels, channel_layout, sample_rate, language, title,
                  is_default, mean_dbfs, peak_dbfs, silent,
                  detected_silence_seconds, selected_for_transcription
                )
                VALUES (?, ?, ?, ?, 'READY', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(media_id),
                    int(stream["track_index"]),
                    int(stream["stream_index"]),
                    AUDIO_TRACK_INTELLIGENCE_VERSION,
                    stream.get("codec"),
                    stream.get("channels"),
                    stream.get("channel_layout"),
                    stream.get("sample_rate"),
                    stream.get("language"),
                    stream.get("title"),
                    1 if stream.get("default") else 0,
                    measurement.get("mean_dbfs"),
                    measurement.get("peak_dbfs"),
                    1 if measurement.get("silent") else 0,
                    measurement.get("detected_silence_seconds", 0.0),
                    1 if previous_selected == stream["track_index"] else 0,
                ),
            )
        conn.commit()
    finally:
        conn.close()

    tracks = list_audio_tracks(root, media_id)
    return {
        "media_id": int(media_id),
        "tracks": tracks,
        "recommended_track_index": recommend_audio_track(tracks),
        "cached": False,
    }


def recommend_audio_track(tracks: list[dict]) -> int | None:
    candidates = [x for x in tracks if not x.get("silent")]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda x: (
            1 if x.get("default") else 0,
            float(x.get("peak_dbfs") or -120.0),
            float(x.get("mean_dbfs") or -120.0),
            int(x.get("channels") or 0),
            -int(x.get("track_index") or 0),
        ),
        reverse=True,
    )
    return int(ranked[0]["track_index"])


def select_audio_track(
    root: Path,
    media_id: int,
    track_index: int,
) -> dict:
    tracks = list_audio_tracks(root, media_id)
    if not tracks:
        tracks = analyze_audio_tracks(root, media_id).get("tracks") or []
    target = next(
        (x for x in tracks if int(x["track_index"]) == int(track_index)),
        None,
    )
    if target is None:
        raise AudioTrackIntelligenceError(
            f"Piste audio introuvable : {track_index}"
        )
    if target.get("silent"):
        raise AudioTrackIntelligenceError(
            "La piste sélectionnée est considérée silencieuse ; "
            "la sélection explicite d’une autre piste est requise."
        )

    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            "UPDATE audio_track_analysis "
            "SET selected_for_transcription=0, updated_at=CURRENT_TIMESTAMP "
            "WHERE media_id=?",
            (int(media_id),),
        )
        conn.execute(
            "UPDATE audio_track_analysis "
            "SET selected_for_transcription=1, updated_at=CURRENT_TIMESTAMP "
            "WHERE media_id=? AND track_index=?",
            (int(media_id), int(track_index)),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "media_id": int(media_id),
        "selected_track_index": int(track_index),
        "track": next(
            x for x in list_audio_tracks(root, media_id)
            if int(x["track_index"]) == int(track_index)
        ),
        "policy": {
            "human_selection_persisted": True,
            "automatic_transcription": False,
        },
    }


def audio_waveform_samples(
    root: Path,
    media_id: int,
    *,
    track_index: int | None = None,
    samples: int = 240,
) -> list[float]:
    item = _media_item(root, media_id)
    path = _media_path(root, item)
    tracks = list_audio_tracks(root, media_id)
    if not tracks:
        tracks = analyze_audio_tracks(root, media_id).get("tracks") or []
    if track_index is None:
        selected = next(
            (x for x in tracks if x.get("selected_for_transcription")),
            None,
        )
        if selected is None:
            recommended = recommend_audio_track(tracks)
            track_index = recommended
        else:
            track_index = int(selected["track_index"])
    if track_index is None:
        return []

    tools = detect_audio_track_tools()
    if not tools.ffmpeg:
        return []
    samples = max(40, min(int(samples), 1200))
    try:
        proc = subprocess.run(
            [
                tools.ffmpeg,
                "-hide_banner", "-loglevel", "error",
                "-i", str(path),
                "-map", f"0:a:{int(track_index)}",
                "-ac", "1",
                "-ar", "4000",
                "-f", "s16le",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0 or not proc.stdout:
        return []

    raw = proc.stdout
    count = len(raw) // 2
    if count <= 0:
        return []
    values = [
        int.from_bytes(
            raw[i:i + 2],
            byteorder="little",
            signed=True,
        )
        for i in range(0, len(raw) - 1, 2)
    ]
    bucket = max(1, len(values) // samples)
    peaks = []
    for start in range(0, len(values), bucket):
        chunk = values[start:start + bucket]
        if not chunk:
            continue
        peaks.append(
            round(max(abs(x) for x in chunk) / 32768.0, 4)
        )
        if len(peaks) >= samples:
            break
    return peaks


def selected_audio_track(root: Path, media_id: int) -> dict | None:
    selected = _selected_track(root, media_id)
    if selected is None:
        return None
    return next(
        (
            x for x in list_audio_tracks(root, media_id)
            if int(x["track_index"]) == selected
        ),
        None,
    )
